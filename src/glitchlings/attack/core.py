"""Attack orchestrator for measuring corruption impact.

This module provides the Attack class, a boundary layer that coordinates
glitchling corruption and metric computation. It follows the functional
purity architecture:

- **Pure planning**: Input analysis and result planning (core_planning.py)
- **Impure execution**: Corruption, tokenization, metrics (core_execution.py)
- **Boundary layer**: This module - validates inputs and delegates

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    pass  # For forward references in type hints

from ..conf import DEFAULT_ATTACK_SEED
from ..protocols import Corruptor
from ..util.transcripts import Transcript, TranscriptTarget
from .core_execution import (
    execute_attack,
    get_default_metrics,
    resolve_glitchlings,
)
from .core_planning import (
    plan_attack,
    plan_result,
)
from .encode import describe_tokenizer
from .metrics import Metric
from .tokenization import Tokenizer, resolve_tokenizer

# ---------------------------------------------------------------------------
# Streaming Token Iterator
# ---------------------------------------------------------------------------


@dataclass
class TokenWindow:
    """A window of tokens for streaming processing.

    Represents a chunk of tokens that can be processed without loading
    the entire token sequence into memory.

    Attributes:
        tokens: Token strings in this window.
        token_ids: Token IDs in this window.
        start_index: Starting index of this window in the full sequence.
        is_last: Whether this is the final window.
    """

    tokens: list[str]
    token_ids: list[int]
    start_index: int
    is_last: bool

    def __len__(self) -> int:
        return len(self.tokens)


class StreamingTokens:
    """Iterator for streaming token access with windowed processing.

    Allows processing large token sequences in fixed-size windows to
    prevent OOM on very large inputs. Tokens are loaded lazily per window.

    Attributes:
        window_size: Number of tokens per window.
        total_tokens: Total number of tokens (if known).
    """

    def __init__(
        self,
        tokens: list[str],
        token_ids: list[int],
        *,
        window_size: int = 10000,
    ):
        """Initialize streaming token access.

        Args:
            tokens: Full token list (will be windowed during iteration).
            token_ids: Full token ID list.
            window_size: Number of tokens per window. Defaults to 10000.
        """
        self._tokens = tokens
        self._token_ids = token_ids
        self.window_size = window_size
        self.total_tokens = len(tokens)

    def __iter__(self) -> Iterator[TokenWindow]:
        """Iterate over token windows."""
        for start in range(0, self.total_tokens, self.window_size):
            end = min(start + self.window_size, self.total_tokens)
            yield TokenWindow(
                tokens=self._tokens[start:end],
                token_ids=self._token_ids[start:end],
                start_index=start,
                is_last=(end >= self.total_tokens),
            )

    def __len__(self) -> int:
        """Return total number of tokens."""
        return self.total_tokens

    @property
    def all_tokens(self) -> list[str]:
        """Get all tokens (materializes full list)."""
        return self._tokens

    @property
    def all_token_ids(self) -> list[int]:
        """Get all token IDs (materializes full list)."""
        return self._token_ids


# ---------------------------------------------------------------------------
# Result Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AttackResult:
    """Result of an attack operation containing tokens and metrics.

    Attributes:
        original: Original input (string, transcript, or batch).
        corrupted: Corrupted output (same type as original).
        input_tokens: Tokenized original content.
        output_tokens: Tokenized corrupted content.
        input_token_ids: Token IDs for original.
        output_token_ids: Token IDs for corrupted.
        tokenizer_info: Description of the tokenizer used.
        metrics: Computed metric values.
    """

    original: str | Transcript | Sequence[str]
    corrupted: str | Transcript | Sequence[str]
    input_tokens: list[str] | list[list[str]]
    output_tokens: list[str] | list[list[str]]
    input_token_ids: list[int] | list[list[int]]
    output_token_ids: list[int] | list[list[int]]
    tokenizer_info: str
    metrics: dict[str, float | list[float]]

    def _tokens_are_batched(self) -> bool:
        """Check if tokens represent a batch."""
        tokens = self.input_tokens
        if tokens and isinstance(tokens[0], list):
            return True
        return isinstance(self.original, list) or isinstance(self.corrupted, list)

    def _token_batches(self) -> tuple[list[list[str]], list[list[str]]]:
        """Get tokens as batches (wrapping single sequences if needed)."""
        if self._tokens_are_batched():
            return (
                cast(list[list[str]], self.input_tokens),
                cast(list[list[str]], self.output_tokens),
            )
        return (
            [cast(list[str], self.input_tokens)],
            [cast(list[str], self.output_tokens)],
        )

    def _token_counts(self) -> tuple[list[int], list[int]]:
        """Compute token counts per batch item."""
        inputs, outputs = self._token_batches()
        return [len(tokens) for tokens in inputs], [len(tokens) for tokens in outputs]

    @staticmethod
    def _format_metric_value(value: float | list[float]) -> str:
        """Format a metric value for display."""
        if isinstance(value, list):
            if not value:
                return "[]"
            if len(value) <= 4:
                rendered = ", ".join(f"{entry:.3f}" for entry in value)
                return f"[{rendered}]"
            total = sum(value)
            minimum = min(value)
            maximum = max(value)
            mean = total / len(value)
            return f"avg={mean:.3f} min={minimum:.3f} max={maximum:.3f}"
        return f"{value:.3f}"

    @staticmethod
    def _format_token(token: str, *, max_length: int) -> str:
        """Format a token for display, truncating if needed."""
        clean = token.replace("\n", "\\n")
        if len(clean) > max_length:
            return clean[: max_length - 3] + "..."
        return clean

    def to_report(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""
        input_counts, output_counts = self._token_counts()
        return {
            "tokenizer": self.tokenizer_info,
            "original": self.original,
            "corrupted": self.corrupted,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_token_ids": self.input_token_ids,
            "output_token_ids": self.output_token_ids,
            "token_counts": {
                "input": {"per_sample": input_counts, "total": sum(input_counts)},
                "output": {"per_sample": output_counts, "total": sum(output_counts)},
            },
            "metrics": self.metrics,
        }

    def summary(self, *, max_rows: int = 8, max_token_length: int = 24) -> str:
        """Generate a human-readable summary.

        Args:
            max_rows: Maximum rows to display in token drift.
            max_token_length: Maximum characters per token.

        Returns:
            Formatted multi-line summary string.
        """
        input_batches, output_batches = self._token_batches()
        input_counts, output_counts = self._token_counts()
        is_batch = self._tokens_are_batched()

        lines: list[str] = [f"Tokenizer: {self.tokenizer_info}"]
        if is_batch:
            lines.append(f"Samples: {len(input_batches)}")

        lines.append("Token counts:")
        for index, (input_count, output_count) in enumerate(
            zip(input_counts, output_counts), start=1
        ):
            prefix = f"#{index} " if is_batch else ""
            delta = output_count - input_count
            lines.append(f"  {prefix}{input_count} -> {output_count} ({delta:+d})")
            if index >= max_rows and len(input_batches) > max_rows:
                remaining = len(input_batches) - max_rows
                lines.append(f"  ... {remaining} more samples")
                break

        lines.append("Metrics:")
        for name, value in self.metrics.items():
            lines.append(f"  {name}: {self._format_metric_value(value)}")

        if input_batches:
            focus_index = 0
            if is_batch and len(input_batches) > 1:
                lines.append("Token drift (first sample):")
            else:
                lines.append("Token drift:")
            input_tokens = input_batches[focus_index]
            output_tokens = output_batches[focus_index]
            rows = max(len(input_tokens), len(output_tokens))
            display_rows = min(rows, max_rows)
            for idx in range(display_rows):
                left = (
                    self._format_token(input_tokens[idx], max_length=max_token_length)
                    if idx < len(input_tokens)
                    else ""
                )
                right = (
                    self._format_token(output_tokens[idx], max_length=max_token_length)
                    if idx < len(output_tokens)
                    else ""
                )
                if idx >= len(input_tokens):
                    marker = "+"
                elif idx >= len(output_tokens):
                    marker = "-"
                elif input_tokens[idx] == output_tokens[idx]:
                    marker = "="
                else:
                    marker = "!"
                lines.append(f"  {idx + 1:>3}{marker} {left} -> {right}")
            if rows > display_rows:
                lines.append(f"  ... {rows - display_rows} more tokens")
        else:
            lines.append("Token drift: (empty input)")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Token-Level Analysis
    # -------------------------------------------------------------------------

    def get_metric(self, name: str) -> float | list[float] | None:
        """Get a specific metric value by name.

        Args:
            name: Metric name (e.g., 'normalized_edit_distance').

        Returns:
            Metric value, or None if not found.
        """
        return self.metrics.get(name)

    def get_changed_tokens(self, batch_index: int = 0) -> list[tuple[str, str]]:
        """Get tokens that changed between original and corrupted.

        Args:
            batch_index: Which batch item to analyze (0 for single strings).

        Returns:
            List of (original_token, corrupted_token) pairs where they differ.
            Only includes positions where both tokens exist and are different.
        """
        input_batches, output_batches = self._token_batches()
        if batch_index >= len(input_batches):
            return []

        input_tokens = input_batches[batch_index]
        output_tokens = output_batches[batch_index]

        changes: list[tuple[str, str]] = []
        for i in range(min(len(input_tokens), len(output_tokens))):
            if input_tokens[i] != output_tokens[i]:
                changes.append((input_tokens[i], output_tokens[i]))
        return changes

    def get_mutation_positions(self, batch_index: int = 0) -> list[int]:
        """Get indices of tokens that were mutated.

        Args:
            batch_index: Which batch item to analyze (0 for single strings).

        Returns:
            List of token positions where original != corrupted.
            Only includes positions where both tokens exist.
        """
        input_batches, output_batches = self._token_batches()
        if batch_index >= len(input_batches):
            return []

        input_tokens = input_batches[batch_index]
        output_tokens = output_batches[batch_index]

        positions: list[int] = []
        for i in range(min(len(input_tokens), len(output_tokens))):
            if input_tokens[i] != output_tokens[i]:
                positions.append(i)
        return positions

    def get_token_alignment(self, batch_index: int = 0) -> list[dict[str, object]]:
        """Get detailed token-by-token comparison with alignment info.

        Args:
            batch_index: Which batch item to analyze (0 for single strings).

        Returns:
            List of alignment entries, each containing:
            - index: Token position
            - original: Original token (empty string if added)
            - corrupted: Corrupted token (empty string if removed)
            - changed: Whether the token changed
            - op: Operation type ('=' unchanged, '!' modified, '+' added, '-' removed)
        """
        input_batches, output_batches = self._token_batches()
        if batch_index >= len(input_batches):
            return []

        input_tokens = input_batches[batch_index]
        output_tokens = output_batches[batch_index]

        alignment: list[dict[str, object]] = []
        max_len = max(len(input_tokens), len(output_tokens))

        for i in range(max_len):
            orig = input_tokens[i] if i < len(input_tokens) else ""
            corr = output_tokens[i] if i < len(output_tokens) else ""

            if i >= len(input_tokens):
                op = "+"
                changed = True
            elif i >= len(output_tokens):
                op = "-"
                changed = True
            elif orig == corr:
                op = "="
                changed = False
            else:
                op = "!"
                changed = True

            alignment.append(
                {
                    "index": i,
                    "original": orig,
                    "corrupted": corr,
                    "changed": changed,
                    "op": op,
                }
            )

        return alignment


# ---------------------------------------------------------------------------
# Attack Orchestrator
# ---------------------------------------------------------------------------


class Attack:
    """Orchestrator for applying glitchling corruptions and measuring impact.

    Attack is a thin boundary layer that:
    1. Validates inputs at construction time
    2. Delegates planning to pure functions (core_planning.py)
    3. Delegates execution to impure functions (core_execution.py)

    Example:
        >>> attack = Attack(Typogre(rate=0.05), tokenizer='cl100k_base')
        >>> result = attack.run("Hello world")
        >>> print(result.summary())
    """

    def __init__(
        self,
        glitchlings: Corruptor | str | Sequence[str | Corruptor],
        tokenizer: str | Tokenizer | None = None,
        metrics: Mapping[str, Metric] | None = None,
        *,
        seed: int | None = None,
        transcript_target: TranscriptTarget | None = None,
    ) -> None:
        """Initialize an Attack.

        Args:
            glitchlings: Glitchling specification - a single Glitchling,
                string spec (e.g. 'Typogre(rate=0.05)'), or iterable of these.
            tokenizer: Tokenizer name (e.g. 'cl100k_base'), Tokenizer instance,
                or None (defaults to whitespace tokenizer).
            metrics: Dictionary of metric functions. If None, uses defaults
                (jensen_shannon_divergence, normalized_edit_distance,
                subsequence_retention).
            seed: Master seed for the Gaggle. If None, uses DEFAULT_ATTACK_SEED.
            transcript_target: Which transcript turns to corrupt. Accepts:
                - "last": corrupt only the last turn (default)
                - "all": corrupt all turns
                - "assistant"/"user": corrupt only those roles
                - int: corrupt a specific index
                - Sequence[int]: corrupt specific indices
        """
        # Boundary: resolve seed
        gaggle_seed = seed if seed is not None else DEFAULT_ATTACK_SEED

        # Impure: resolve glitchlings (clones to avoid mutation)
        self.glitchlings = resolve_glitchlings(
            glitchlings,
            seed=gaggle_seed,
            transcript_target=transcript_target,
        )

        # Impure: resolve tokenizer
        self.tokenizer = resolve_tokenizer(tokenizer)
        self.tokenizer_info = describe_tokenizer(self.tokenizer, tokenizer)

        # Setup metrics
        if metrics is None:
            self.metrics: dict[str, Metric] = get_default_metrics()
        else:
            self.metrics = dict(metrics)

        # Validate custom metrics have correct signature
        self._validate_metrics()

    def _validate_metrics(self) -> None:
        """Validate that metric functions have correct signatures.

        Uses signature inspection to avoid executing metrics (which may have
        side effects).

        Raises:
            ValueError: If a metric function has an invalid signature.
        """
        for name, func in self.metrics.items():
            if not callable(func):
                raise ValueError(f"Metric '{name}' is not callable")

            try:
                sig = inspect.signature(func)
                params = list(sig.parameters.values())

                # Count required positional parameters (no default, not *args/**kwargs)
                positional_params = [
                    p
                    for p in params
                    if p.kind
                    in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                    and p.default is inspect.Parameter.empty
                ]

                if len(positional_params) < 2:
                    raise ValueError(
                        f"Metric '{name}' must accept at least 2 positional arguments "
                        f"(original_tokens, corrupted_tokens), found {len(positional_params)}"
                    )
            except (ValueError, TypeError) as e:
                if "Metric" in str(e):
                    raise
                raise ValueError(f"Metric '{name}' has invalid signature: {e}") from e

    def run(self, text: str | Transcript | Sequence[str]) -> AttackResult:
        """Apply corruptions and calculate metrics.

        Supports single strings, batches of strings, and chat transcripts.
        For batched inputs, metrics are computed per entry and returned
        as lists.

        Args:
            text: Input text, transcript, or batch of strings to corrupt.

        Returns:
            AttackResult containing original, corrupted, tokens, and metrics.

        Raises:
            TypeError: If input type is not recognized.
        """
        # Pure: plan the attack
        attack_plan = plan_attack(text)
        result_plan = plan_result(
            attack_plan,
            list(self.metrics.keys()),
            self.tokenizer_info,
        )

        # Impure: execute the attack
        fields = execute_attack(
            self.glitchlings,
            self.tokenizer,
            self.metrics,
            attack_plan,
            result_plan,
            text,
        )

        return AttackResult(**fields)  # type: ignore[arg-type]

    def run_batch(
        self,
        texts: Sequence[str | Transcript],
        *,
        progress_callback: Callable[[list[AttackResult]], None] | None = None,
    ) -> list[AttackResult]:
        """Run attack on multiple texts, returning results in order.

        Args:
            texts: List of inputs to process.
            progress_callback: Optional callback called after each result,
                receiving the list of results so far.

        Returns:
            List of AttackResult objects in input order.
        """
        results: list[AttackResult] = []
        for text in texts:
            result = self.run(text)
            results.append(result)
            if progress_callback is not None:
                progress_callback(results)
        return results

    def run_stream(
        self,
        texts: Iterator[str | Transcript] | Sequence[str | Transcript],
    ) -> Generator[AttackResult, None, None]:
        """Stream attack results as they are computed.

        Unlike run_batch(), this method yields results immediately as each
        text is processed, allowing for memory-efficient processing of large
        datasets without holding all results in memory.

        Args:
            texts: Iterator or sequence of inputs to process.

        Yields:
            AttackResult objects as they are computed.

        Example:
            >>> attack = Attack(Typogre(rate=0.05))
            >>> for result in attack.run_stream(large_text_iterator):
            ...     process_result(result)  # Process each result immediately
        """
        for text in texts:
            yield self.run(text)

    def run_streaming_result(
        self,
        text: str | Transcript | Sequence[str],
        *,
        window_size: int = 10000,
    ) -> "StreamingAttackResult":
        """Run attack and return a streaming result for large token sets.

        This method returns a StreamingAttackResult that provides windowed
        access to tokens, preventing OOM when processing very large texts.

        Args:
            text: Input text, transcript, or batch of strings to corrupt.
            window_size: Number of tokens per window when streaming.
                Defaults to 10000.

        Returns:
            StreamingAttackResult with windowed token access.
        """
        result = self.run(text)
        return StreamingAttackResult.from_attack_result(result, window_size=window_size)


# ---------------------------------------------------------------------------
# Streaming Attack Result
# ---------------------------------------------------------------------------


@dataclass
class StreamingAttackResult:
    """Attack result with streaming token access for large datasets.

    This class wraps an AttackResult and provides windowed access to tokens,
    allowing processing of very large token sequences without loading them
    all into memory at once.

    Attributes:
        original: Original input text/transcript/batch.
        corrupted: Corrupted output.
        tokenizer_info: Description of the tokenizer used.
        metrics: Computed metric values.
        window_size: Number of tokens per streaming window.
    """

    original: str | Transcript | Sequence[str]
    corrupted: str | Transcript | Sequence[str]
    tokenizer_info: str
    metrics: dict[str, float | list[float]]
    window_size: int = field(default=10000)
    _input_tokens: list[str] | list[list[str]] = field(default_factory=list, repr=False)
    _output_tokens: list[str] | list[list[str]] = field(default_factory=list, repr=False)
    _input_token_ids: list[int] | list[list[int]] = field(default_factory=list, repr=False)
    _output_token_ids: list[int] | list[list[int]] = field(default_factory=list, repr=False)

    @classmethod
    def from_attack_result(
        cls,
        result: AttackResult,
        *,
        window_size: int = 10000,
    ) -> "StreamingAttackResult":
        """Create a StreamingAttackResult from an AttackResult.

        Args:
            result: The AttackResult to wrap.
            window_size: Number of tokens per window.

        Returns:
            StreamingAttackResult with windowed token access.
        """
        return cls(
            original=result.original,
            corrupted=result.corrupted,
            tokenizer_info=result.tokenizer_info,
            metrics=result.metrics,
            window_size=window_size,
            _input_tokens=result.input_tokens,
            _output_tokens=result.output_tokens,
            _input_token_ids=result.input_token_ids,
            _output_token_ids=result.output_token_ids,
        )

    def _is_batched(self) -> bool:
        """Check if tokens represent a batch."""
        tokens = self._input_tokens
        if tokens and isinstance(tokens[0], list):
            return True
        return isinstance(self.original, list) or isinstance(self.corrupted, list)

    def stream_input_tokens(self, batch_index: int = 0) -> StreamingTokens:
        """Get streaming access to input tokens.

        Args:
            batch_index: Which batch item to stream (0 for single strings).

        Returns:
            StreamingTokens iterator for windowed access.
        """
        if self._is_batched():
            tokens = cast(list[list[str]], self._input_tokens)[batch_index]
            token_ids = cast(list[list[int]], self._input_token_ids)[batch_index]
        else:
            tokens = cast(list[str], self._input_tokens)
            token_ids = cast(list[int], self._input_token_ids)

        return StreamingTokens(tokens, token_ids, window_size=self.window_size)

    def stream_output_tokens(self, batch_index: int = 0) -> StreamingTokens:
        """Get streaming access to output tokens.

        Args:
            batch_index: Which batch item to stream (0 for single strings).

        Returns:
            StreamingTokens iterator for windowed access.
        """
        if self._is_batched():
            tokens = cast(list[list[str]], self._output_tokens)[batch_index]
            token_ids = cast(list[list[int]], self._output_token_ids)[batch_index]
        else:
            tokens = cast(list[str], self._output_tokens)
            token_ids = cast(list[int], self._output_token_ids)

        return StreamingTokens(tokens, token_ids, window_size=self.window_size)

    def stream_token_pairs(
        self,
        batch_index: int = 0,
    ) -> Generator[tuple[TokenWindow, TokenWindow], None, None]:
        """Stream paired windows of input and output tokens.

        Yields windows of (input_tokens, output_tokens) for aligned comparison.
        Useful for computing streaming metrics or processing large diffs.

        Args:
            batch_index: Which batch item to stream (0 for single strings).

        Yields:
            Tuples of (input_window, output_window).
        """
        input_stream = self.stream_input_tokens(batch_index)
        output_stream = self.stream_output_tokens(batch_index)

        for input_window, output_window in zip(input_stream, output_stream):
            yield input_window, output_window

    def get_token_count(self, batch_index: int = 0) -> tuple[int, int]:
        """Get token counts without materializing full lists.

        Args:
            batch_index: Which batch item to count (0 for single strings).

        Returns:
            Tuple of (input_token_count, output_token_count).
        """
        input_stream = self.stream_input_tokens(batch_index)
        output_stream = self.stream_output_tokens(batch_index)
        return len(input_stream), len(output_stream)

    def to_attack_result(self) -> AttackResult:
        """Convert back to a standard AttackResult.

        Warning: This materializes all tokens in memory.

        Returns:
            AttackResult with all tokens loaded.
        """
        return AttackResult(
            original=self.original,
            corrupted=self.corrupted,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            input_token_ids=self._input_token_ids,
            output_token_ids=self._output_token_ids,
            tokenizer_info=self.tokenizer_info,
            metrics=self.metrics,
        )

    def get_metric(self, name: str) -> float | list[float] | None:
        """Get a specific metric value by name."""
        return self.metrics.get(name)


__all__ = [
    "Attack",
    "AttackResult",
    "StreamingAttackResult",
    "StreamingTokens",
    "TokenWindow",
]

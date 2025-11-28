from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeGuard, cast

from ..conf import DEFAULT_ATTACK_SEED
from ..util.adapters import coerce_gaggle
from ..util.transcripts import Transcript, TranscriptTarget, is_transcript
from ..zoo.core import Glitchling
from .compose import (
    build_batch_result,
    build_empty_result,
    build_single_result,
    extract_transcript_contents,
)
from .encode import describe_tokenizer, encode_batch
from .metrics import (
    Metric,
    jensen_shannon_divergence,
    normalized_edit_distance,
    subsequence_retention,
)
from .tokenization import Tokenizer, resolve_tokenizer


def _is_string_batch(value: Any) -> TypeGuard[Sequence[str]]:
    if isinstance(value, (str, bytes)):
        return False
    if not isinstance(value, Sequence):
        return False
    return all(isinstance(item, str) for item in value)


@dataclass
class AttackResult:
    original: str | Transcript | Sequence[str]
    corrupted: str | Transcript | Sequence[str]
    input_tokens: list[str] | list[list[str]]
    output_tokens: list[str] | list[list[str]]
    input_token_ids: list[int] | list[list[int]]
    output_token_ids: list[int] | list[list[int]]
    tokenizer_info: str
    metrics: dict[str, float | list[float]]

    def _tokens_are_batched(self) -> bool:
        tokens = self.input_tokens
        if tokens and isinstance(tokens[0], list):
            return True
        return isinstance(self.original, list) or isinstance(self.corrupted, list)

    def _token_batches(self) -> tuple[list[list[str]], list[list[str]]]:
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
        inputs, outputs = self._token_batches()
        return [len(tokens) for tokens in inputs], [len(tokens) for tokens in outputs]

    @staticmethod
    def _format_metric_value(value: float | list[float]) -> str:
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
        clean = token.replace("\n", "\\n")
        if len(clean) > max_length:
            return clean[: max_length - 3] + "..."
        return clean

    def to_report(self) -> dict[str, object]:
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


@dataclass
class MultiAttackResult:
    results: dict[str, AttackResult]
    order: list[str]

    @property
    def primary(self) -> AttackResult:
        return self.results[self.order[0]]

    def to_report(self) -> dict[str, object]:
        return {
            "tokenizers": list(self.order),
            "results": {name: self.results[name].to_report() for name in self.order},
        }

    def summary(self, *, max_rows: int = 6, max_token_length: int = 24) -> str:
        lines: list[str] = []
        for index, name in enumerate(self.order, start=1):
            lines.append(f"{index}. {name}")
            nested = self.results[name].summary(
                max_rows=max_rows,
                max_token_length=max_token_length,
            )
            lines.extend(f"   {line}" for line in nested.splitlines())
        return "\n".join(lines)


class Attack:
    """Orchestrator for applying glitchling corruptions and measuring impact.

    Attack is a thin orchestrator that coordinates:
    - Glitchling invocation (impure: may use Rust FFI)
    - Tokenization (impure: resolves tokenizers)
    - Metric computation (impure: calls Rust metrics)
    - Result composition (delegated to pure compose.py helpers)

    The class validates inputs at construction time (boundary layer)
    and delegates pure operations to compose.py and encode.py modules.
    """

    def __init__(
        self,
        glitchlings: Glitchling | str | Iterable[str | Glitchling],
        tokenizer: str | Tokenizer | None = None,
        metrics: Mapping[str, Metric] | None = None,
        *,
        seed: int | None = None,
        transcript_target: TranscriptTarget | None = None,
    ) -> None:
        """Initialize an Attack.

        Args:
            glitchlings: A single Glitchling (including Gaggle), a string specification
                         (e.g. 'Typogre(rate=0.05)'), or an iterable of glitchlings/specs.
            tokenizer: Tokenizer name (e.g. 'cl100k_base', 'bert-base-uncased'),
                       Tokenizer object, or None (defaults to whitespace).
            metrics: Dictionary of metric functions. If None, defaults are used.
            seed: Optional master seed used when building a Gaggle. When a Gaggle
                  instance is provided directly, the seed is applied to that instance
                  to keep runs deterministic. Instances are cloned before seeding to
                  avoid mutating caller-owned objects.
            transcript_target: Which transcript turns to corrupt. When None (default),
                uses the Gaggle default ("last"). Accepts:
                - "last": corrupt only the last turn (default)
                - "all": corrupt all turns
                - "assistant": corrupt only assistant turns
                - "user": corrupt only user turns
                - int: corrupt a specific index (negative indexing supported)
                - Sequence[int]: corrupt specific indices
        """
        # Boundary validation and resolution (impure)
        gaggle_seed = seed if seed is not None else DEFAULT_ATTACK_SEED
        cloned_glitchlings = self._clone_glitchling_specs(glitchlings)
        self.glitchlings = coerce_gaggle(
            cloned_glitchlings,
            seed=gaggle_seed,
            apply_seed_to_existing=True,
            transcript_target=transcript_target,
        )

        # Impure tokenizer resolution
        self.tokenizer = resolve_tokenizer(tokenizer)
        self.tokenizer_info = describe_tokenizer(self.tokenizer, tokenizer)

        # Metrics setup
        if metrics is None:
            self.metrics: dict[str, Metric] = {
                "jensen_shannon_divergence": jensen_shannon_divergence,
                "normalized_edit_distance": normalized_edit_distance,
                "subsequence_retention": subsequence_retention,
            }
        else:
            self.metrics = dict(metrics)

    @staticmethod
    def _clone_glitchling_specs(
        glitchlings: Glitchling | str | Iterable[str | Glitchling],
    ) -> Glitchling | str | list[str | Glitchling]:
        """Return cloned glitchling specs so Attack ownership never mutates inputs."""
        if isinstance(glitchlings, Glitchling):
            return glitchlings.clone()

        if isinstance(glitchlings, str):
            return glitchlings

        if isinstance(glitchlings, Iterable):
            cloned_specs: list[str | Glitchling] = []
            for entry in glitchlings:
                if isinstance(entry, Glitchling):
                    cloned_specs.append(entry.clone())
                else:
                    cloned_specs.append(entry)
            return cloned_specs

        return glitchlings

    def run(self, text: str | Transcript | Sequence[str]) -> AttackResult:
        """Apply corruptions and calculate metrics.

        Supports single strings, batches of strings, and chat transcripts. For
        batched inputs (transcripts or lists of strings) metrics are computed
        per entry and returned as lists.

        Args:
            text: Input text, transcript, or batch of plain strings to corrupt.

        Returns:
            AttackResult containing original, corrupted, tokens, and metrics.
        """
        if _is_string_batch(text):
            original_batch = list(text)
            corrupted_batch: list[str] = []
            for entry in original_batch:
                corrupted = self.glitchlings.corrupt(entry)
                if not isinstance(corrupted, str):
                    raise TypeError("Attack expected string output when given a batch of strings.")
                corrupted_batch.append(corrupted)

            return self._compose_result(
                original_container=original_batch,
                corrupted_container=corrupted_batch,
                original_contents=original_batch,
                corrupted_contents=corrupted_batch,
                is_batch=True,
            )

        if is_transcript(text):
            original_transcript = text
            corrupted_transcript = self.glitchlings.corrupt(original_transcript)
            if not is_transcript(corrupted_transcript):
                raise ValueError("Attack expected output type to mirror input type.")

            original_contents = extract_transcript_contents(original_transcript)
            corrupted_contents = extract_transcript_contents(corrupted_transcript)

            return self._compose_result(
                original_container=original_transcript,
                corrupted_container=corrupted_transcript,
                original_contents=original_contents,
                corrupted_contents=corrupted_contents,
                is_batch=True,
            )

        if not isinstance(text, str):
            message = (
                "Attack.run expected string, transcript, or list of strings, "
                f"got {type(text).__name__}"
            )
            raise TypeError(message)

        corrupted = self.glitchlings.corrupt(text)
        if not isinstance(corrupted, str):
            raise TypeError("Attack expected output type to mirror input type.")

        return self._compose_result(
            original_container=text,
            corrupted_container=corrupted,
            original_contents=[text],
            corrupted_contents=[corrupted],
            is_batch=False,
        )

    def _compose_result(
        self,
        *,
        original_container: str | Transcript | Sequence[str],
        corrupted_container: str | Transcript | Sequence[str],
        original_contents: list[str],
        corrupted_contents: list[str],
        is_batch: bool,
    ) -> AttackResult:
        if len(original_contents) != len(corrupted_contents):
            raise ValueError("Inputs and outputs must contain the same number of entries.")

        if not original_contents:
            fields = build_empty_result(
                original_container,
                corrupted_container,
                self.tokenizer_info,
                list(self.metrics.keys()),
            )
            return AttackResult(**fields)  # type: ignore[arg-type]

        batched_input_tokens, batched_input_token_ids = encode_batch(
            self.tokenizer, original_contents
        )
        batched_output_tokens, batched_output_token_ids = encode_batch(
            self.tokenizer, corrupted_contents
        )

        metric_inputs: list[str] | list[list[str]]
        metric_outputs: list[str] | list[list[str]]
        if is_batch:
            metric_inputs = batched_input_tokens
            metric_outputs = batched_output_tokens
        else:
            metric_inputs = batched_input_tokens[0]
            metric_outputs = batched_output_tokens[0]

        computed_metrics: dict[str, float | list[float]] = {}
        for name, metric_fn in self.metrics.items():
            computed_metrics[name] = metric_fn(metric_inputs, metric_outputs)

        if not is_batch:
            fields = build_single_result(
                original=cast(str, original_container),
                corrupted=cast(str, corrupted_container),
                input_tokens=batched_input_tokens[0],
                input_token_ids=batched_input_token_ids[0],
                output_tokens=batched_output_tokens[0],
                output_token_ids=batched_output_token_ids[0],
                tokenizer_info=self.tokenizer_info,
                metrics=computed_metrics,
            )
            return AttackResult(**fields)  # type: ignore[arg-type]

        fields = build_batch_result(
            original=original_container,
            corrupted=corrupted_container,
            input_tokens=batched_input_tokens,
            input_token_ids=batched_input_token_ids,
            output_tokens=batched_output_tokens,
            output_token_ids=batched_output_token_ids,
            tokenizer_info=self.tokenizer_info,
            metrics=computed_metrics,
        )
        return AttackResult(**fields)  # type: ignore[arg-type]

    def compare(
        self,
        text: str | Transcript | Sequence[str],
        *,
        tokenizers: Sequence[str | Tokenizer],
        include_self: bool = True,
    ) -> MultiAttackResult:
        """Run the attack across multiple tokenizers for side-by-side comparison."""
        if not tokenizers and not include_self:
            raise ValueError("At least one tokenizer must be provided for comparison.")

        results: dict[str, AttackResult] = {}
        order: list[str] = []
        seen: set[str] = set()

        def record(result: AttackResult) -> None:
            if result.tokenizer_info in seen:
                return
            seen.add(result.tokenizer_info)
            order.append(result.tokenizer_info)
            results[result.tokenizer_info] = result

        runner_seed = self.glitchlings.seed
        transcript_target = getattr(self.glitchlings, "transcript_target", None)

        if include_self:
            baseline = Attack(
                self.glitchlings,
                tokenizer=self.tokenizer,
                metrics=self.metrics,
                seed=runner_seed,
                transcript_target=transcript_target,
            ).run(text)
            record(baseline)

        for spec in tokenizers:
            resolved_tokenizer = resolve_tokenizer(spec)
            comparator = Attack(
                self.glitchlings,
                tokenizer=resolved_tokenizer,
                metrics=self.metrics,
                seed=runner_seed,
                transcript_target=transcript_target,
            )
            record(comparator.run(text))

        return MultiAttackResult(results=results, order=order)

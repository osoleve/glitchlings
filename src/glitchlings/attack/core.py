from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast

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


@dataclass
class AttackResult:
    original: str | Transcript
    corrupted: str | Transcript
    input_tokens: list[str] | list[list[str]]
    output_tokens: list[str] | list[list[str]]
    input_token_ids: list[int] | list[list[int]]
    output_token_ids: list[int] | list[list[int]]
    tokenizer_info: str
    metrics: dict[str, float | list[float]]


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

    def run(self, text: str | Transcript) -> AttackResult:
        """Apply corruptions and calculate metrics.

        Supports both single strings and chat transcripts. For transcripts,
        metrics are computed per-turn and returned as lists.

        Args:
            text: Input text or transcript to corrupt.

        Returns:
            AttackResult containing original, corrupted, tokens, and metrics.
        """
        # Impure: apply corruptions
        result = self.glitchlings.corrupt(text)

        # Validate type consistency
        input_is_transcript = is_transcript(text)
        output_is_transcript = is_transcript(result)
        if input_is_transcript != output_is_transcript:
            raise ValueError("Attack expected output type to mirror input type.")

        # Extract contents for tokenization
        if input_is_transcript:
            original_transcript = cast(Transcript, text)
            corrupted_transcript = cast(Transcript, result)
            original_contents = extract_transcript_contents(original_transcript)
            corrupted_contents = extract_transcript_contents(corrupted_transcript)
        else:
            assert isinstance(text, str)
            assert isinstance(result, str)
            original_str = text
            corrupted_str = result
            original_contents = [text]
            corrupted_contents = [result]

        if len(original_contents) != len(corrupted_contents):
            raise ValueError("Transcript inputs and outputs must contain the same number of turns.")

        # Handle empty transcripts using pure helper
        if not original_contents:
            # Empty transcript case - must be transcript type
            fields = build_empty_result(
                cast(Transcript, text),
                cast(Transcript, result),
                self.tokenizer_info,
                list(self.metrics.keys()),
            )
            return AttackResult(**fields)  # type: ignore[arg-type]

        # Impure: tokenize contents
        batched_input_tokens, batched_input_token_ids = encode_batch(
            self.tokenizer, original_contents
        )
        batched_output_tokens, batched_output_token_ids = encode_batch(
            self.tokenizer, corrupted_contents
        )

        # Prepare metric inputs (single vs batch)
        metric_inputs: list[str] | list[list[str]]
        metric_outputs: list[str] | list[list[str]]
        if input_is_transcript:
            metric_inputs = batched_input_tokens
            metric_outputs = batched_output_tokens
        else:
            metric_inputs = batched_input_tokens[0]
            metric_outputs = batched_output_tokens[0]

        # Impure: compute metrics
        computed_metrics: dict[str, float | list[float]] = {}
        for name, metric_fn in self.metrics.items():
            computed_metrics[name] = metric_fn(metric_inputs, metric_outputs)

        # Pure: compose result using helpers
        if not input_is_transcript:
            fields = build_single_result(
                original=original_str,
                corrupted=corrupted_str,
                input_tokens=batched_input_tokens[0],
                input_token_ids=batched_input_token_ids[0],
                output_tokens=batched_output_tokens[0],
                output_token_ids=batched_output_token_ids[0],
                tokenizer_info=self.tokenizer_info,
                metrics=computed_metrics,
            )
            return AttackResult(**fields)  # type: ignore[arg-type]

        fields = build_batch_result(
            original=original_transcript,
            corrupted=corrupted_transcript,
            input_tokens=batched_input_tokens,
            input_token_ids=batched_input_token_ids,
            output_tokens=batched_output_tokens,
            output_token_ids=batched_output_token_ids,
            tokenizer_info=self.tokenizer_info,
            metrics=computed_metrics,
        )
        return AttackResult(**fields)  # type: ignore[arg-type]

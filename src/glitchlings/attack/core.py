from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence, Tuple, Union, cast

from ..conf import DEFAULT_ATTACK_SEED
from ..util.transcripts import Transcript, is_transcript
from ..zoo.core import Gaggle, Glitchling
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
    input_tokens: List[str] | List[List[str]]
    output_tokens: List[str] | List[List[str]]
    input_token_ids: List[int] | List[List[int]]
    output_token_ids: List[int] | List[List[int]]
    tokenizer_info: str
    metrics: dict[str, float | List[float]]


class Attack:
    def __init__(
        self,
        glitchlings: Union[Glitchling, Sequence[Glitchling]],
        tokenizer: Union[str, Tokenizer, None] = None,
        metrics: Optional[Mapping[str, Metric]] = None,
        *,
        seed: int | None = None,
    ) -> None:
        """Initialize an Attack.

        Args:
            glitchlings: A single Glitchling (including Gaggle) or a list of Glitchlings.
            tokenizer: Tokenizer name (e.g. 'cl100k_base', 'bert-base-uncased'),
                       Tokenizer object, or None (defaults to whitespace).
            metrics: Dictionary of metric functions. If None, defaults are used.
            seed: Optional master seed used when building a Gaggle from a list/sequence.
                  When a Gaggle or Glitchling instance is provided directly, the seed
                  is applied to that instance to keep runs deterministic.
        """
        if isinstance(glitchlings, Glitchling):
            self.glitchlings = glitchlings
            if seed is not None:
                if isinstance(glitchlings, Gaggle):
                    glitchlings.seed = seed
                    glitchlings.sort_glitchlings()
                else:
                    glitchlings.reset_rng(seed)
        else:
            glitchling_list = self._validate_glitchling_sequence(glitchlings)
            gaggle_seed = seed if seed is not None else DEFAULT_ATTACK_SEED
            self.glitchlings = Gaggle(glitchling_list, seed=gaggle_seed)

        self.tokenizer = resolve_tokenizer(tokenizer)
        self.tokenizer_info = self._describe_tokenizer(tokenizer)

        if metrics is None:
            self.metrics: dict[str, Metric] = {
                "jensen_shannon_divergence": jensen_shannon_divergence,
                "normalized_edit_distance": normalized_edit_distance,
                "subsequence_retention": subsequence_retention,
            }
        else:
            self.metrics = dict(metrics)

    @staticmethod
    def _validate_glitchling_sequence(
        glitchlings: Sequence[Glitchling],
    ) -> list[Glitchling]:
        normalized = list(glitchlings)
        for index, entry in enumerate(normalized):
            if not isinstance(entry, Glitchling):
                message = (
                    "glitchlings sequence entries must be Glitchling instances "
                    f"(index {index})"
                )
                raise TypeError(message)
        return normalized

    def _describe_tokenizer(self, raw: Union[str, Tokenizer, None]) -> str:
        if isinstance(raw, str):
            return raw

        name = getattr(self.tokenizer, "name", None)
        if isinstance(name, str) and name:
            return name

        if raw is None:
            return self.tokenizer.__class__.__name__

        return str(raw)

    def _encode(self, text: str) -> Tuple[List[str], List[int]]:
        tokens, ids = self.tokenizer.encode(text)
        return list(tokens), list(ids)

    def _encode_batch(self, texts: List[str]) -> Tuple[List[List[str]], List[List[int]]]:
        batch_encode = getattr(self.tokenizer, "encode_batch", None)
        if callable(batch_encode):
            try:
                encoded = batch_encode(texts)
            except Exception:
                # Fall back to per-item encoding if a custom tokenizer's batch
                # implementation is missing or mis-specified.
                pass
            else:
                fast_token_batches: List[List[str]] = []
                fast_id_batches: List[List[int]] = []
                for tokens, ids in encoded:
                    fast_token_batches.append(list(tokens))
                    fast_id_batches.append(list(ids))
                return fast_token_batches, fast_id_batches

        token_batches: List[List[str]] = []
        id_batches: List[List[int]] = []
        for entry in texts:
            tokens, ids = self._encode(entry)
            token_batches.append(tokens)
            id_batches.append(ids)
        return token_batches, id_batches

    @staticmethod
    def _extract_transcript_contents(transcript: Transcript) -> List[str]:
        contents: List[str] = []
        for index, turn in enumerate(transcript):
            if not isinstance(turn, Mapping):
                raise TypeError(f"Transcript turn #{index + 1} must be a mapping.")
            content = turn.get("content")
            if not isinstance(content, str):
                raise TypeError(f"Transcript turn #{index + 1} is missing string content.")
            contents.append(content)
        return contents

    def run(self, text: str | Transcript) -> AttackResult:
        """Apply corruptions and calculate metrics, supporting transcripts as batches."""
        result = self.glitchlings.corrupt(text)

        input_is_transcript = is_transcript(text)
        output_is_transcript = is_transcript(result)
        if input_is_transcript != output_is_transcript:
            raise ValueError("Attack expected output type to mirror input type.")

        if not input_is_transcript:
            assert isinstance(text, str)  # For type checkers
            assert isinstance(result, str)
            corrupted = result

            input_tokens, input_token_ids = self._encode(text)
            output_tokens, output_token_ids = self._encode(corrupted)

            computed_metrics: dict[str, float | List[float]] = {}
            for name, metric_fn in self.metrics.items():
                value = metric_fn(input_tokens, output_tokens)
                computed_metrics[name] = cast(float, value)

            return AttackResult(
                original=text,
                corrupted=corrupted,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_token_ids=input_token_ids,
                output_token_ids=output_token_ids,
                tokenizer_info=self.tokenizer_info,
                metrics=computed_metrics,
            )

        original_transcript = cast(Transcript, text)
        corrupted_transcript = cast(Transcript, result)
        original_contents = self._extract_transcript_contents(original_transcript)
        corrupted_contents = self._extract_transcript_contents(corrupted_transcript)

        if len(original_contents) != len(corrupted_contents):
            raise ValueError("Transcript inputs and outputs must contain the same number of turns.")

        if not original_contents:
            empty_metrics: dict[str, float | List[float]] = {name: [] for name in self.metrics}
            return AttackResult(
                original=original_transcript,
                corrupted=corrupted_transcript,
                input_tokens=[],
                output_tokens=[],
                input_token_ids=[],
                output_token_ids=[],
                tokenizer_info=self.tokenizer_info,
                metrics=empty_metrics,
            )

        batched_input_tokens, batched_input_token_ids = self._encode_batch(original_contents)
        batched_output_tokens, batched_output_token_ids = self._encode_batch(corrupted_contents)

        batched_metrics: dict[str, float | List[float]] = {}
        for name, metric_fn in self.metrics.items():
            batched_metrics[name] = metric_fn(batched_input_tokens, batched_output_tokens)

        return AttackResult(
            original=original_transcript,
            corrupted=corrupted_transcript,
            input_tokens=batched_input_tokens,
            output_tokens=batched_output_tokens,
            input_token_ids=batched_input_token_ids,
            output_token_ids=batched_output_token_ids,
            tokenizer_info=self.tokenizer_info,
            metrics=batched_metrics,
        )

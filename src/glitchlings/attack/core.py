from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence, Union, cast

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
    original: str
    corrupted: str
    input_tokens: List[str]
    output_tokens: List[str]
    input_token_ids: List[int]
    output_token_ids: List[int]
    tokenizer_info: str
    metrics: dict[str, float]


class Attack:
    def __init__(
        self,
        glitchlings: Union[Glitchling, Sequence[Glitchling]],
        tokenizer: Union[str, Tokenizer, None] = None,
        metrics: Optional[Mapping[str, Metric]] = None,
    ) -> None:
        """Initialize an Attack.

        Args:
            glitchlings: A single Glitchling (including Gaggle) or a list of Glitchlings.
            tokenizer: Tokenizer name (e.g. 'cl100k_base', 'bert-base-uncased'),
                       Tokenizer object, or None (defaults to whitespace).
            metrics: Dictionary of metric functions. If None, defaults are used.
        """
        if isinstance(glitchlings, Glitchling):
            self.glitchlings = glitchlings
        elif isinstance(glitchlings, list):
            self.glitchlings = Gaggle(glitchlings)
        else:
            # Fallback for other sequences
            self.glitchlings = Gaggle(list(glitchlings))

        self.tokenizer = resolve_tokenizer(tokenizer)
        # Best effort description of tokenizer
        if isinstance(tokenizer, str):
            self.tokenizer_info = tokenizer
        elif tokenizer is None:
            self.tokenizer_info = "WhitespaceTokenizer"
        else:
            self.tokenizer_info = str(tokenizer)

        if metrics is None:
            self.metrics: dict[str, Metric] = {
                "jensen_shannon_divergence": jensen_shannon_divergence,
                "normalized_edit_distance": normalized_edit_distance,
                "subsequence_retention": subsequence_retention,
            }
        else:
            self.metrics = dict(metrics)

    def run(self, text: str) -> AttackResult:
        """Apply corruptions and calculate metrics."""
        result = self.glitchlings.corrupt(text)

        if not isinstance(result, str):
            # Handle transcript if possible, but metrics need definition.
            # For now, error or convert.
            raise ValueError("Attack currently only supports string input, not transcripts.")

        corrupted = result

        input_tokens, input_token_ids = self.tokenizer.encode(text)
        output_tokens, output_token_ids = self.tokenizer.encode(corrupted)

        # Ensure lists
        input_tokens = list(input_tokens)
        output_tokens = list(output_tokens)
        input_token_ids = list(input_token_ids)
        output_token_ids = list(output_token_ids)

        computed_metrics: dict[str, float] = {}
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

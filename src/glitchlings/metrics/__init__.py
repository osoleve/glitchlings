"""Metrics framework for analyzing glitchling effects across tokenizers.

Install the optional extras with:

    pip install glitchlings[metrics]

The metrics framework provides:

- 16+ metrics measuring edit distance, distributional changes, and structure
- Visualization tools (radar, heatmap, UMAP, sparklines)
- Batch processing and comparative analysis
- Extensible metric registration system

Example:

    >>> from glitchlings import Typogre
    >>> from glitchlings.metrics import (
    ...     compute_metrics,
    ...     create_default_registry,
    ... )
    >>> from transformers import AutoTokenizer
    >>>
    >>> glitchling = Typogre(rate=0.05)
    >>> tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    >>> registry = create_default_registry()
    >>>
    >>> text = "Hello world"
    >>> corrupted = glitchling(text)
    >>>
    >>> metrics = compute_metrics(
    ...     text_before=text,
    ...     text_after=corrupted,
    ...     tokenizer=tokenizer,
    ...     registry=registry,
    ...     tokenize_kwargs={"add_special_tokens": False},
    ... )

For full documentation, see docs/metrics/
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, MutableMapping, Sequence

from .core.tokenizers import (
    SimpleTokenizer,
    TokenizerAdapter,
    create_huggingface_adapter,
    create_tiktoken_adapter,
)
from .metrics.defaults import create_default_registry
from .metrics.registry import MetricFn, MetricRegistry, MetricSpec

__version__ = "0.1.0"


TokenizeFn = Callable[[str], Sequence[int]]


def compute_metrics(
    text_before: str,
    text_after: str,
    tokenizer: TokenizerAdapter | Callable[[str], Sequence[int]] | Any,
    registry: MetricRegistry | None = None,
    *,
    context: Mapping[str, Any] | None = None,
    tokenize_kwargs: MutableMapping[str, Any] | None = None,
) -> Mapping[str, float]:
    """Compute all metrics for ``text_before`` → ``text_after``.

    Args:
        text_before: Original text.
        text_after: Transformed text.
        tokenizer: Any object with an ``encode(str) -> Sequence[int]`` method
            (e.g., HuggingFace tokenizers, tiktoken encodings, or the bundled
            ``TokenizerAdapter`` implementations). Callables that accept a
            single ``text`` argument are also supported.
        registry: Metric registry to use. Defaults to ``create_default_registry()``.
        context: Optional mapping forwarded to metric functions.
        tokenize_kwargs: Extra keyword arguments for the tokenizer ``encode`` call
            (for example, ``{"add_special_tokens": False}``).

    Returns:
        Mapping of ``"metric_id.key"`` to floats.

    Raises:
        TypeError: If ``tokenizer`` does not provide an ``encode`` callable.
    """

    def _resolve_encoder(
        tokenizer_like: Any, extra_kwargs: MutableMapping[str, Any] | None
    ) -> TokenizeFn:
        kwargs = dict(extra_kwargs or {})

        if callable(tokenizer_like) and not hasattr(tokenizer_like, "encode"):
            if kwargs:
                return lambda text: tokenizer_like(text, **kwargs)
            return lambda text: tokenizer_like(text)

        encode = getattr(tokenizer_like, "encode", None)
        if encode is None or not callable(encode):
            raise TypeError(
                "tokenizer must be a callable or provide an encode(text, ...) method"
            )

        if kwargs:
            return lambda text: encode(text, **kwargs)
        return lambda text: encode(text)

    registry_obj = registry or create_default_registry()
    encoder = _resolve_encoder(tokenizer, tokenize_kwargs)

    tokens_before = list(encoder(text_before))
    tokens_after = list(encoder(text_after))

    return registry_obj.compute_all(tokens_before, tokens_after, context or {})


__all__ = [
    "__version__",
    "MetricFn",
    "MetricRegistry",
    "MetricSpec",
    "SimpleTokenizer",
    "TokenizerAdapter",
    "compute_metrics",
    "create_default_registry",
    "create_huggingface_adapter",
    "create_tiktoken_adapter",
]

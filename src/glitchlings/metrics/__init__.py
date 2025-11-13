"""Metrics framework for analyzing glitchling effects across tokenizers.

This is an OPTIONAL subpackage. Install with:
    pip install glitchlings[metrics]

The metrics framework provides:
- 16+ metrics measuring edit distance, distributional changes, and structure
- Visualization tools (radar, heatmap, UMAP, sparklines)
- Batch processing and comparative analysis
- Extensible metric registration system

Example:
    >>> from glitchlings import Typogre
    >>> from glitchlings.metrics import MetricRegistry, compute_metrics
    >>> from transformers import AutoTokenizer
    >>>
    >>> glitchling = Typogre(rate=0.05)
    >>> tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    >>> registry = MetricRegistry()  # Auto-loads default metrics
    >>>
    >>> text = "Hello world"
    >>> corrupted = glitchling(text)
    >>>
    >>> metrics = compute_metrics(
    ...     text, corrupted, tokenizer, registry
    ... )

For full documentation, see docs/metrics/
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__: list[str] = []

# NOTE: We use lazy imports to avoid forcing heavy dependencies
# unless users actually import from this subpackage.
# The core glitchlings library should remain lightweight.

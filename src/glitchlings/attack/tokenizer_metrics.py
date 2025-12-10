"""Tokenizer analysis metrics for evaluating tokenizer behavior.

This module provides pure functions for analyzing how a tokenizer encodes text.
Unlike the corruption metrics in metrics.py which compare before/after token
sequences, these metrics evaluate the tokenizer's encoding of a single text.

These metrics are implemented in Rust for performance. The functions here
provide a Python API with documentation and type hints.

Pure guarantees:
- No import side effects beyond stdlib
- No file IO or network calls
- Deterministic output for given inputs

Example:
    >>> from glitchlings.attack.tokenizer_metrics import compression_ratio
    >>> from glitchlings.attack.tokenization import resolve_tokenizer
    >>> tokenizer = resolve_tokenizer("o200k_base")
    >>> text = "Hello, world!"
    >>> tokens, token_ids = tokenizer.encode(text)
    >>> ratio = compression_ratio(text, tokens)
    >>> print(f"Bytes per token: {ratio:.2f}")
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, Sequence, cast

if TYPE_CHECKING:
    from .tokenization import Tokenizer

# Load Rust extension
try:
    _rust: Any = importlib.import_module("glitchlings._zoo_rust")
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guard
    raise ImportError(
        "Could not import compiled Rust extension. "
        "Please ensure the project is installed with the Rust extension built."
    ) from exc

# Rust function references
_compression_ratio = getattr(_rust, "compression_ratio")
_batch_compression_ratio = getattr(_rust, "batch_compression_ratio")
_characters_per_token = getattr(_rust, "characters_per_token")
_batch_characters_per_token = getattr(_rust, "batch_characters_per_token")
_token_entropy = getattr(_rust, "token_entropy")
_batch_token_entropy = getattr(_rust, "batch_token_entropy")
_vocabulary_utilization = getattr(_rust, "vocabulary_utilization")
_unknown_token_rate = getattr(_rust, "unknown_token_rate")
_batch_unknown_token_rate = getattr(_rust, "batch_unknown_token_rate")


# ---------------------------------------------------------------------------
# Compression Metrics
# ---------------------------------------------------------------------------


def compression_ratio(text: str, tokens: Sequence[str]) -> float:
    """Compute bytes per token - measures encoding efficiency.

    Lower values indicate the tokenizer represents the text more compactly.
    Useful for comparing tokenizer suitability across domains.

    Args:
        text: Input text to measure.
        tokens: Token strings from encoding the text.

    Returns:
        Ratio of UTF-8 bytes to token count. Returns inf for empty output.

    Example:
        >>> text = "Hello, world!"
        >>> tokens, _ = tokenizer.encode(text)
        >>> ratio = compression_ratio(text, tokens)
    """
    return cast(float, _compression_ratio(text, list(tokens)))


def batch_compression_ratio(
    texts: Sequence[str],
    token_batches: Sequence[Sequence[str]],
) -> list[float]:
    """Compute compression ratios for a batch of texts.

    Args:
        texts: Input texts to measure.
        token_batches: Token sequences from encoding each text.

    Returns:
        List of compression ratios for each text.
    """
    return cast(
        list[float],
        _batch_compression_ratio(list(texts), [list(tokens) for tokens in token_batches]),
    )


def characters_per_token(text: str, tokens: Sequence[str]) -> float:
    """Compute average characters per token - simpler efficiency measure.

    Higher values mean fewer tokens needed. Unlike compression_ratio,
    this ignores UTF-8 encoding costs, so it's more intuitive for
    ASCII-heavy text but less accurate for multilingual content.

    Args:
        text: Input text to measure.
        tokens: Token strings from encoding the text.

    Returns:
        Ratio of character count to token count. Returns inf for empty output.
    """
    return cast(float, _characters_per_token(text, list(tokens)))


def batch_characters_per_token(
    texts: Sequence[str],
    token_batches: Sequence[Sequence[str]],
) -> list[float]:
    """Compute characters per token for a batch of texts.

    Args:
        texts: Input texts to measure.
        token_batches: Token sequences from encoding each text.

    Returns:
        List of characters-per-token ratios for each text.
    """
    return cast(
        list[float],
        _batch_characters_per_token(list(texts), [list(tokens) for tokens in token_batches]),
    )


# ---------------------------------------------------------------------------
# Token Distribution Metrics
# ---------------------------------------------------------------------------


def token_entropy(tokens: Sequence[str]) -> float:
    """Compute Shannon entropy of token distribution.

    Higher entropy means more uniform token usage (less repetition).
    Useful for understanding how "spread out" the vocabulary usage is.

    Args:
        tokens: Token sequence to analyze.

    Returns:
        Entropy in bits. Returns 0.0 for empty input.

    Example:
        >>> tokens = ["the", "cat", "sat", "on", "the", "mat"]
        >>> entropy = token_entropy(tokens)
    """
    return cast(float, _token_entropy(list(tokens)))


def batch_token_entropy(token_batches: Sequence[Sequence[str]]) -> list[float]:
    """Compute token entropy for a batch of token sequences.

    Args:
        token_batches: Token sequences to analyze.

    Returns:
        List of entropy values for each sequence.
    """
    return cast(
        list[float],
        _batch_token_entropy([list(tokens) for tokens in token_batches]),
    )


# ---------------------------------------------------------------------------
# Vocabulary Analysis
# ---------------------------------------------------------------------------


def vocabulary_utilization(
    tokens: Sequence[str],
    token_ids: Sequence[int],
) -> dict[str, float]:
    """Analyze vocabulary usage patterns.

    Provides insights into how the tokenizer uses its vocabulary for a
    given text. Useful for identifying domain mismatches where the
    tokenizer may be using unusual or sparse regions of its vocabulary.

    Args:
        tokens: Token strings from encoding.
        token_ids: Corresponding token IDs.

    Returns:
        Dictionary with:
        - unique_ratio: fraction of tokens that are unique (type/token ratio)
        - repetition_rate: 1 - unique_ratio (how much token reuse)
        - max_id: highest token ID used (hints at vocabulary region)
        - id_spread: stddev of IDs (are we using clustered or spread vocab?)

    Example:
        >>> tokens, ids = tokenizer.encode("The quick brown fox")
        >>> stats = vocabulary_utilization(tokens, ids)
        >>> print(f"Unique ratio: {stats['unique_ratio']:.2%}")
    """
    result = _vocabulary_utilization(list(tokens), list(token_ids))
    return dict(result)


# ---------------------------------------------------------------------------
# Unknown Token Detection
# ---------------------------------------------------------------------------


DEFAULT_UNKNOWN_MARKERS = ("[UNK]", "<unk>", "�", "\ufffd")


def unknown_token_rate(
    tokens: Sequence[str],
    *,
    unknown_markers: tuple[str, ...] | None = None,
) -> float:
    """Compute fraction of tokens that appear to be unknown/fallback tokens.

    Different tokenizers use different markers for OOV (out-of-vocabulary)
    handling. High rates suggest the tokenizer's vocabulary doesn't cover
    this domain well.

    Also detects byte fallback tokens (e.g., "<0xFF>") which indicate
    characters that couldn't be represented by the vocabulary.

    Args:
        tokens: Token sequence to analyze.
        unknown_markers: Tuple of strings that indicate unknown tokens.
            Defaults to common markers like "[UNK]", "<unk>", "�".

    Returns:
        Fraction of tokens that are unknown/fallback tokens.

    Example:
        >>> tokens, _ = tokenizer.encode("日本語テスト")
        >>> rate = unknown_token_rate(tokens)
        >>> if rate > 0.1:
        ...     print("Warning: high unknown token rate")
    """
    markers = list(unknown_markers) if unknown_markers is not None else None
    return cast(float, _unknown_token_rate(list(tokens), markers))


def batch_unknown_token_rate(
    token_batches: Sequence[Sequence[str]],
    *,
    unknown_markers: tuple[str, ...] | None = None,
) -> list[float]:
    """Compute unknown token rates for a batch of token sequences.

    Args:
        token_batches: Token sequences to analyze.
        unknown_markers: Tuple of strings that indicate unknown tokens.

    Returns:
        List of unknown token rates for each sequence.
    """
    markers = list(unknown_markers) if unknown_markers is not None else None
    return cast(
        list[float],
        _batch_unknown_token_rate([list(tokens) for tokens in token_batches], markers),
    )


# ---------------------------------------------------------------------------
# Convenience Functions (using Tokenizer directly)
# ---------------------------------------------------------------------------


def analyze_tokenizer(
    text: str,
    tokenizer: "Tokenizer",
    *,
    unknown_markers: tuple[str, ...] | None = None,
) -> dict[str, float]:
    """Comprehensive tokenizer analysis for a text.

    Convenience function that encodes the text and computes all tokenizer
    metrics at once.

    Args:
        text: Input text to analyze.
        tokenizer: Tokenizer to evaluate.
        unknown_markers: Tuple of strings that indicate unknown tokens.

    Returns:
        Dictionary with all tokenizer metrics:
        - compression_ratio: bytes per token
        - characters_per_token: chars per token
        - token_entropy: Shannon entropy of token distribution
        - unknown_token_rate: fraction of unknown tokens
        - unique_ratio: type/token ratio
        - repetition_rate: 1 - unique_ratio
        - max_id: highest token ID
        - id_spread: standard deviation of token IDs
        - token_count: total number of tokens

    Example:
        >>> from glitchlings.attack.tokenization import resolve_tokenizer
        >>> tokenizer = resolve_tokenizer("o200k_base")
        >>> stats = analyze_tokenizer("Hello, world!", tokenizer)
        >>> for key, value in stats.items():
        ...     print(f"{key}: {value:.4f}")
    """
    if not text:
        return {
            "compression_ratio": 0.0,
            "characters_per_token": 0.0,
            "token_entropy": 0.0,
            "unknown_token_rate": 0.0,
            "unique_ratio": 0.0,
            "repetition_rate": 0.0,
            "max_id": 0.0,
            "id_spread": 0.0,
            "token_count": 0.0,
        }

    tokens, token_ids = tokenizer.encode(text)

    # Compute all metrics
    comp_ratio = compression_ratio(text, tokens)
    chars_per_token = characters_per_token(text, tokens)
    entropy = token_entropy(tokens)
    unk_rate = unknown_token_rate(tokens, unknown_markers=unknown_markers)
    vocab_stats = vocabulary_utilization(tokens, token_ids)

    return {
        "compression_ratio": comp_ratio,
        "characters_per_token": chars_per_token,
        "token_entropy": entropy,
        "unknown_token_rate": unk_rate,
        "unique_ratio": vocab_stats["unique_ratio"],
        "repetition_rate": vocab_stats["repetition_rate"],
        "max_id": vocab_stats["max_id"],
        "id_spread": vocab_stats["id_spread"],
        "token_count": float(len(tokens)),
    }


__all__ = [
    # Core metrics
    "compression_ratio",
    "batch_compression_ratio",
    "characters_per_token",
    "batch_characters_per_token",
    "token_entropy",
    "batch_token_entropy",
    "vocabulary_utilization",
    "unknown_token_rate",
    "batch_unknown_token_rate",
    # Convenience
    "analyze_tokenizer",
    # Constants
    "DEFAULT_UNKNOWN_MARKERS",
]

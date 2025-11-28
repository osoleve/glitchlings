"""Pure encoding utilities for tokenization.

This module contains pure functions for encoding text using tokenizers.
The functions here do not resolve tokenizers or perform IO - they operate
on already-resolved Tokenizer instances.

Pure guarantees:
- No import side effects beyond stdlib
- No file IO or network calls
- No environment variable access
- Deterministic output for given inputs

The impure tokenizer resolution lives in tokenization.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .tokenization import Tokenizer


def encode_single(
    tokenizer: "Tokenizer",
    text: str,
) -> tuple[list[str], list[int]]:
    """Encode a single text string into tokens and IDs.

    This is a thin wrapper that ensures list output types.

    Args:
        tokenizer: A resolved tokenizer instance.
        text: Text to encode.

    Returns:
        Tuple of (tokens, token_ids) as lists.
    """
    tokens, ids = tokenizer.encode(text)
    return list(tokens), list(ids)


def encode_batch(
    tokenizer: "Tokenizer",
    texts: Sequence[str],
) -> tuple[list[list[str]], list[list[int]]]:
    """Encode multiple texts into batched tokens and IDs.

    Attempts to use the tokenizer's batch_encode method if available,
    otherwise falls back to per-item encoding.

    Args:
        tokenizer: A resolved tokenizer instance.
        texts: Sequence of texts to encode.

    Returns:
        Tuple of (token_batches, id_batches) as nested lists.
    """
    # Try batch encoding if available
    batch_encode = getattr(tokenizer, "encode_batch", None)
    if callable(batch_encode):
        encoded = batch_encode(texts)
        token_batches: list[list[str]] = []
        id_batches: list[list[int]] = []
        for tokens, ids in encoded:
            token_batches.append(list(tokens))
            id_batches.append(list(ids))
        return token_batches, id_batches

    # Fallback: encode each text individually
    token_batches_fallback: list[list[str]] = []
    id_batches_fallback: list[list[int]] = []
    for entry in texts:
        tokens, ids = encode_single(tokenizer, entry)
        token_batches_fallback.append(tokens)
        id_batches_fallback.append(ids)
    return token_batches_fallback, id_batches_fallback


def describe_tokenizer(
    tokenizer: "Tokenizer",
    raw_spec: "str | Tokenizer | None",
) -> str:
    """Generate a human-readable description of a tokenizer.

    Args:
        tokenizer: The resolved tokenizer instance.
        raw_spec: The original specification used to create/resolve the tokenizer.

    Returns:
        A descriptive string identifying the tokenizer.
    """
    # If the raw spec was a string, use it directly
    if isinstance(raw_spec, str):
        return raw_spec

    # Try to get a name attribute
    name = getattr(tokenizer, "name", None)
    if isinstance(name, str) and name:
        return name

    # For None spec, use the class name
    if raw_spec is None:
        return tokenizer.__class__.__name__

    # Fallback to string representation
    return str(raw_spec)


__all__ = [
    "describe_tokenizer",
    "encode_batch",
    "encode_single",
]

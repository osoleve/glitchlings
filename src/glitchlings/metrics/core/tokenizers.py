"""Tokenizer adapters for metrics framework.

This module provides a protocol-based adapter system for different tokenizers,
allowing metrics to be computed across multiple tokenization schemes.

Supported tokenizers:
- HuggingFace transformers (AutoTokenizer)
- OpenAI tiktoken
- Simple whitespace tokenizer
- Custom tokenizers (implement TokenizerAdapter protocol)
"""

from __future__ import annotations

import hashlib
from abc import abstractmethod
from typing import Protocol, Sequence


class TokenizerAdapter(Protocol):
    """Protocol for tokenizer adapters.

    All tokenizers must implement this interface to work with the metrics
    framework. The adapter wraps the underlying tokenizer and provides a
    uniform API.

    Example:
        >>> class MyTokenizer:
        ...     def encode(self, text: str) -> list[int]:
        ...         return [ord(c) for c in text]
        ...
        ...     @property
        ...     def name(self) -> str:
        ...         return "character-tokenizer"
        ...
        ...     @property
        ...     def vocab_size(self) -> int:
        ...         return 256
        ...
        ...     def vocab_hash(self) -> str:
        ...         return hashlib.sha256(b"char-vocab").hexdigest()[:16]
    """

    @abstractmethod
    def encode(self, text: str) -> Sequence[int]:
        """Encode text into token IDs.

        Args:
            text: Input text to tokenize

        Returns:
            Sequence of integer token IDs

        Note:
            - Should handle empty strings gracefully
            - Should be deterministic (same text -> same tokens)
            - May raise exceptions for invalid inputs
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifying this tokenizer.

        Returns:
            String identifier (e.g., "gpt2", "bert-base-uncased")

        Note:
            - Should include version info if relevant
            - Used for grouping results by tokenizer
        """
        ...

    @property
    @abstractmethod
    def vocab_size(self) -> int:
        """Size of the vocabulary.

        Returns:
            Number of tokens in vocabulary

        Note:
            - May be approximate for unbounded tokenizers
            - Used for validation and metadata
        """
        ...

    @abstractmethod
    def vocab_hash(self) -> str:
        """Compute a hash of the vocabulary for versioning.

        Returns:
            Hex string (e.g., first 16 chars of SHA256)

        Purpose:
            - Detect vocabulary changes across runs
            - Ensure reproducibility
            - Cache invalidation

        Note:
            - Should be deterministic
            - Should change if vocabulary changes
            - Can be expensive; results may be cached
        """
        ...


class SimpleTokenizer:
    """Simple whitespace-based tokenizer for testing and demos.

    Splits on whitespace and assigns sequential integer IDs.

    Example:
        >>> tok = SimpleTokenizer()
        >>> tok.encode("hello world")
        [0, 1]
        >>> tok.encode("hello world hello")
        [0, 1, 0]
    """

    def __init__(self) -> None:
        """Initialize simple tokenizer."""
        self._vocab: dict[str, int] = {}
        self._next_id = 0

    def encode(self, text: str) -> list[int]:
        """Encode text by splitting on whitespace.

        Args:
            text: Input text

        Returns:
            List of token IDs
        """
        if not text:
            return []

        tokens = text.split()
        ids = []

        for token in tokens:
            if token not in self._vocab:
                self._vocab[token] = self._next_id
                self._next_id += 1
            ids.append(self._vocab[token])

        return ids

    @property
    def name(self) -> str:
        """Return tokenizer name."""
        return "simple-whitespace"

    @property
    def vocab_size(self) -> int:
        """Return current vocabulary size."""
        return len(self._vocab)

    def vocab_hash(self) -> str:
        """Compute vocabulary hash.

        Returns:
            SHA256 hash of sorted vocabulary
        """
        vocab_str = ",".join(sorted(self._vocab.keys()))
        return hashlib.sha256(vocab_str.encode()).hexdigest()[:16]


def create_huggingface_adapter(model_name: str) -> TokenizerAdapter:
    """Create a HuggingFace tokenizer adapter.

    Args:
        model_name: Model identifier (e.g., "gpt2", "bert-base-uncased")

    Returns:
        TokenizerAdapter wrapping HuggingFace AutoTokenizer

    Raises:
        ImportError: If transformers is not installed
        ValueError: If model not found

    Example:
        >>> adapter = create_huggingface_adapter("gpt2")
        >>> tokens = adapter.encode("Hello world")
        >>> print(adapter.name)
        gpt2
    """
    try:
        from transformers import AutoTokenizer
    except ImportError as e:
        raise ImportError(
            "HuggingFace transformers not installed. Install with: pip install transformers"
        ) from e

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    class HuggingFaceAdapter:
        """Adapter for HuggingFace tokenizers."""

        def __init__(self, hf_tokenizer, model_id: str):
            self._tokenizer = hf_tokenizer
            self._model_id = model_id

        def encode(self, text: str) -> list[int]:
            """Encode text using HuggingFace tokenizer."""
            if not text:
                return []
            return self._tokenizer.encode(text, add_special_tokens=False)

        @property
        def name(self) -> str:
            """Return model name."""
            return self._model_id

        @property
        def vocab_size(self) -> int:
            """Return vocabulary size."""
            return len(self._tokenizer)

        def vocab_hash(self) -> str:
            """Compute vocabulary hash.

            For HuggingFace, we hash the vocab.json content if available,
            otherwise use model name + vocab size.
            """
            # Simple hash based on vocab size and model name
            # In production, could hash actual vocab file
            content = f"{self._model_id}:{self.vocab_size}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

    return HuggingFaceAdapter(tokenizer, model_name)


def create_tiktoken_adapter(encoding_name: str = "cl100k_base") -> TokenizerAdapter:
    """Create a tiktoken (OpenAI) tokenizer adapter.

    Args:
        encoding_name: Encoding name (e.g., "cl100k_base" for GPT-4,
                      "p50k_base" for older models)

    Returns:
        TokenizerAdapter wrapping tiktoken encoding

    Raises:
        ImportError: If tiktoken is not installed

    Example:
        >>> adapter = create_tiktoken_adapter("cl100k_base")
        >>> tokens = adapter.encode("Hello world")
        >>> print(adapter.name)
        tiktoken-cl100k_base
    """
    try:
        import tiktoken
    except ImportError as e:
        raise ImportError("tiktoken not installed. Install with: pip install tiktoken") from e

    encoding = tiktoken.get_encoding(encoding_name)

    class TiktokenAdapter:
        """Adapter for OpenAI tiktoken."""

        def __init__(self, enc, enc_name: str):
            self._encoding = enc
            self._encoding_name = enc_name

        def encode(self, text: str) -> list[int]:
            """Encode text using tiktoken."""
            if not text:
                return []
            return self._encoding.encode(text)

        @property
        def name(self) -> str:
            """Return encoding name."""
            return f"tiktoken-{self._encoding_name}"

        @property
        def vocab_size(self) -> int:
            """Return vocabulary size.

            Note: tiktoken has a large vocab (~100k for cl100k_base)
            """
            return self._encoding.n_vocab

        def vocab_hash(self) -> str:
            """Compute vocabulary hash.

            For tiktoken, hash the encoding name (encodings are versioned).
            """
            content = f"tiktoken:{self._encoding_name}:{self.vocab_size}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

    return TiktokenAdapter(encoding, encoding_name)


__all__ = [
    "TokenizerAdapter",
    "SimpleTokenizer",
    "create_huggingface_adapter",
    "create_tiktoken_adapter",
]

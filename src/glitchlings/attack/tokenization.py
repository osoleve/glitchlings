from __future__ import annotations

import importlib.util
import zlib
from typing import Any, Protocol, Sequence

DEFAULT_TIKTOKEN_ENCODINGS = ("o200k_base", "cl100k_base")


class Tokenizer(Protocol):
    def encode(self, text: str) -> tuple[list[str], list[int]]: ...

    def decode(self, tokens: Sequence[str]) -> str: ...


class WhitespaceTokenizer:
    def encode(self, text: str) -> tuple[list[str], list[int]]:
        tokens = text.split()
        # Synthetic IDs based on adler32 hash for stability
        ids = [zlib.adler32(t.encode("utf-8")) & 0xFFFFFFFF for t in tokens]
        return tokens, ids

    def decode(self, tokens: Sequence[str]) -> str:
        return " ".join(tokens)

    def encode_batch(self, texts: Sequence[str]) -> list[tuple[list[str], list[int]]]:
        return [self.encode(text) for text in texts]


class TiktokenTokenizer:
    def __init__(self, model_name: str):
        import tiktoken

        self.name = model_name
        try:
            self.enc = tiktoken.get_encoding(model_name)
        except ValueError:
            self.enc = tiktoken.encoding_for_model(model_name)

    def encode(self, text: str) -> tuple[list[str], list[int]]:
        ids = self.enc.encode(text)
        tokens = [
            self.enc.decode_single_token_bytes(i).decode("utf-8", errors="replace") for i in ids
        ]
        return tokens, ids

    def decode(self, tokens: Sequence[str], sep: str = "") -> str:
        return sep.join(tokens)

    def encode_batch(self, texts: Sequence[str]) -> list[tuple[list[str], list[int]]]:
        id_batches = [list(batch) for batch in self.enc.encode_batch(list(texts))]
        token_batches: list[list[str]] = []
        for ids in id_batches:
            token_batches.append(
                [
                    self.enc.decode_single_token_bytes(i).decode("utf-8", errors="replace")
                    for i in ids
                ]
            )
        return list(zip(token_batches, id_batches))


class HuggingFaceTokenizerWrapper:
    def __init__(self, tokenizer_obj: Any, *, unknown_token: str = "[UNK]"):
        self.tokenizer = tokenizer_obj
        self.unknown_token = unknown_token

    def encode(self, text: str) -> tuple[list[str], list[int]]:
        # tokenizers.Tokenizer.encode returns an Encoding object
        encoding = self.tokenizer.encode(text)
        return encoding.tokens, encoding.ids

    def decode(self, tokens: Sequence[str]) -> str:
        # Use the tokenizer's decode method to properly handle model-specific
        # artifacts (e.g., "##" for WordPiece, "Ġ" for BPE).
        # Convert tokens to IDs first, then decode.
        try:
            token_ids = [self.tokenizer.token_to_id(token) for token in tokens]
            # Filter out None values (tokens not in vocabulary)
            valid_ids = [tid for tid in token_ids if tid is not None]
            if valid_ids:
                result: str = self.tokenizer.decode(valid_ids)
                return result
        except (AttributeError, TypeError):
            pass
        # Fallback: join with spaces, replacing unknown tokens
        decoded_tokens = []
        for token in tokens:
            token_id = None
            try:
                token_id = self.tokenizer.token_to_id(token)
            except (AttributeError, TypeError):
                pass
            if token_id is None:
                decoded_tokens.append(self.unknown_token)
            else:
                decoded_tokens.append(token)
        return " ".join(decoded_tokens)

    def encode_batch(self, texts: Sequence[str]) -> list[tuple[list[str], list[int]]]:
        encodings = self.tokenizer.encode_batch(list(texts))
        return [(encoding.tokens, encoding.ids) for encoding in encodings]


def list_available_tokenizers() -> list[str]:
    """List tokenizer names that can be resolved.

    Returns a list of known tokenizer names including:
    - Tiktoken encodings (if tiktoken is installed)
    - A note about HuggingFace tokenizers (if tokenizers is installed)
    - 'whitespace' (always available)

    Returns:
        List of available tokenizer names/descriptions.
    """
    available: list[str] = []

    if importlib.util.find_spec("tiktoken"):
        import tiktoken

        # Add known tiktoken encodings
        for encoding in DEFAULT_TIKTOKEN_ENCODINGS:
            try:
                tiktoken.get_encoding(encoding)
                available.append(encoding)
            except ValueError:
                pass
        # Add common model names
        available.extend(["gpt-4", "gpt-4o", "gpt-3.5-turbo"])

    if importlib.util.find_spec("tokenizers"):
        available.append("<any HuggingFace tokenizer name>")

    available.append("whitespace")
    return available


def resolve_tokenizer(tokenizer: str | Tokenizer | None) -> Tokenizer:
    """Resolve a tokenizer specification to a Tokenizer instance.

    Args:
        tokenizer: One of:
            - None: Use default tokenizer (tiktoken o200k_base, or whitespace)
            - str: Tokenizer name (tiktoken encoding, model name, or HF tokenizer)
            - Tokenizer: Pass through as-is

    Returns:
        A Tokenizer instance.

    Raises:
        ValueError: If string tokenizer cannot be resolved.
    """
    if tokenizer is None:
        return _default_tokenizer()

    if isinstance(tokenizer, str):
        if importlib.util.find_spec("tiktoken"):
            import tiktoken

            try:
                # Check if valid tiktoken encoding/model
                try:
                    tiktoken.get_encoding(tokenizer)
                    return TiktokenTokenizer(tokenizer)
                except ValueError:
                    try:
                        tiktoken.encoding_for_model(tokenizer)
                        return TiktokenTokenizer(tokenizer)
                    except ValueError:
                        pass
            except ImportError:
                pass

        if importlib.util.find_spec("tokenizers"):
            from tokenizers import Tokenizer

            try:
                return HuggingFaceTokenizerWrapper(Tokenizer.from_pretrained(tokenizer))
            except Exception:
                pass

        available = list_available_tokenizers()
        raise ValueError(
            f"Could not resolve tokenizer: {tokenizer!r}. "
            f"Available: {', '.join(available)}"
        )

    # Check if it is a HuggingFace tokenizer object
    if importlib.util.find_spec("tokenizers"):
        from tokenizers import Tokenizer as HFTokenizer

        if isinstance(tokenizer, HFTokenizer):
            return HuggingFaceTokenizerWrapper(tokenizer)

    return tokenizer


def _default_tokenizer() -> Tokenizer:
    """Select a modern, lightweight tokenizer with graceful fallbacks."""
    if importlib.util.find_spec("tiktoken"):
        import tiktoken

        for encoding in DEFAULT_TIKTOKEN_ENCODINGS:
            try:
                tiktoken.get_encoding(encoding)
                return TiktokenTokenizer(encoding)
            except ValueError:
                continue

    return WhitespaceTokenizer()


__all__ = [
    "DEFAULT_TIKTOKEN_ENCODINGS",
    "HuggingFaceTokenizerWrapper",
    "TiktokenTokenizer",
    "Tokenizer",
    "WhitespaceTokenizer",
    "list_available_tokenizers",
    "resolve_tokenizer",
]

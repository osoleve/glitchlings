from __future__ import annotations

import importlib.util
import zlib
from functools import lru_cache
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
    def __init__(self, tokenizer_obj: Any):
        self.tokenizer = tokenizer_obj

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
        # Fallback: simple join without any replacements
        return "".join(tokens)

    def encode_batch(self, texts: Sequence[str]) -> list[tuple[list[str], list[int]]]:
        encodings = self.tokenizer.encode_batch(list(texts))
        return [(encoding.tokens, encoding.ids) for encoding in encodings]


@lru_cache(maxsize=32)
def _resolve_tokenizer_from_string(tokenizer_name: str) -> Tokenizer:
    """Cached tokenizer resolution for string names.

    This cache dramatically improves performance by avoiding repeated
    calls to Tokenizer.from_pretrained() for HuggingFace tokenizers,
    which can take 50-500ms per call.
    """
    if importlib.util.find_spec("tiktoken"):
        import tiktoken

        try:
            # Check if valid tiktoken encoding/model
            try:
                tiktoken.get_encoding(tokenizer_name)
                return TiktokenTokenizer(tokenizer_name)
            except ValueError:
                try:
                    tiktoken.encoding_for_model(tokenizer_name)
                    return TiktokenTokenizer(tokenizer_name)
                except (ValueError, KeyError):
                    pass
        except ImportError:
            pass

    if importlib.util.find_spec("tokenizers"):
        from tokenizers import Tokenizer

        try:
            return HuggingFaceTokenizerWrapper(Tokenizer.from_pretrained(tokenizer_name))
        except Exception:
            pass

    raise ValueError(f"Could not resolve tokenizer: {tokenizer_name}")


def resolve_tokenizer(tokenizer: str | Tokenizer | None) -> Tokenizer:
    if tokenizer is None:
        return _default_tokenizer()

    if isinstance(tokenizer, str):
        return _resolve_tokenizer_from_string(tokenizer)

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
    "resolve_tokenizer",
]

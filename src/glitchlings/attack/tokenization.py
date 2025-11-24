import importlib.util
import zlib
from typing import Any, List, Protocol, Sequence, Tuple, Union


class Tokenizer(Protocol):
    def encode(self, text: str) -> Tuple[List[str], List[int]]: ...

    def decode(self, tokens: Sequence[str]) -> str: ...


class WhitespaceTokenizer:
    def encode(self, text: str) -> Tuple[List[str], List[int]]:
        tokens = text.split()
        # Synthetic IDs based on adler32 hash for stability
        ids = [zlib.adler32(t.encode("utf-8")) & 0xFFFFFFFF for t in tokens]
        return tokens, ids

    def decode(self, tokens: Sequence[str]) -> str:
        return " ".join(tokens)


class TiktokenTokenizer:
    def __init__(self, model_name: str):
        import tiktoken

        try:
            self.enc = tiktoken.get_encoding(model_name)
        except ValueError:
            self.enc = tiktoken.encoding_for_model(model_name)

    def encode(self, text: str) -> Tuple[List[str], List[int]]:
        ids = self.enc.encode(text)
        tokens = [
            self.enc.decode_single_token_bytes(i).decode("utf-8", errors="replace") for i in ids
        ]
        return tokens, ids

    def decode(self, tokens: Sequence[str], sep: str = "") -> str:
        return sep.join(tokens)


class HuggingFaceTokenizerWrapper:
    def __init__(self, tokenizer_obj: Any):
        self.tokenizer = tokenizer_obj

    def encode(self, text: str) -> Tuple[List[str], List[int]]:
        # tokenizers.Tokenizer.encode returns an Encoding object
        encoding = self.tokenizer.encode(text)
        return encoding.tokens, encoding.ids

    def decode(self, tokens: Sequence[str]) -> str:
        # Best effort
        return "".join(tokens).replace("##", "")


def resolve_tokenizer(tokenizer: Union[str, Tokenizer, None]) -> Tokenizer:
    if tokenizer is None:
        return WhitespaceTokenizer()

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

        raise ValueError(f"Could not resolve tokenizer: {tokenizer}")

    # Check if it is a HuggingFace tokenizer object
    if importlib.util.find_spec("tokenizers"):
        from tokenizers import Tokenizer as HFTokenizer

        if isinstance(tokenizer, HFTokenizer):
            return HuggingFaceTokenizerWrapper(tokenizer)

    return tokenizer

import importlib.util
from typing import Any, List, Tuple

import pytest

from glitchlings.attack import Attack
from glitchlings.zoo.core import AttackWave, Glitchling


class MockGlitchling(Glitchling):
    def __init__(self, name="mock"):
        super().__init__(name, self.corrupt_func, AttackWave.WORD)

    def corrupt_func(self, text: str, **kwargs: Any) -> str:
        return text + "!"


def test_attack_initialization():
    glitchling = MockGlitchling()
    attack = Attack([glitchling])
    assert attack.glitchlings is not None


def test_attack_run_basic():
    glitchling = MockGlitchling()
    attack = Attack([glitchling])
    result = attack.run("hello world")

    assert result.original == "hello world"
    assert result.corrupted == "hello world!"
    assert result.input_tokens == ["hello", "world"]  # Default whitespace tokenizer
    assert result.output_tokens == ["hello", "world!"]
    assert len(result.input_token_ids) == 2
    assert len(result.output_token_ids) == 2

    # Check default metrics
    assert "jensen_shannon_divergence" in result.metrics
    assert "normalized_edit_distance" in result.metrics
    assert "subsequence_retention" in result.metrics


def test_custom_metrics():
    glitchling = MockGlitchling()

    def my_metric(orig, corr):
        return 42.0

    attack = Attack([glitchling], metrics={"my_metric": my_metric})
    result = attack.run("test")
    assert result.metrics["my_metric"] == 42.0
    assert "jensen_shannon_divergence" not in result.metrics


def test_custom_tokenizer():
    class CharTokenizer:
        def encode(self, text: str) -> Tuple[List[str], List[int]]:
            return list(text), [ord(c) for c in text]

        def decode(self, tokens: List[str]) -> str:
            return "".join(tokens)

    glitchling = MockGlitchling()
    attack = Attack([glitchling], tokenizer=CharTokenizer())
    result = attack.run("abc")

    assert result.input_tokens == ["a", "b", "c"]
    assert result.output_tokens == ["a", "b", "c", "!"]
    assert result.input_token_ids == [97, 98, 99]


def test_tiktoken_integration():
    if not importlib.util.find_spec("tiktoken"):
        pytest.skip("tiktoken not installed")

    glitchling = MockGlitchling()
    # Assuming string identifier for tiktoken
    attack = Attack([glitchling], tokenizer="gpt2")
    result = attack.run("hello world")

    assert len(result.input_tokens) > 0
    assert isinstance(result.input_tokens[0], str)
    assert len(result.input_token_ids) > 0
    assert isinstance(result.input_token_ids[0], int)


def test_tokenizers_integration():
    if not importlib.util.find_spec("tokenizers"):
        pytest.skip("tokenizers not installed")

    from tokenizers import Tokenizer, models, pre_tokenizers

    # Create a simple whitespace tokenizer using the library
    tokenizer_obj = Tokenizer(
        models.WordLevel(vocab={"hello": 0, "world": 1, "!": 2, "[UNK]": 3}, unk_token="[UNK]")
    )
    tokenizer_obj.pre_tokenizer = pre_tokenizers.Whitespace()

    glitchling = MockGlitchling()
    attack = Attack([glitchling], tokenizer=tokenizer_obj)
    result = attack.run("hello world")

    assert result.input_tokens == ["hello", "world"]
    assert len(result.input_token_ids) == 2


def test_batch_metrics():
    from glitchlings.attack.metrics import (
        jensen_shannon_divergence,
        normalized_edit_distance,
        subsequence_retention,
    )

    inputs = [["a", "b"], ["c"]]
    outputs = [["a", "c"], ["c"]]

    jsd = jensen_shannon_divergence(inputs, outputs)
    ned = normalized_edit_distance(inputs, outputs)
    sr = subsequence_retention(inputs, outputs)

    assert len(jsd) == 2
    assert len(ned) == 2
    assert len(sr) == 2

    assert jsd[1] == 0.0
    assert ned[1] == 0.0
    assert sr[1] == 1.0

    assert jsd[0] > 0.0
    assert ned[0] > 0.0
    assert sr[0] < 1.0

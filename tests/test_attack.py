import importlib.util
from typing import Any, List, Tuple

import pytest

from glitchlings.attack import Attack
from glitchlings.conf import DEFAULT_ATTACK_SEED
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

    expected_tokens, expected_ids = attack.tokenizer.encode("hello world")
    output_tokens, output_ids = attack.tokenizer.encode("hello world!")

    assert result.original == "hello world"
    assert result.corrupted == "hello world!"
    assert result.input_tokens == expected_tokens
    assert result.output_tokens == output_tokens
    assert result.input_token_ids == expected_ids
    assert result.output_token_ids == output_ids

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


def test_attack_transcript_is_treated_as_batch():
    glitchling = MockGlitchling()
    attack = Attack([glitchling])

    transcript = [
        {"role": "user", "content": "hello world"},
        {"role": "assistant", "content": "goodbye"},
    ]

    result = attack.run(transcript)

    assert isinstance(result.corrupted, list)
    assert len(result.input_tokens) == len(transcript)
    assert len(result.output_tokens) == len(transcript)

    jsd = result.metrics["jensen_shannon_divergence"]
    assert isinstance(jsd, list)
    assert len(jsd) == len(transcript)


def test_attack_empty_transcript_returns_empty_metrics():
    glitchling = MockGlitchling()
    attack = Attack([glitchling])

    transcript: list[dict[str, str]] = []

    result = attack.run(transcript)

    assert result.input_tokens == []
    assert result.output_tokens == []
    assert result.metrics["jensen_shannon_divergence"] == []
    assert result.metrics["normalized_edit_distance"] == []
    assert result.metrics["subsequence_retention"] == []


def test_attack_rejects_invalid_glitchling_specs():
    """Invalid glitchling names in specs raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        Attack([MockGlitchling(), "nope"])

    with pytest.raises(TypeError):
        Attack((MockGlitchling(), None))  # type: ignore[arg-type]


def test_attack_accepts_seed_for_gaggle_creation():
    glitchlings = [MockGlitchling("a"), MockGlitchling("b")]
    attack = Attack(glitchlings, seed=999)

    assert attack.glitchlings.seed == 999

    default_seed_attack = Attack(glitchlings)
    assert default_seed_attack.glitchlings.seed == DEFAULT_ATTACK_SEED


def test_attack_applies_seed_to_existing_gaggle():
    base = Attack([MockGlitchling("a"), MockGlitchling("b")]).glitchlings
    seeded_attack = Attack(base, seed=42)

    assert seeded_attack.glitchlings.seed == 42


@pytest.mark.parametrize("override_seed", [None, 42])
def test_attack_clones_existing_gaggle_before_seeding(override_seed):
    base = Attack([MockGlitchling("a"), MockGlitchling("b")], seed=7).glitchlings
    base("hello")  # Advance RNG state to detect resets.

    original_seed = base.seed
    original_states = [glitchling.rng.getstate() for glitchling in base.apply_order]

    Attack(base, seed=override_seed)

    assert base.seed == original_seed
    assert [glitchling.rng.getstate() for glitchling in base.apply_order] == original_states


def test_attack_accepts_string_specifications():
    """Attack can be initialized with string glitchling specs."""
    # Single string spec
    attack = Attack("typogre")
    assert len(attack.glitchlings._clones_by_index) == 1
    assert attack.glitchlings._clones_by_index[0].name.lower() == "typogre"

    # String spec with parameters
    attack_with_params = Attack("Typogre(rate=0.05)")
    assert len(attack_with_params.glitchlings._clones_by_index) == 1

    # List of string specs
    attack_list = Attack(["typogre", "mim1c"])
    assert len(attack_list.glitchlings._clones_by_index) == 2


def test_attack_accepts_mixed_specs_and_instances():
    """Attack can mix string specs with Glitchling instances."""
    mock = MockGlitchling()  # Uses default name "mock"
    attack = Attack([mock, "typogre"])

    names = [g.name.lower() for g in attack.glitchlings._clones_by_index]
    assert "mock" in names
    assert "typogre" in names

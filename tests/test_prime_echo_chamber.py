import pytest

datasets = pytest.importorskip("datasets")
Dataset = datasets.Dataset

# The Prime DLC depends on the optional ``verifiers`` package. Skip these
# tests entirely when it isn't installed (e.g. in wheel builds that don't
# request the ``prime`` extra).
pytest.importorskip("verifiers")

from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling
from glitchlings.dlc import prime


def append_marker(text: str) -> str:
    """Tag the provided text with a deterministic marker."""

    return f"{text}<<<"


def test_conversational_prompts_remain_structured() -> None:
    dataset = Dataset.from_dict(
        {
            "prompt": [
                [
                    {"role": "system", "content": "Restore the text."},
                    {"role": "user", "content": "coRRuPt3d"},
                ]
            ]
        }
    )

    glitchling = Glitchling("marker", append_marker, AttackWave.SENTENCE)
    gaggle = Gaggle([glitchling], seed=99)

    corrupted_rows = list(gaggle.corrupt_dataset(dataset, ["prompt"]))

    assert len(corrupted_rows) == 1
    prompt = corrupted_rows[0]["prompt"]

    assert isinstance(prompt, list)
    assert prompt[0] == {"role": "system", "content": "Restore the text."}
    assert prompt[1]["role"] == "user"
    assert prompt[1]["content"] == "coRRuPt3d<<<"


def test_prime_resolve_columns_requires_string_candidates():
    dataset = Dataset.from_dict({"scores": [[1, 2], [3, 4]], "ids": [1, 2]})

    with pytest.raises(ValueError, match=r"Unable to determine which dataset columns to corrupt\."):
        prime._resolve_columns(dataset, None)


class _FakeEnvironment:
    def __init__(self, dataset):
        self.dataset = dataset


class _RecordingGaggle:
    def __init__(self):
        self.columns_seen: list[list[str]] = []

    def corrupt_dataset(self, dataset, columns):
        self.columns_seen.append(list(columns))
        return dataset


def test_load_environment_respects_explicit_columns(monkeypatch):
    dataset = Dataset.from_dict({"prompt": ["alpha"], "extra": ["beta"]})
    stub = _RecordingGaggle()

    monkeypatch.setattr(prime, "_resolve_environment", lambda _env: _FakeEnvironment(dataset))
    monkeypatch.setattr(prime, "summon", lambda specs, seed: stub)

    env = prime.load_environment("ignored", glitchlings=[prime.Typogre()], seed=7, columns=["extra"])

    assert env.dataset is dataset
    assert stub.columns_seen == [["extra"]]


def test_tutorial_level_applies_tuned_glitchlings(monkeypatch):
    baseline = "alpha beta gamma delta"

    def _fake_environment(_):
        return _FakeEnvironment(Dataset.from_dict({"prompt": [baseline]}))

    monkeypatch.setattr(prime, "_resolve_environment", _fake_environment)

    env = prime.tutorial_level("ignored", seed=123, difficulty=prime.Difficulty.Easy)
    mutated_prompt = list(env.dataset)[0]["prompt"]
    assert mutated_prompt != baseline

    env_again = prime.tutorial_level("ignored", seed=123, difficulty=prime.Difficulty.Easy)
    mutated_again = list(env_again.dataset)[0]["prompt"]
    assert mutated_again != baseline
    assert mutated_prompt == mutated_again




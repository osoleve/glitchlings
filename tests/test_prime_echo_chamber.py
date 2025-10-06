from __future__ import annotations

import importlib
import sys
import types

import pytest


class _VerifierEnvironment:
    def __init__(self, dataset=None):
        self.dataset = dataset


def _load_environment(_: str) -> _VerifierEnvironment:
    return _VerifierEnvironment()


verifiers_stub = types.ModuleType("verifiers")
verifiers_stub.Environment = _VerifierEnvironment
verifiers_stub.load_environment = _load_environment
sys.modules.setdefault("verifiers", verifiers_stub)

import glitchlings.zoo.core as zoo_core
import glitchlings.zoo.jargoyle as jargoyle
from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling
from glitchlings.dlc import prime


def _no_op_ensure_wordnet() -> None:
    jargoyle._wordnet_ready = True


jargoyle.ensure_wordnet = _no_op_ensure_wordnet
jargoyle._ensure_wordnet = _no_op_ensure_wordnet
# conftest = importlib.import_module("conftest")
# conftest.ensure_wordnet = _no_op_ensure_wordnet


@pytest.fixture(autouse=True)
def patch_ensure_wordnet(monkeypatch):
    import conftest
    monkeypatch.setattr(conftest, "ensure_wordnet", _no_op_ensure_wordnet)
class FakeDataset:
    def __init__(self, rows: list[dict[str, object]], column_names: list[str] | None = None):
        self._rows = [dict(row) for row in rows]
        if column_names is None:
            if rows:
                column_names = list(rows[0].keys())
            else:
                column_names = []
        self.column_names = list(column_names)

    @classmethod
    def from_dict(cls, columns: dict[str, list[object]]) -> "FakeDataset":
        keys = list(columns.keys())
        length = len(next(iter(columns.values()), []))
        rows = [
            {key: columns[key][index] for key in keys}
            for index in range(length)
        ]
        return cls(rows, keys)

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index: int) -> dict[str, object]:
        return dict(self._rows[index])

    def __iter__(self):
        for row in self._rows:
            yield dict(row)

    def with_transform(self, function):
        transformed = [function(dict(row)) for row in self._rows]
        return FakeDataset(transformed, self.column_names)


Dataset = FakeDataset


@pytest.fixture(autouse=True)
def _install_fake_datasets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(zoo_core, "_DatasetsDataset", FakeDataset, raising=False)
    monkeypatch.setattr(zoo_core, "_datasets_error", None, raising=False)


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


def test_extract_completion_text_handles_strings_and_structures() -> None:
    assert prime._extract_completion_text("plain text") == "plain text"

    message = [{"role": "assistant", "content": "structured"}]
    assert prime._extract_completion_text(message) == "structured"

    assert prime._extract_completion_text({"foo": 1}) == "{'foo': 1}"


def test_similarity_scores_expected_fraction_for_single_edit() -> None:
    completion = "hello"
    answer = "hella"
    expected_distance = 1
    expected_score = 1 - (expected_distance / max(len(completion), len(answer), 1))

    score = prime.symmetric_damerau_levenshtein_similarity(None, completion, answer)

    assert score == pytest.approx(expected_score)


def test_similarity_handles_identical_and_extreme_inputs() -> None:
    assert prime.symmetric_damerau_levenshtein_similarity(None, "same", "same") == 1.0

    shorter = prime.symmetric_damerau_levenshtein_similarity(None, "a", "a" * 10)
    longer = prime.symmetric_damerau_levenshtein_similarity(None, "a" * 10, "a")
    assert 0.0 <= shorter <= 1.0
    assert 0.0 <= longer <= 1.0

    empty_answer = prime.symmetric_damerau_levenshtein_similarity(None, "abc", "")
    both_empty = prime.symmetric_damerau_levenshtein_similarity(None, "", "")
    assert empty_answer == 0.0
    assert both_empty == 1.0




from __future__ import annotations

import importlib
import sys
import types

import pytest

pytest.importorskip("jellyfish")


class _Rubric:
    def __init__(self, funcs, weights):
        self.funcs = list(funcs)
        self.weights = list(weights)


class _SingleTurnEnv:
    def __init__(self, dataset=None, rubric=None):
        self.dataset = dataset
        self.rubric = rubric

class _VerifierEnvironment:
    def __init__(self, dataset=None):
        self.dataset = dataset


def _load_environment(_: str) -> _VerifierEnvironment:
    return _VerifierEnvironment()


verifiers_stub = types.ModuleType("verifiers")
verifiers_stub.Environment = _VerifierEnvironment
verifiers_stub.Rubric = _Rubric
verifiers_stub.SingleTurnEnv = _SingleTurnEnv
verifiers_stub.load_environment = _load_environment
sys.modules["verifiers"] = verifiers_stub

zoo_core = importlib.import_module("glitchlings.zoo.core")
prime = importlib.import_module("glitchlings.dlc.prime")
glitchlings_compat = importlib.import_module("glitchlings.compat")

AttackWave = zoo_core.AttackWave
Gaggle = zoo_core.Gaggle
Glitchling = zoo_core.Glitchling




class FakeDataset:
    def __init__(
        self,
        rows: list[dict[str, object]],
        column_names: list[str] | None = None,
        *,
        streaming: bool = False,
    ) -> None:
        self._rows = [dict(row) for row in rows]
        if column_names is None:
            if rows:
                column_names = list(rows[0].keys())
            else:
                column_names = []
        self.column_names = list(column_names)
        self._streaming = streaming

    @classmethod
    def from_dict(
        cls, columns: dict[str, list[object]], *, streaming: bool = False
    ) -> "FakeDataset":
        keys = list(columns.keys())
        lengths = [len(col) for col in columns.values()]
        if lengths and any(length != lengths[0] for length in lengths):
            raise ValueError(
                "All columns must have the same length, but got lengths: "
                f"{dict(zip(keys, lengths))}"
            )
        length = lengths[0] if lengths else 0
        rows = [
            {key: columns[key][index] for key in keys}
            for index in range(length)
        ]
        return cls(rows, keys, streaming=streaming)

    def __len__(self) -> int:
        if self._streaming:
            raise TypeError("Streaming dataset does not define __len__.")
        return len(self._rows)

    def __getitem__(self, index: int) -> dict[str, object]:
        return dict(self._rows[index])

    def __iter__(self):
        for row in self._rows:
            yield dict(row)

    def filter(self, function, load_from_cache_file: bool = True):
        filtered = [row for row in self._rows if function(dict(row))]
        return FakeDataset(filtered, self.column_names, streaming=self._streaming)

    def map(
        self,
        function,
        remove_columns=None,
        load_from_cache_file: bool = True,
    ):
        mapped_rows = []
        for row in self._rows:
            result = function(dict(row))
            if remove_columns:
                for column in remove_columns:
                    result.pop(column, None)
            mapped_rows.append(result)
        if mapped_rows:
            column_names = list(mapped_rows[0].keys())
        else:
            column_names = []
        return FakeDataset(mapped_rows, column_names, streaming=self._streaming)

    def take(self, n: int):
        return FakeDataset(self._rows[:n], self.column_names, streaming=self._streaming)

    def with_transform(self, function):
        transformed = [function(dict(row)) for row in self._rows]
        return FakeDataset(transformed, self.column_names, streaming=self._streaming)


Dataset = FakeDataset


@pytest.fixture(autouse=True)
def _install_fake_datasets(monkeypatch: pytest.MonkeyPatch) -> None:
    datasets_stub = types.ModuleType("datasets")
    datasets_stub.Dataset = FakeDataset
    datasets_stub.DatasetDict = dict

    def _unimplemented_load(*args, **kwargs):
        raise RuntimeError("load_dataset stub not configured for this test.")

    datasets_stub.load_dataset = _unimplemented_load
    monkeypatch.setitem(sys.modules, "datasets", datasets_stub)
    glitchlings_compat.reset_optional_dependencies()
    glitchlings_compat.datasets.get()
    monkeypatch.setattr(zoo_core, "_DatasetsDataset", FakeDataset, raising=False)


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


def test_resolve_environment_rejects_invalid_type():
    with pytest.raises(TypeError, match="Invalid environment type"):
        prime._resolve_environment(object())



def test_prime_resolve_columns_handles_streaming_dataset():
    row = {"context": "alpha", "score": 1, "response": "beta"}

    class StreamingDataset:
        def __init__(self):
            self.column_names = ["context", "score", "response"]

        def __len__(self):
            raise TypeError("Streaming dataset does not define __len__.")

        def __getitem__(self, index):
            raise TypeError("Streaming dataset does not support indexing.")

        def take(self, n):
            return [row][:n]

        def __iter__(self):
            return iter([row])

    inferred = prime._resolve_columns(StreamingDataset(), None)

    assert inferred == ["context", "response"]

def test_load_environment_respects_explicit_columns(monkeypatch):
    dataset = Dataset.from_dict({"prompt": ["alpha"], "extra": ["beta"]})
    stub = _RecordingGaggle()

    monkeypatch.setattr(
        prime, "_resolve_environment", lambda _env: _FakeEnvironment(dataset)
    )
    monkeypatch.setattr(prime, "coerce_gaggle", lambda specs, seed: stub)

    env = prime.load_environment(
        "ignored", glitchlings=[prime.Typogre()], seed=7, columns=["extra"]
    )

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


def test_echo_chamber_uses_custom_reward(monkeypatch: pytest.MonkeyPatch) -> None:
    base_dataset = Dataset.from_dict({"text": ["alpha"]})

    def _fake_load_dataset(*args, **kwargs):
        return base_dataset

    datasets_stub = types.ModuleType("datasets")
    datasets_stub.Dataset = Dataset
    datasets_stub.DatasetDict = dict
    datasets_stub.load_dataset = _fake_load_dataset
    monkeypatch.setitem(sys.modules, "datasets", datasets_stub)
    glitchlings_compat.reset_optional_dependencies()
    glitchlings_compat.datasets.get()

    recorder = _RecordingGaggle()
    monkeypatch.setattr(prime, "_as_gaggle", lambda glitchlings, seed: recorder)

    def custom_reward(*_args, **_kwargs) -> float:
        return 0.0

    env = prime.echo_chamber(
        dataset_id="stub/dataset",
        column="text",
        glitchlings=["Typogre"],
        reward_function=custom_reward,
    )

    assert env.rubric.funcs == [custom_reward]
    assert recorder.columns_seen == [["prompt"]]


def test_echo_chamber_passes_split_to_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    base_dataset = Dataset.from_dict({"text": ["alpha"]})
    captured: dict[str, object] = {}

    def _fake_load_dataset(dataset_id, *, split=None, **kwargs):
        captured["split"] = split
        return base_dataset

    datasets_stub = types.ModuleType("datasets")
    datasets_stub.Dataset = Dataset
    datasets_stub.DatasetDict = dict
    datasets_stub.load_dataset = _fake_load_dataset
    monkeypatch.setitem(sys.modules, "datasets", datasets_stub)
    glitchlings_compat.reset_optional_dependencies()
    glitchlings_compat.datasets.get()

    monkeypatch.setattr(prime, "_as_gaggle", lambda glitchlings, seed: _RecordingGaggle())

    prime.echo_chamber(
        dataset_id="stub/dataset",
        column="text",
        glitchlings=["Typogre"],
        split="train",
    )

    assert captured["split"] == "train"


def test_echo_chamber_requires_non_empty_column(monkeypatch: pytest.MonkeyPatch) -> None:
    empty_dataset = Dataset.from_dict({"text": [None, None]})

    def _fake_load_dataset(*args, **kwargs):
        return empty_dataset

    datasets_stub = types.ModuleType("datasets")
    datasets_stub.Dataset = Dataset
    datasets_stub.DatasetDict = dict
    datasets_stub.load_dataset = _fake_load_dataset
    monkeypatch.setitem(sys.modules, "datasets", datasets_stub)
    glitchlings_compat.reset_optional_dependencies()
    glitchlings_compat.datasets.get()

    monkeypatch.setattr(prime, "_as_gaggle", lambda *args, **kwargs: _RecordingGaggle())

    with pytest.raises(ValueError, match="did not yield any textual entries"):
        prime.echo_chamber(
            dataset_id="stub/dataset",
            column="text",
            glitchlings=["Typogre"],
        )
def test_echo_chamber_streams_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    base_dataset = Dataset.from_dict({
        "text": ["alpha", None, "beta"],
        "other": [1, 2, 3],
    }, streaming=True)

    def _fake_load_dataset(*args, **kwargs):
        return base_dataset

    datasets_stub = types.ModuleType("datasets")
    datasets_stub.Dataset = Dataset
    datasets_stub.DatasetDict = dict
    datasets_stub.load_dataset = _fake_load_dataset
    monkeypatch.setitem(sys.modules, "datasets", datasets_stub)
    glitchlings_compat.reset_optional_dependencies()
    glitchlings_compat.datasets.get()

    class _RecordingGaggle:
        def __init__(self):
            self.records: list[tuple[Dataset, list[str]]] = []

        def corrupt_dataset(self, dataset, columns):
            self.records.append((dataset, list(columns)))
            return dataset

    recorder = _RecordingGaggle()
    monkeypatch.setattr(prime, "_as_gaggle", lambda glitchlings, seed: recorder)

    env = prime.echo_chamber(
        dataset_id="stub/the-dataset",
        column="text",
        glitchlings=["Typogre"],
        instructions="Restore the text.",
    )

    assert sum(1 for _ in base_dataset) == 3
    assert recorder.records
    dataset, columns = recorder.records[0]
    assert dataset is not base_dataset
    assert columns == ["prompt"]

    assert env.dataset is dataset
    rows = list(dataset)
    assert len(rows) == 2
    assert rows[0]["answer"] == "alpha"
    assert rows[0]["prompt"][0]["content"] == "Restore the text."
    assert rows[0]["prompt"][1]["content"] == "Corrupted text:\nalpha"






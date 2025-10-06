"""Regression tests covering dataset corruption with optional dependencies."""

from __future__ import annotations

import builtins
import importlib
import random
import sys
from typing import Any

import pytest


def _materialize(dataset: "Dataset") -> list[dict[str, Any]]:
    """Eagerly load a dataset to regular dictionaries for comparison."""

    return [
        {column: row[column] for column in dataset.column_names}
        for row in dataset
    ]


def test_corrupt_dataset_is_deterministic_across_columns() -> None:
    """Ensure ``Glitchling.corrupt_dataset`` produces stable results."""

    pytest.importorskip("datasets")
    from datasets import Dataset

    from glitchlings.zoo.core import AttackWave, Glitchling

    def append_rng_token(text: str, *, rng: random.Random) -> str:
        return f"{text}:{rng.randint(0, 999)}"

    dataset = Dataset.from_dict(
        {
            "text": ["alpha", "bravo", "charlie"],
            "untouched": ["keep", "these", "same"],
        }
    )
    glitchling = Glitchling(
        "rngster", append_rng_token, AttackWave.SENTENCE, seed=2024
    )

    original_rows = _materialize(dataset)

    glitchling.reset_rng(seed=1337)
    corrupted_first = glitchling.corrupt_dataset(dataset, columns=["text"])
    first_rows = _materialize(corrupted_first)

    glitchling.reset_rng(seed=1337)
    corrupted_second = glitchling.corrupt_dataset(dataset, columns=["text"])
    second_rows = _materialize(corrupted_second)

    assert corrupted_first.column_names == dataset.column_names
    assert corrupted_second.column_names == dataset.column_names
    assert first_rows == second_rows
    assert [row["untouched"] for row in first_rows] == [
        row["untouched"] for row in original_rows
    ]


def test_corrupt_dataset_requires_optional_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ``Glitchling.corrupt_dataset`` surfaces a clear error."""

    monkeypatch.delitem(sys.modules, "datasets", raising=False)

    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):  # type: ignore[override]
        if name == "datasets":
            raise ModuleNotFoundError("datasets is not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    for module_name in [
        module
        for module in sys.modules
        if module == "glitchlings" or module.startswith("glitchlings.")
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    glitchlings = importlib.import_module("glitchlings")
    assert glitchlings is not None

    from glitchlings.zoo.core import AttackWave, Glitchling

    noop = Glitchling("noop", lambda text, **_: text, AttackWave.CHARACTER)

    with pytest.raises(ModuleNotFoundError, match="datasets is not installed"):
        noop.corrupt_dataset(dataset=object(), columns=["text"])


def test_corrupt_dataset_glitches_list_columns_individually():
    pytest.importorskip("datasets")
    from datasets import Dataset

    from glitchlings.zoo.core import AttackWave, Glitchling

    def tag_entry(text: str, *, rng: random.Random) -> str:
        return f"{text}:{rng.randint(0, 99)}"

    dataset = Dataset.from_dict(
        {
            "utterances": [["alpha", "bravo"], ["charlie", "delta"]],
            "notes": ["keep", "steady"],
        }
    )
    glitchling = Glitchling("tagger", tag_entry, AttackWave.SENTENCE, seed=314)

    glitchling.reset_rng(seed=21)
    corrupted = glitchling.corrupt_dataset(dataset, columns=["utterances"])

    rows = _materialize(corrupted)
    glitchling.reset_rng(seed=21)
    repeat_rows = _materialize(glitchling.corrupt_dataset(dataset, columns=["utterances"]))

    assert rows == repeat_rows
    originals = dataset["utterances"]
    original_notes = dataset["notes"]
    for row, original, note in zip(rows, originals, original_notes):
        mutated = row["utterances"]
        assert isinstance(mutated, str)
        for item in original:
            assert item in mutated
        assert ":" in mutated
        assert row["notes"] == note


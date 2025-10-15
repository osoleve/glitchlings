from __future__ import annotations

from collections.abc import Iterable
from random import Random
from typing import Any

import pytest

from glitchlings.dlc import pytorch_lightning as pl_dlc
from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling

pl = pytest.importorskip("pytorch_lightning")


def append_rng_token(text: str, *, rng: Random) -> str:
    """Append a deterministic RNG token to the supplied text."""

    return f"{text}-{rng.randint(0, 999)}"


class _ListDataLoader:
    """Minimal dataloader implementation backed by an in-memory list."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self._data = data

    def __iter__(self) -> Iterable[dict[str, Any]]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


class _SimpleDataModule(pl.LightningDataModule):
    """LightningDataModule emitting deterministic dictionary batches."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        super().__init__()
        self.rows = rows
        self.flag = "base"

    def train_dataloader(self) -> _ListDataLoader:
        return _ListDataLoader(self.rows)

    def val_dataloader(self) -> _ListDataLoader:
        return _ListDataLoader(self.rows)

    def test_dataloader(self) -> _ListDataLoader:
        return _ListDataLoader(self.rows)

    def predict_dataloader(self) -> _ListDataLoader:
        return _ListDataLoader(self.rows)


@pytest.fixture(autouse=True)
def ensure_glitch_installed() -> Iterable[None]:
    pl_dlc.install()
    yield


def test_install_is_idempotent() -> None:
    pl_dlc.install()
    assert hasattr(pl.LightningDataModule, "glitch")


def test_glitch_wraps_batches_and_preserves_original_data() -> None:
    rows = [
        {"text": "alpha", "notes": "one", "label": 0},
        {"text": "beta", "notes": "two", "label": 1},
    ]
    datamodule = _SimpleDataModule([row.copy() for row in rows])

    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=1337)
    gaggle = Gaggle([glitchling], seed=99)

    glitched = datamodule.glitch(gaggle, column="text", seed=99)

    assert isinstance(glitched, pl.LightningDataModule)
    assert glitched.flag == "base"

    train_batches = list(glitched.train_dataloader())
    comparison_gaggle = Gaggle([glitchling.clone()], seed=99)
    expected = []
    for row in rows:
        mutated = dict(row)
        mutated["text"] = comparison_gaggle.corrupt(row["text"])
        expected.append(mutated)

    assert train_batches == expected

    original_batches = list(datamodule.train_dataloader())
    assert original_batches == rows


def test_glitch_accepts_multiple_columns() -> None:
    rows = [
        {"text": "alpha", "notes": "one", "label": 0},
        {"text": "beta", "notes": "two", "label": 1},
    ]
    datamodule = _SimpleDataModule([row.copy() for row in rows])
    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=7)

    glitched = datamodule.glitch([glitchling], column=("text", "notes"), seed=11)

    batches = list(glitched.val_dataloader())
    comparison_gaggle = Gaggle([glitchling.clone()], seed=11)
    expected = []
    for row in rows:
        mutated = dict(row)
        mutated["text"] = comparison_gaggle.corrupt(row["text"])
        mutated["notes"] = comparison_gaggle.corrupt(row["notes"])
        expected.append(mutated)

    assert batches == expected


def test_glitch_proxies_attribute_assignment() -> None:
    datamodule = _SimpleDataModule([
        {"text": "alpha", "notes": "one", "label": 0},
    ])

    glitched = datamodule.glitch("typogre", column="text")
    glitched.flag = "updated"

    assert datamodule.flag == "updated"


def test_missing_column_raises_error() -> None:
    datamodule = _SimpleDataModule([
        {"text": "alpha", "label": 0},
    ])
    glitched = datamodule.glitch("typogre", column="notes")

    loader = glitched.test_dataloader()
    with pytest.raises(ValueError, match="Columns not found"):
        list(loader)

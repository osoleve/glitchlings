from __future__ import annotations

import importlib
import sys
import types
from random import Random

import pytest

from glitchlings.zoo import Gaggle, Glitchling
from glitchlings.zoo.core import AttackWave


def append_rng_token(text: str, *, rng: Random) -> str:
    """Append a deterministic RNG token to the supplied text."""
    return f"{text}-{rng.randint(0, 999)}"


@pytest.fixture()
def pytorch_dlc() -> types.ModuleType:
    """Reload the PyTorch DLC module against the stub."""
    sys.modules.pop("glitchlings.dlc.pytorch", None)
    module = importlib.import_module("glitchlings.dlc.pytorch")
    module.install()
    return module


def test_install_is_idempotent(pytorch_dlc: types.ModuleType) -> None:
    loader_cls = pytorch_dlc.DataLoader
    assert loader_cls is not None
    initial_method = getattr(loader_cls, "glitch", None)

    pytorch_dlc.install()
    assert getattr(loader_cls, "glitch") is initial_method


def test_glitch_corrupts_named_columns(pytorch_dlc: types.ModuleType) -> None:
    loader_cls = pytorch_dlc.DataLoader
    assert loader_cls is not None

    dataset = [{"text": ["alpha", "beta"], "label": [0, 1]}]
    loader = loader_cls(dataset)

    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=404)
    glitched_loader = loader.glitch(glitchling, columns="text", seed=21)

    batches = list(glitched_loader)
    assert len(batches) == 1
    batch = batches[0]
    assert batch["label"] == [0, 1]
    assert batch["text"][0].startswith("alpha-")
    assert dataset[0]["text"][0] == "alpha"

    rerun = list(glitched_loader)
    assert rerun == batches


def test_glitch_infers_textual_columns(pytorch_dlc: types.ModuleType) -> None:
    loader_cls = pytorch_dlc.DataLoader
    assert loader_cls is not None

    dataset = [{"text": "alpha", "label": 1}]
    loader = loader_cls(dataset)

    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=123)
    glitched_loader = loader.glitch([glitchling], seed=99)

    batches = list(glitched_loader)
    assert batches[0]["label"] == 1
    assert batches[0]["text"].startswith("alpha-")
    assert list(glitched_loader) == batches


def test_glitch_accepts_sequence_indices(pytorch_dlc: types.ModuleType) -> None:
    loader_cls = pytorch_dlc.DataLoader
    assert loader_cls is not None

    dataset = [("alpha", 1), ("beta", 0)]
    loader = loader_cls(dataset)

    gaggle = Gaggle(
        [Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=77)],
        seed=11,
    )
    glitched_loader = loader.glitch(gaggle, columns=(0,))

    batches = list(glitched_loader)
    assert batches[0][0].startswith("alpha-")
    assert batches[0][1] == 1


def test_glitch_rejects_empty_column_sequence(pytorch_dlc: types.ModuleType) -> None:
    loader_cls = pytorch_dlc.DataLoader
    assert loader_cls is not None

    dataset = [{"text": "alpha"}]
    loader = loader_cls(dataset)

    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=55)

    with pytest.raises(ValueError, match="At least one column"):
        loader.glitch(glitchling, columns=())

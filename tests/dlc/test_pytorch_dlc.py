from __future__ import annotations

import importlib
import sys
import types
from random import Random

import pytest

from glitchlings.compat import reset_optional_dependencies
from glitchlings.dlc.pytorch import GlitchedDataLoader
from glitchlings.zoo import Gaggle, Glitchling
from glitchlings.zoo.core import AttackWave


def append_rng_token(text: str, *, rng: Random) -> str:
    """Append a deterministic RNG token to the supplied text."""
    return f"{text}-{rng.randint(0, 999)}"


@pytest.fixture(autouse=True)
def _use_torch_stub(torch_stub):
    """Automatically use the torch_stub fixture for all tests in this file."""
    pass


def test_glitched_dataloader_wrapper_corrupts_named_columns(
    torch_stub: type[Any],
) -> None:
    """Test the new GlitchedDataLoader wrapper API."""
    dataset = [{"text": ["alpha", "beta"], "label": [0, 1]}]
    loader = torch_stub(dataset)

    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=404)
    glitched_loader = GlitchedDataLoader(loader, glitchling, columns="text", seed=21)

    batches = list(glitched_loader)
    assert len(batches) == 1
    batch = batches[0]
    assert batch["label"] == [0, 1]
    assert batch["text"][0].startswith("alpha-")
    assert dataset[0]["text"][0] == "alpha"

    rerun = list(glitched_loader)
    assert rerun == batches


def test_glitched_dataloader_wrapper_infers_textual_columns(
    torch_stub: type[Any],
) -> None:
    """Test GlitchedDataLoader with auto-inferred columns."""
    dataset = [{"text": "alpha", "label": 1}]
    loader = torch_stub(dataset)

    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=123)
    glitched_loader = GlitchedDataLoader(loader, [glitchling], seed=99)

    batches = list(glitched_loader)
    assert batches[0]["label"] == 1
    assert batches[0]["text"].startswith("alpha-")
    assert list(glitched_loader) == batches


def test_glitched_dataloader_wrapper_accepts_sequence_indices(
    torch_stub: type[Any],
) -> None:
    """Test GlitchedDataLoader with sequence indices."""
    dataset = [("alpha", 1), ("beta", 0)]
    loader = torch_stub(dataset)

    gaggle = Gaggle(
        [Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=77)],
        seed=11,
    )
    glitched_loader = GlitchedDataLoader(loader, gaggle, columns=(0,))

    batches = list(glitched_loader)
    assert batches[0][0].startswith("alpha-")
    assert batches[0][1] == 1


def test_glitched_dataloader_wrapper_rejects_empty_column_sequence(
    torch_stub: type[Any],
) -> None:
    """Test GlitchedDataLoader rejects empty column sequence."""
    dataset = [{"text": "alpha"}]
    loader = torch_stub(dataset)

    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=55)

    with pytest.raises(ValueError, match="At least one column"):
        GlitchedDataLoader(loader, glitchling, columns=())

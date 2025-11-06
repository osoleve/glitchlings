from __future__ import annotations

from functools import partial
from typing import cast

import pytest

from glitchlings import jargoyle, mim1c, redactyl, rushmore, scannequin, typogre, zeedub
from glitchlings.zoo.core import AttackWave, Glitchling
from glitchlings.zoo.pedant import Pedant
from glitchlings.zoo.pedant.stones import PedantStone


def _twice(fn, text: str, seed: int = 42) -> tuple[str, str]:
    fn.reset_rng(seed)
    out1 = cast(str, fn(text))
    fn.reset_rng(seed)
    out2 = cast(str, fn(text))
    return out1, out2


@pytest.mark.parametrize(
    ("glitchling", "params"),
    [
        pytest.param(typogre, {"seed": 42, "rate": 0.03}, id="typogre"),
        pytest.param(
            mim1c,
            {"seed": 42, "rate": 0.03, "classes": ["LATIN", "GREEK", "CYRILLIC"]},
            id="mim1c",
        ),
        pytest.param(jargoyle, {"seed": 42, "rate": 0.05}, id="jargoyle"),
        pytest.param(rushmore, {"seed": 42, "rate": 0.01}, id="rushmore"),
        pytest.param(redactyl, {"seed": 42, "rate": 0.05}, id="redactyl"),
        pytest.param(scannequin, {"seed": 42, "rate": 0.03}, id="scannequin"),
        pytest.param(zeedub, {"seed": 42, "rate": 0.03}, id="zeedub"),
    ],
)
def test_glitchling_is_deterministic(glitchling, params, sample_text):
    """Test that each glitchling produces deterministic output with the same seed."""
    for param, value in params.items():
        glitchling.set_param(param, value)
    
    a, b = _twice(glitchling, sample_text, seed=params["seed"])
    assert a == b


def test_apostrofae_determinism(sample_text):
    """Test Pedant (Apostrofae) determinism separately due to special construction."""
    curlite = Pedant(stone=PedantStone.CURLITE)
    curlite.set_param("seed", 42)
    a, b = _twice(curlite, sample_text)
    assert a == b


def _partial_helper(text: str, *, rng) -> str:
    # The helper intentionally relies on the injected RNG to ensure it is provided.
    rng.random()
    return text


def test_partial_corruption_receives_rng(sample_text):
    """Ensure RNG injection works for callables lacking a ``__code__`` attribute."""
    corruption = partial(_partial_helper)
    glitchling = Glitchling("partial", corruption, AttackWave.WORD)

    result = glitchling(sample_text)
    assert result == sample_text

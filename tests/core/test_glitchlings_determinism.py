"""Determinism tests for all glitchlings.

This module tests that each glitchling produces deterministic output
when given the same seed, which is critical for reproducibility.
"""

from __future__ import annotations

from functools import partial

import pytest

from glitchlings import (
    ekkokin,
    hokey,
    jargoyle,
    mim1c,
    redactyl,
    rushmore,
    scannequin,
    typogre,
    zeedub,
)
from glitchlings.zoo.core import AttackWave, Glitchling
from glitchlings.zoo.pedant import Pedant
from glitchlings.zoo.pedant.stones import PedantStone
from tests.helpers.assertions import assert_deterministic


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
        pytest.param(hokey, {"seed": 42, "rate": 0.6}, id="hokey"),
        pytest.param(ekkokin, {"seed": 42, "rate": 0.05}, id="ekkokin"),
    ],
)
def test_glitchling_is_deterministic(glitchling, params, sample_text):
    """Test that each glitchling produces deterministic output with the same seed."""
    # Clone to avoid modifying the module-level instance
    glitch = glitchling.clone()

    # Apply all parameters
    for param, value in params.items():
        glitch.set_param(param, value)

    # Use the shared assertion helper
    seed = params["seed"]
    assert_deterministic(glitch, sample_text, seed)


def test_apostrofae_determinism(sample_text):
    """Test Pedant (Apostrofae) determinism separately due to special construction."""
    curlite = Pedant(stone=PedantStone.CURLITE)
    curlite.set_param("seed", 42)
    assert_deterministic(curlite, sample_text, seed=42)


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

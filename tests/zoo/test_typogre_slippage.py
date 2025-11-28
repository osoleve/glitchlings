"""Tests for Typogre modifier slippage behaviour."""

import random

from glitchlings.internal.rust_ffi import fatfinger_rust, resolve_seed
from glitchlings.util import KEYNEIGHBORS
from glitchlings.zoo.typogre import Typogre


def test_shift_slip_creates_burst_not_scatter() -> None:
    """High slip rate should produce a short shifted burst, not alternating caps."""

    typogre = Typogre(
        rate=0.0,
        keyboard="QWERTY",
        shift_slip_rate=1.0,
        seed=151,
    )

    assert typogre.corrupt("hello") == "HEllo"


def test_shift_slip_zero_matches_fatfinger() -> None:
    """Existing fatfinger behaviour remains unchanged when slippage is disabled."""

    text = "guardian of the vault"
    rate = 0.35
    seed = 7
    layout = getattr(KEYNEIGHBORS, "QWERTY")

    derived_seed = resolve_seed(None, random.Random(seed))
    expected = fatfinger_rust(text, rate, layout, derived_seed)

    typogre = Typogre(
        rate=rate,
        keyboard="QWERTY",
        shift_slip_rate=0.0,
        seed=seed,
    )

    assert typogre.corrupt(text) == expected

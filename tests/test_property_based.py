"""Property-based tests covering core orchestration primitives."""

from __future__ import annotations

import math
import string

import importlib

import pytest

pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, assume, given, settings, strategies as st

from glitchlings.zoo.core import AttackOrder, AttackWave, Gaggle, Glitchling

rushmore_module = importlib.import_module("glitchlings.zoo.rushmore")
typogre_module = importlib.import_module("glitchlings.zoo.typogre")


def _build_corruption(name: str, amplitude: int):
    """Create a deterministic corruption function driven by the provided RNG.

    The function appends a marker tied to the glitchling name along with a
    pseudo-random suffix that depends on the glitchling's RNG. This allows the
    tests to assert that derived seeds and ordering are both respected.
    """

    choices = (name + "xyz").replace("|", "_")

    def _corrupt(text: str, *, rng) -> str:
        if amplitude == 0:
            return f"{text}|{name}"
        suffix = "".join(rng.choice(choices) for _ in range(amplitude))
        return f"{text}|{name}:{suffix}"

    return _corrupt


@st.composite
def glitchling_specs(draw):
    name = draw(
        st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=8)
    )
    wave = draw(st.sampled_from(list(AttackWave)))
    order = draw(st.sampled_from(list(AttackOrder)))
    amplitude = draw(st.integers(min_value=0, max_value=4))
    return {"name": name, "wave": wave, "order": order, "amplitude": amplitude}


word_sequences = st.lists(
    st.text(alphabet=string.ascii_letters, min_size=1, max_size=12),
    min_size=2,
    max_size=12,
).map(lambda parts: " ".join(parts))


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    master_seed=st.integers(min_value=-(2**63), max_value=2**63 - 1),
    specs=st.lists(glitchling_specs(), min_size=1, max_size=5, unique_by=lambda s: s["name"]),
)
def test_gaggle_ordering_and_determinism(master_seed, specs):
    """Gaggles should honour ordering guarantees and deterministic RNG use."""

    glitchlings = [
        Glitchling(
            name=spec["name"],
            corruption_function=_build_corruption(spec["name"], spec["amplitude"]),
            scope=spec["wave"],
            order=spec["order"],
        )
        for spec in specs
    ]

    gaggle = Gaggle(glitchlings, seed=master_seed)

    expected = [
        spec["name"]
        for spec in sorted(
            specs,
            key=lambda spec: (spec["wave"], spec["order"], spec["name"]),
        )
    ]
    actual = [g.name for g in gaggle.apply_order]
    assert actual == expected

    text = "payload"
    first_run = gaggle(text)
    second_run = Gaggle(glitchlings, seed=master_seed)(text)
    assert first_run == second_run


@given(
    left=st.tuples(
        st.integers(min_value=-(2**63), max_value=2**63 - 1),
        st.text(alphabet=string.ascii_letters + string.digits, min_size=0, max_size=12),
        st.integers(min_value=0, max_value=1024),
    ),
    right=st.tuples(
        st.integers(min_value=-(2**63), max_value=2**63 - 1),
        st.text(alphabet=string.ascii_letters + string.digits, min_size=0, max_size=12),
        st.integers(min_value=0, max_value=1024),
    ),
)
def test_derived_seeds_change_with_inputs(left, right):
    """Changing any component of the derivation tuple should alter the seed."""

    assume(left != right)
    assert Gaggle.derive_seed(*left) != Gaggle.derive_seed(*right)


@given(
    text=st.text(min_size=0, max_size=40),
    rate=st.floats(min_value=0.0, max_value=0.3),
    seed=st.integers(min_value=0, max_value=2**32 - 1),
)
def test_typogre_length_change_stays_within_bound(text: str, rate: float, seed: int) -> None:
    result = typogre_module.fatfinger(text, rate=rate, seed=seed)

    if not text:
        assert result == ""
        return

    max_changes = math.ceil(len(text) * rate)
    min_len = max(len(text) - max_changes, 0)
    max_len = len(text) + max_changes
    assert min_len <= len(result) <= max_len


@settings(suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow])
@given(
    text=word_sequences,
    rate=st.floats(min_value=0.0, max_value=1.0),
    seed=st.integers(min_value=0, max_value=2**32 - 1),
)
def test_rushmore_preserves_first_token_and_respects_cap(text: str, rate: float, seed: int) -> None:
    words = text.split()

    result = rushmore_module.delete_random_words(text, rate=rate, seed=seed)
    result_words = result.split()
    assert result_words
    assert result_words[0] == words[0]

    candidate_count = len(words) - 1
    allowed = min(candidate_count, math.floor(candidate_count * rate))
    removed = len(words) - len(result_words)
    assert removed <= allowed


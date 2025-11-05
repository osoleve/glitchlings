import pytest

import glitchlings.zoo.core as core_module
from glitchlings import Typogre, summon
from glitchlings.zoo.core import Gaggle


def test_gaggle_determinism(sample_text):
    g1 = summon(["rushmore", "mim1c", "typogre", "redactyl", "spectroll"], seed=777)
    out1 = g1(sample_text)
    g2 = summon(["rushmore", "mim1c", "typogre", "redactyl", "spectroll"], seed=777)
    out2 = g2(sample_text)
    assert out1 == out2


def test_gaggle_seed_changes_output(sample_text):
    g1 = summon(["rushmore", "mim1c", "typogre", "redactyl", "spectroll"], seed=1)
    out1 = g1(sample_text)
    g2 = summon(["rushmore", "mim1c", "typogre", "redactyl", "spectroll"], seed=2)
    out2 = g2(sample_text)
    assert out1 != out2


def test_gaggle_ordering_stable(sample_text):
    # When summoned by name, built-ins choose a stable order by scope, then order, then name
    gaggle = summon(["typogre", "mim1c", "rushmore", "redactyl"], seed=42)
    expected = ["Redactyl", "Rushmore", "Typogre", "Mim1c"]
    assert [member.name for member in gaggle.apply_order] == expected


def test_gaggle_seed_derivation_regression():
    assert Gaggle.derive_seed(151, "Typogre", 0) == 13006513535068165406
    assert Gaggle.derive_seed(151, "Redactyl", 3) == 12503957440331561761


def test_summon_accepts_parameterized_specification():
    gaggle = summon(["Typogre(rate=0.05)"], seed=151)
    assert len(gaggle.apply_order) == 1
    member = gaggle.apply_order[0]
    assert isinstance(member, Typogre)
    assert member.rate == 0.05


def test_summon_rejects_positional_parameter_specifications():
    with pytest.raises(ValueError, match="keyword arguments"):
        summon(["Typogre(0.2)"])


def test_gaggle_requires_master_seed():
    glitchling = Typogre(rate=0.05)

    with pytest.raises(ValueError, match="master seed"):
        Gaggle([glitchling], seed=None)


def test_gaggle_detects_missing_plan_indices(monkeypatch):
    glitchlings = [Typogre(rate=0.01, seed=3), Typogre(rate=0.02, seed=5)]

    monkeypatch.setattr(
        core_module,
        "plan_glitchlings",
        lambda *_args, **_kwargs: [(0, 123456789)],
        raising=False,
    )

    with pytest.raises(RuntimeError, match="missing glitchlings"):
        Gaggle(glitchlings, seed=99)

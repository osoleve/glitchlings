from glitchlings import summon
from glitchlings.zoo.core import Gaggle


def test_gaggle_determinism(sample_text):
    g1 = summon(["reduple", "mim1c", "typogre", "rushmore", "redactyl"], seed=777)
    out1 = g1(sample_text)
    g2 = summon(["reduple", "mim1c", "typogre", "rushmore", "redactyl"], seed=777)
    out2 = g2(sample_text)
    assert out1 == out2


def test_gaggle_seed_changes_output(sample_text):
    g1 = summon(["reduple", "mim1c", "typogre", "rushmore", "redactyl"], seed=1)
    out1 = g1(sample_text)
    g2 = summon(["reduple", "mim1c", "typogre", "rushmore", "redactyl"], seed=2)
    out2 = g2(sample_text)
    assert out1 != out2


def test_gaggle_ordering_stable(sample_text):
    # When summoned by name, built-ins choose a stable order by scope, then order, then name
    g = summon(["typogre", "mim1c", "reduple", "rushmore"], seed=42)
    assert [g.name[0].lower() for g in g.apply_order][:2] == [
        "r",
        "r",
    ]


def test_gaggle_seed_derivation_regression():
    assert Gaggle.derive_seed(151, "Typogre", 0) == 13006513535068165406
    assert Gaggle.derive_seed(151, "Redactyl", 3) == 12503957440331561761

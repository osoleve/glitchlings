import string

from glitchlings.util import KEYNEIGHBORS


def test_standard_layouts_cover_alphabet() -> None:
    letters = set(string.ascii_lowercase)
    for layout_name in ("QWERTY", "DVORAK", "COLEMAK", "AZERTY"):
        layout = getattr(KEYNEIGHBORS, layout_name)
        missing = letters - set(layout)
        assert not missing, f"{layout_name} missing: {sorted(missing)}"


def test_layout_neighbor_expectations() -> None:
    qwerty = getattr(KEYNEIGHBORS, "QWERTY")
    assert {"q", "w", "s", "z"} <= set(qwerty["a"])

    azerty = getattr(KEYNEIGHBORS, "AZERTY")
    assert {"q", "z"} <= set(azerty["a"])

    dvorak = getattr(KEYNEIGHBORS, "DVORAK")
    assert {"a", "e"} <= set(dvorak["o"])

    colemak = getattr(KEYNEIGHBORS, "COLEMAK")
    assert {"j", "n"} <= set(colemak["h"])

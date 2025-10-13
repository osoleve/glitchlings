import string

from glitchlings.util import KEYNEIGHBORS


def test_standard_layouts_cover_alphabet() -> None:
    letters = set(string.ascii_lowercase)
    for layout_name in (
        "QWERTY",
        "DVORAK",
        "COLEMAK",
        "AZERTY",
        "QWERTZ",
        "SPANISH_QWERTY",
        "SWEDISH_QWERTY",
    ):
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

    qwertz = getattr(KEYNEIGHBORS, "QWERTZ")
    assert {"t", "u"} <= set(qwertz["z"])

    spanish = getattr(KEYNEIGHBORS, "SPANISH_QWERTY")
    assert {"s", "d", "x"} <= set(spanish["z"])

    swedish = getattr(KEYNEIGHBORS, "SWEDISH_QWERTY")
    assert {"å", "ö"} <= set(swedish["p"])

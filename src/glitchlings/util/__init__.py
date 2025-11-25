from collections.abc import Iterable

from glitchlings.zoo.transforms import (
    KeyNeighborMap,
    build_keyboard_neighbor_map,
)
from glitchlings.zoo.transforms import (
    compute_string_diffs as string_diffs,
)

__all__ = [
    "SAMPLE_TEXT",
    "string_diffs",
    "KeyNeighborMap",
    "KeyboardLayouts",
    "KeyNeighbors",
    "KEYNEIGHBORS",
]

SAMPLE_TEXT = (
    "One morning, when Gregor Samsa woke from troubled dreams, he found himself "
    "transformed in his bed into a horrible vermin. He lay on his armour-like back, and "
    "if he lifted his head a little he could see his brown belly, slightly domed and "
    "divided by arches into stiff sections. The bedding was hardly able to cover it and "
    "seemed ready to slide off any moment. His many legs, pitifully thin compared with "
    "the size of the rest of him, waved about helplessly as he looked."
)


KeyboardLayouts = dict[str, KeyNeighborMap]


_KEYNEIGHBORS: KeyboardLayouts = {
    "CURATOR_QWERTY": {
        "a": [*"qwsz"],
        "b": [*"vghn  "],
        "c": [*"xdfv  "],
        "d": [*"serfcx"],
        "e": [*"wsdrf34"],
        "f": [*"drtgvc"],
        "g": [*"ftyhbv"],
        "h": [*"gyujnb"],
        "i": [*"ujko89"],
        "j": [*"huikmn"],
        "k": [*"jilom,"],
        "l": [*"kop;.,"],
        "m": [*"njk,  "],
        "n": [*"bhjm  "],
        "o": [*"iklp90"],
        "p": [*"o0-[;l"],
        "q": [*"was 12"],
        "r": [*"edft45"],
        "s": [*"awedxz"],
        "t": [*"r56ygf"],
        "u": [*"y78ijh"],
        "v": [*"cfgb  "],
        "w": [*"q23esa"],
        "x": [*"zsdc  "],
        "y": [*"t67uhg"],
        "z": [*"asx"],
    }
}


def _register_layout(name: str, rows: Iterable[str]) -> None:
    _KEYNEIGHBORS[name] = build_keyboard_neighbor_map(rows)


_register_layout(
    "DVORAK",
    (
        "`1234567890[]\\",
        " ',.pyfgcrl/=\\",
        "  aoeuidhtns-",
        "   ;qjkxbmwvz",
    ),
)

_register_layout(
    "COLEMAK",
    (
        "`1234567890-=",
        " qwfpgjluy;[]\\",
        "  arstdhneio'",
        "   zxcvbkm,./",
    ),
)

_register_layout(
    "QWERTY",
    (
        "`1234567890-=",
        " qwertyuiop[]\\",
        "  asdfghjkl;'",
        "   zxcvbnm,./",
    ),
)

_register_layout(
    "AZERTY",
    (
        "²&é\"'(-è_çà)=",
        " azertyuiop^$",
        "  qsdfghjklmù*",
        "   <wxcvbn,;:!",
    ),
)

_register_layout(
    "QWERTZ",
    (
        "^1234567890ß´",
        " qwertzuiopü+",
        "  asdfghjklöä#",
        "   yxcvbnm,.-",
    ),
)

_register_layout(
    "SPANISH_QWERTY",
    (
        "º1234567890'¡",
        " qwertyuiop´+",
        "  asdfghjklñ´",
        "   <zxcvbnm,.-",
    ),
)

_register_layout(
    "SWEDISH_QWERTY",
    (
        "§1234567890+´",
        " qwertyuiopå¨",
        "  asdfghjklöä'",
        "   <zxcvbnm,.-",
    ),
)


class KeyNeighbors:
    def __init__(self) -> None:
        for layout_name, layout in _KEYNEIGHBORS.items():
            setattr(self, layout_name, layout)


KEYNEIGHBORS: KeyNeighbors = KeyNeighbors()

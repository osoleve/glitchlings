"""Keyboard layout neighbor maps for typo simulation.

This module centralizes keyboard layout data that was previously stored
directly in :mod:`glitchlings.util.__init__`. It defines adjacency maps
for various keyboard layouts used by typo-generating glitchlings.
"""

from __future__ import annotations

from collections.abc import Iterable

from glitchlings.zoo.transforms import (
    KeyNeighborMap,
    build_keyboard_neighbor_map,
)

__all__ = [
    "KeyboardLayouts",
    "KeyNeighbors",
    "KEYNEIGHBORS",
]

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
    """Attribute-based access to keyboard layout neighbor maps."""

    def __init__(self) -> None:
        for layout_name, layout in _KEYNEIGHBORS.items():
            setattr(self, layout_name, layout)


KEYNEIGHBORS: KeyNeighbors = KeyNeighbors()

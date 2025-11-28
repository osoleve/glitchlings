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
    "ShiftMap",
    "ShiftMaps",
    "SHIFT_MAPS",
]

KeyboardLayouts = dict[str, KeyNeighborMap]
ShiftMap = dict[str, str]
ShiftMaps = dict[str, ShiftMap]


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


def _uppercase_keys(layout: str) -> ShiftMap:
    mapping: ShiftMap = {}
    for key in _KEYNEIGHBORS.get(layout, {}):
        if key.isalpha():
            mapping[key] = key.upper()
    return mapping


def _with_letters(base: ShiftMap, layout: str) -> ShiftMap:
    mapping = dict(base)
    mapping.update(_uppercase_keys(layout))
    return mapping


def _qwerty_symbols() -> ShiftMap:
    return {
        "`": "~",
        "1": "!",
        "2": "@",
        "3": "#",
        "4": "$",
        "5": "%",
        "6": "^",
        "7": "&",
        "8": "*",
        "9": "(",
        "0": ")",
        "-": "_",
        "=": "+",
        "[": "{",
        "]": "}",
        "\\": "|",
        ";": ":",
        "'": '"',
        ",": "<",
        ".": ">",
        "/": "?",
    }


def _azerty_symbols() -> ShiftMap:
    return {
        "&": "1",
        "\u00e9": "2",
        '"': "3",
        "'": "4",
        "(": "5",
        "-": "6",
        "\u00e8": "7",
        "_": "8",
        "\u00e7": "9",
        "\u00e0": "0",
        ")": "\u00b0",
        "=": "+",
        "^": "\u00a8",
        "$": "\u00a3",
        "*": "\u00b5",
        "\u00f9": "%",
        "<": ">",
        ",": "?",
        ";": ".",
        ":": "/",
        "!": "\u00a7",
    }


def _qwertz_symbols() -> ShiftMap:
    return {
        "^": "\u00b0",
        "1": "!",
        "2": '"',
        "3": "\u00a7",
        "4": "$",
        "5": "%",
        "6": "&",
        "7": "/",
        "8": "(",
        "9": ")",
        "0": "=",
        "\u00df": "?",
        "\u00b4": "`",
        "+": "*",
        "#": "'",
        "-": "_",
        ",": ";",
        ".": ":",
        "\u00e4": "\u00c4",
        "\u00f6": "\u00d6",
        "\u00fc": "\u00dc",
    }


def _spanish_symbols() -> ShiftMap:
    return {
        "\u00ba": "\u00aa",
        "1": "!",
        "2": '"',
        "3": "\u00b7",
        "4": "$",
        "5": "%",
        "6": "&",
        "7": "/",
        "8": "(",
        "9": ")",
        "0": "=",
        "'": "?",
        "\u00a1": "\u00bf",
        "+": "*",
        "\u00b4": "\u00a8",
        "-": "_",
        ",": ";",
        ".": ":",
        "<": ">",
        "\u00f1": "\u00d1",
    }


def _swedish_symbols() -> ShiftMap:
    return {
        "\u00a7": "\u00bd",
        "1": "!",
        "2": '"',
        "3": "#",
        "4": "\u00a4",
        "5": "%",
        "6": "&",
        "7": "/",
        "8": "(",
        "9": ")",
        "0": "=",
        "+": "?",
        "\u00b4": "\u00a8",
        "-": "_",
        ",": ";",
        ".": ":",
        "<": ">",
        "\u00e5": "\u00c5",
        "\u00e4": "\u00c4",
        "\u00f6": "\u00d6",
    }


_SHIFT_MAPS: ShiftMaps = {
    "CURATOR_QWERTY": _with_letters(_qwerty_symbols(), "CURATOR_QWERTY"),
    "QWERTY": _with_letters(_qwerty_symbols(), "QWERTY"),
    "COLEMAK": _with_letters(_qwerty_symbols(), "COLEMAK"),
    "DVORAK": _with_letters(_qwerty_symbols(), "DVORAK"),
    "AZERTY": _with_letters(_azerty_symbols(), "AZERTY"),
    "QWERTZ": _with_letters(_qwertz_symbols(), "QWERTZ"),
    "SPANISH_QWERTY": _with_letters(_spanish_symbols(), "SPANISH_QWERTY"),
    "SWEDISH_QWERTY": _with_letters(_swedish_symbols(), "SWEDISH_QWERTY"),
}


class ShiftMapsAccessor:
    """Attribute-based access to per-layout shift maps."""

    def __init__(self) -> None:
        for layout_name, mapping in _SHIFT_MAPS.items():
            setattr(self, layout_name, mapping)


SHIFT_MAPS: ShiftMapsAccessor = ShiftMapsAccessor()

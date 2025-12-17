"""Keyboard layout neighbor maps for typo simulation.

This module centralizes keyboard layout data that was previously stored
directly in :mod:`glitchlings.util.__init__`. It defines adjacency maps
for various keyboard layouts used by typo-generating glitchlings.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = [
    "KeyboardLayouts",
    "KeyNeighbors",
    "KEYNEIGHBORS",
    "ShiftMap",
    "ShiftMaps",
    "SHIFT_MAPS",
    "KeyNeighborMap",
    "build_keyboard_neighbor_map",
    # Pre-serialized accessors for pipeline use
    "get_serialized_layout",
    "get_serialized_shift_map",
    # Motor coordination types
    "FingerAssignment",
    "FINGER_MAP",
    "MOTOR_WEIGHTS",
    "classify_transition",
]

# Type alias for keyboard neighbor maps
KeyNeighborMap = dict[str, list[str]]


def build_keyboard_neighbor_map(rows: Iterable[str]) -> KeyNeighborMap:
    """Derive 8-neighbour adjacency lists from keyboard layout rows.

    Each row represents a keyboard row with characters positioned by index.
    Spaces are treated as empty positions. Characters are normalized to lowercase.

    Args:
        rows: Iterable of strings representing keyboard rows, with
            characters positioned to reflect their physical layout.

    Returns:
        Dictionary mapping each lowercase character to its adjacent characters.

    Example:
        >>> rows = ["qwerty", " asdfg"]  # 'a' offset by 1
        >>> neighbors = build_keyboard_neighbor_map(rows)
        >>> neighbors['s']  # adjacent to q, w, e, a, d on QWERTY
        ['q', 'w', 'e', 'a', 'd']
    """
    grid: dict[tuple[int, int], str] = {}
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == " ":
                continue
            grid[(x, y)] = char.lower()

    neighbors: KeyNeighborMap = {}
    for (x, y), char in grid.items():
        seen: list[str] = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                candidate = grid.get((x + dx, y + dy))
                if candidate is None:
                    continue
                seen.append(candidate)
        # Preserve encounter order but drop duplicates for determinism
        deduped = list(dict.fromkeys(seen))
        neighbors[char] = deduped

    return neighbors


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

    def get(self, name: str) -> KeyNeighborMap | None:
        """Get a layout by name, returning None if not found."""
        return _KEYNEIGHBORS.get(name)


KEYNEIGHBORS: KeyNeighbors = KeyNeighbors()


# Pre-serialized layouts for pipeline use (avoids per-call dict comprehension)
# Format: {key: list(neighbors)} - lists instead of iterables for Rust FFI
_SERIALIZED_LAYOUTS: dict[str, dict[str, list[str]]] = {
    name: {k: list(v) for k, v in layout.items()} for name, layout in _KEYNEIGHBORS.items()
}


def get_serialized_layout(name: str) -> dict[str, list[str]] | None:
    """Get a pre-serialized layout for pipeline use.

    Returns the cached serialized form directly - do not mutate.
    """
    return _SERIALIZED_LAYOUTS.get(name)


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

    def get(self, name: str) -> ShiftMap | None:
        """Get a shift map by name, returning None if not found."""
        return _SHIFT_MAPS.get(name)


SHIFT_MAPS: ShiftMapsAccessor = ShiftMapsAccessor()


def get_serialized_shift_map(name: str) -> dict[str, str] | None:
    """Get a pre-serialized shift map for pipeline use.

    Returns the cached dict directly - do not mutate.
    """
    return _SHIFT_MAPS.get(name)


# ---------------------------------------------------------------------------
# Motor Coordination Types
# ---------------------------------------------------------------------------
# Based on the Aalto 136M Keystrokes dataset
# Dhakal et al. (2018). Observations on Typing from 136 Million Keystrokes. CHI '18.
# https://doi.org/10.1145/3173574.3174220

# Finger assignment: (hand, finger)
# hand: 0=left, 1=right, 2=thumb/space
# finger: 0=pinky, 1=ring, 2=middle, 3=index, 4=thumb
FingerAssignment = tuple[int, int]

# fmt: off
FINGER_MAP: dict[str, FingerAssignment] = {
    # Left pinky (hand=0, finger=0)
    '`': (0, 0), '1': (0, 0), 'q': (0, 0), 'a': (0, 0), 'z': (0, 0),
    '~': (0, 0), '!': (0, 0), 'Q': (0, 0), 'A': (0, 0), 'Z': (0, 0),
    # Left ring (hand=0, finger=1)
    '2': (0, 1), 'w': (0, 1), 's': (0, 1), 'x': (0, 1),
    '@': (0, 1), 'W': (0, 1), 'S': (0, 1), 'X': (0, 1),
    # Left middle (hand=0, finger=2)
    '3': (0, 2), 'e': (0, 2), 'd': (0, 2), 'c': (0, 2),
    '#': (0, 2), 'E': (0, 2), 'D': (0, 2), 'C': (0, 2),
    # Left index - two columns (hand=0, finger=3)
    '4': (0, 3), 'r': (0, 3), 'f': (0, 3), 'v': (0, 3),
    '5': (0, 3), 't': (0, 3), 'g': (0, 3), 'b': (0, 3),
    '$': (0, 3), 'R': (0, 3), 'F': (0, 3), 'V': (0, 3),
    '%': (0, 3), 'T': (0, 3), 'G': (0, 3), 'B': (0, 3),
    # Right index - two columns (hand=1, finger=3)
    '6': (1, 3), 'y': (1, 3), 'h': (1, 3), 'n': (1, 3),
    '7': (1, 3), 'u': (1, 3), 'j': (1, 3), 'm': (1, 3),
    '^': (1, 3), 'Y': (1, 3), 'H': (1, 3), 'N': (1, 3),
    '&': (1, 3), 'U': (1, 3), 'J': (1, 3), 'M': (1, 3),
    # Right middle (hand=1, finger=2)
    '8': (1, 2), 'i': (1, 2), 'k': (1, 2), ',': (1, 2),
    '*': (1, 2), 'I': (1, 2), 'K': (1, 2), '<': (1, 2),
    # Right ring (hand=1, finger=1)
    '9': (1, 1), 'o': (1, 1), 'l': (1, 1), '.': (1, 1),
    '(': (1, 1), 'O': (1, 1), 'L': (1, 1), '>': (1, 1),
    # Right pinky (hand=1, finger=0)
    '0': (1, 0), 'p': (1, 0), ';': (1, 0), '/': (1, 0),
    '-': (1, 0), '[': (1, 0), "'": (1, 0),
    ')': (1, 0), 'P': (1, 0), ':': (1, 0), '?': (1, 0),
    '_': (1, 0), '{': (1, 0), '"': (1, 0),
    '=': (1, 0), ']': (1, 0), '\\': (1, 0),
    '+': (1, 0), '}': (1, 0), '|': (1, 0),
    # Space - thumb (hand=2, finger=4)
    ' ': (2, 4),
}
# fmt: on

# Motor coordination weights derived from Aalto 136M Keystrokes dataset
# Keys: transition type -> weight multiplier
# Values normalized so cross_hand = 1.0 (baseline)
MOTOR_WEIGHTS: dict[str, dict[str, float]] = {
    # "Wet ink" - uncorrected errors (errors that survive to final output)
    # Same-finger errors are caught/corrected, cross-hand errors slip through
    "wet_ink": {
        "same_finger": 0.858,
        "same_hand": 0.965,
        "cross_hand": 1.0,
    },
    # "Hastily edited" - raw error distribution before correction
    # Same-finger errors occur most often but are easy to detect
    "hastily_edited": {
        "same_finger": 3.031,
        "same_hand": 1.101,
        "cross_hand": 1.0,
    },
    # Uniform weighting - all transitions equal (original behavior)
    "uniform": {
        "same_finger": 1.0,
        "same_hand": 1.0,
        "cross_hand": 1.0,
    },
}


def classify_transition(prev_char: str, curr_char: str) -> str:
    """Classify the motor coordination required for a key transition.

    Args:
        prev_char: The previous character typed.
        curr_char: The current character being typed.

    Returns:
        One of: 'same_finger', 'same_hand', 'cross_hand', 'space', or 'unknown'.
    """
    prev = FINGER_MAP.get(prev_char)
    curr = FINGER_MAP.get(curr_char)

    if prev is None or curr is None:
        return "unknown"

    prev_hand, prev_finger = prev
    curr_hand, curr_finger = curr

    # Space transitions (thumb) get their own category
    if prev_hand == 2 or curr_hand == 2:
        return "space"

    # Cross-hand transition
    if prev_hand != curr_hand:
        return "cross_hand"

    # Same-finger transition (same hand, same finger)
    if prev_finger == curr_finger:
        return "same_finger"

    # Same-hand transition (same hand, different finger)
    return "same_hand"

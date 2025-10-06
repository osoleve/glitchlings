import difflib
from collections.abc import Iterable

SAMPLE_TEXT = "One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked."


def string_diffs(a: str, b: str) -> list[list[tuple[str, str, str]]]:
    """
    Compare two strings using SequenceMatcher and return
    grouped adjacent opcodes (excluding 'equal' tags).

    Each element is a tuple: (tag, a_text, b_text).
    """
    sm = difflib.SequenceMatcher(None, a, b)
    ops: list[list[tuple[str, str, str]]] = []
    buffer: list[tuple[str, str, str]] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            # flush any buffered operations before skipping
            if buffer:
                ops.append(buffer)
                buffer = []
            continue

        # append operation to buffer
        buffer.append((tag, a[i1:i2], b[j1:j2]))

    # flush trailing buffer
    if buffer:
        ops.append(buffer)

    return ops


KeyNeighborMap = dict[str, list[str]]
KeyboardLayouts = dict[str, KeyNeighborMap]


def _build_neighbor_map(rows: Iterable[str]) -> KeyNeighborMap:
    """Derive 8-neighbour adjacency lists from keyboard layout rows."""

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
    _KEYNEIGHBORS[name] = _build_neighbor_map(rows)


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

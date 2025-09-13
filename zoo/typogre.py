from .core import Glitchling, AttackWave, AttackOrder
from util import KEYNEIGHBORS
import random
import re
from typing import Literal

# Removed dependency on external 'typo' library for deterministic control.


def unichar(text: str, rng: random.Random) -> str:
    """Collapse one random doubled letter (like 'ee' in 'seed') to a single occurrence."""
    # capture doubled letter followed by trailing word chars so we don't match punctuation
    matches = list(re.finditer(r"((.)\2)(?=\w)", text))
    if not matches:
        return text
    m = rng.choice(matches)
    start, end = m.span(1)
    # Replace the doubled pair with a single char
    return text[:start] + text[start] + text[end:]


def subs(text, index, rng: random.Random, key_neighbors=None):
    if key_neighbors is None:
        key_neighbors = getattr(KEYNEIGHBORS, "CURATOR_QWERTY")
    char = text[index]
    neighbors = key_neighbors.get(char, [])
    if not neighbors:
        return text
    new_char = rng.choice(neighbors)
    return text[:index] + new_char + text[index + 1 :]


def indel(
    text: str,
    index: int,
    op: Literal["delete", "insert", "swap"],
    rng: random.Random,
    key_neighbors=None,
):
    if key_neighbors is None:
        key_neighbors = getattr(KEYNEIGHBORS, "CURATOR_QWERTY")
    if index < 0 or index >= len(text):
        return text
    if op == "delete":
        return text[:index] + text[index + 1 :]
    if op == "swap":
        if index >= len(text) - 1:
            return text
        return text[:index] + text[index + 1] + text[index] + text[index + 2 :]
    # insert (choose neighbor of this char) – if none, just duplicate char
    char = text[index]
    candidates = key_neighbors.get(char, []) or [char]
    new_char = rng.choice(candidates)
    return text[:index] + new_char + text[index:]


def repeated_char(text: str, rng: random.Random) -> str:
    """Repeat a random non-space character once (e.g., 'cat' -> 'caat')."""
    positions = [i for i, c in enumerate(text) if not c.isspace()]
    if not positions:
        return text
    i = rng.choice(positions)
    return text[:i] + text[i] + text[i:]


def random_space(text: str, rng: random.Random) -> str:
    """Insert a space at a random boundary between characters (excluding ends)."""
    if len(text) < 2:
        return text
    idx = rng.randrange(1, len(text))
    return text[:idx] + " " + text[idx:]


def skipped_space(text: str, rng: random.Random) -> str:
    """Remove a random existing single space (simulate missed space press)."""
    space_positions = [m.start() for m in re.finditer(r" ", text)]
    if not space_positions:
        return text
    idx = rng.choice(space_positions)
    # collapse this one space: remove it
    return text[:idx] + text[idx + 1 :]


def fair_game(text, preserve_first_last=False) -> list[int]:
    """Return the indices of characters that can be modified, respecting preserve_first_last.

    If preserve_first_last is True, the first and last character of words are excluded unless there are 3 or fewer characters.
    """
    positions = []
    words = re.finditer(r"\b\w+\b", text)
    for word in words:
        start, end = word.span()
        if preserve_first_last and end - start > 2:
            positions.extend(range(start + 1, end - 1))
        else:
            positions.extend(range(start, end))
    return positions


def fatfinger(
    text: str,
    max_change_rate: float = 0.02,
    preserve_first_last: bool = False,
    keyboard: str = "CURATOR_QWERTY",
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str | list[dict]:
    """Introduce character-level 'fat finger' style edits deterministically with provided rng."""
    if rng is None:
        rng = random.Random(seed)
    if not text:
        return ""

    _text = text
    max_changes = max(1, int(len(text) * max_change_rate))

    # Pre-draw all actions and base positions from the original text length to ensure reset reproducibility.
    base_positions = fair_game(text, preserve_first_last)
    if not base_positions:
        return _text

    actions_drawn = [
        rng.choice(
            [
                "char_swap",
                "missing_char",
                "extra_char",
                "nearby_char",
                "skipped_space",
                "unichar",
                "repeated_char",
                "random_space",
            ]
        )
        for _ in range(max_changes)
    ]
    pos_drawn = [rng.choice(base_positions) for _ in range(max_changes)]
    for action, base_idx in zip(actions_drawn, pos_drawn):
        if action == "char_swap":
            idx = base_idx
            if idx is not None and idx < len(_text) - 1:
                if idx + 1 in base_positions:
                    _text = _text[:idx] + _text[idx + 1] + _text[idx] + _text[idx + 2 :]
        elif action == "missing_char":
            idx = base_idx
            if idx is not None:
                _text = _text[:idx] + _text[idx + 1 :]
        elif action == "extra_char":
            idx = base_idx
            if idx is not None and idx < len(_text):
                char = _text[idx]
                layout = getattr(KEYNEIGHBORS, keyboard)
                neighbors = layout.get(char.lower(), []) or [char]
                ins = rng.choice(neighbors) or char
                _text = _text[:idx] + ins + _text[idx:]
        elif action == "nearby_char":
            idx = base_idx
            if idx is not None:
                char = _text[idx]
                layout = getattr(KEYNEIGHBORS, keyboard)
                neighbors = layout.get(char.lower(), [])
                if neighbors:
                    rep = rng.choice(neighbors)
                    _text = _text[:idx] + rep + _text[idx + 1 :]
        elif action == "skipped_space":
            _text = skipped_space(_text, rng)
        elif action == "random_space":
            _text = random_space(_text, rng)
        elif action == "unichar":
            _text = unichar(_text, rng)
        elif action == "repeated_char":
            _text = repeated_char(_text, rng)

    return _text


typogre = Glitchling(
    name="Typogre",
    corruption_function=fatfinger,
    scope=AttackWave.CHARACTER,
    order=AttackOrder.EARLY,
)

from .core import Glitchling, AttackWave, AttackOrder
from util import KEYNEIGHBORS
import random
import re
from typing import Literal, Optional

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


def _is_word_char(c: str) -> bool:
    return c.isalnum() or c == "_"


def _eligible_idx(s: str, i: int, preserve_first_last: bool) -> bool:
    """O(1) check whether index i is eligible under preserve_first_last."""
    if i < 0 or i >= len(s):
        return False
    if not _is_word_char(s[i]):
        return False
    if not preserve_first_last:
        return True
    # interior-of-word only
    left_ok = i > 0 and _is_word_char(s[i - 1])
    right_ok = i + 1 < len(s) and _is_word_char(s[i + 1])
    return left_ok and right_ok


def _draw_eligible_index(
    rng: random.Random, s: str, preserve_first_last: bool, max_tries: int = 16
) -> Optional[int]:
    """Try a few uniform draws; if none hit, do a single wraparound scan."""
    n = len(s)
    if n == 0:
        return None
    for _ in range(max_tries):
        i = rng.randrange(n)
        if _eligible_idx(s, i, preserve_first_last):
            return i
    # Fallback: linear scan starting from a random point (rare path)
    start = rng.randrange(n)
    i = start
    while True:
        if _eligible_idx(s, i, preserve_first_last):
            return i
        i += 1
        if i == n:
            i = 0
        if i == start:
            return None


def fatfinger(
    text: str,
    max_change_rate: float = 0.02,
    preserve_first_last: bool = False,
    keyboard: str = "CURATOR_QWERTY",
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Introduce character-level "fat finger" edits.

    Parameters
    - text: Input string to corrupt.
    - max_change_rate: Max proportion of characters to edit (default 0.02).
    - preserve_first_last: If True, avoid modifying first/last character of words (default False).
    - keyboard: Name of keyboard neighbor map from util.KEYNEIGHBORS to use (default "CURATOR_QWERTY").
    - seed: Optional seed used if `rng` is not provided; creates a dedicated Random.
    - rng: Optional random.Random to use; if provided, overrides `seed`.

    Notes
    - Chooses indices lazily from the current text after each edit to keep offsets valid.
    - Uses the glitchling's own RNG for determinism when run via Gaggle/summon.
    """
    if rng is None:
        rng = random.Random(seed)
    if not text:
        return ""

    s = text
    max_changes = max(1, int(len(s) * max_change_rate))

    # Prebind for speed
    layout = getattr(KEYNEIGHBORS, keyboard)
    choose = rng.choice

    # Actions that require a specific index vs. "global" actions
    positional_actions = ("char_swap", "missing_char", "extra_char", "nearby_char")
    global_actions = ("skipped_space", "random_space", "unichar", "repeated_char")
    all_actions = positional_actions + global_actions

    # Pre-draw action types (cheap); pick indices lazily on each step
    actions_drawn = [choose(all_actions) for _ in range(max_changes)]

    for action in actions_drawn:
        if action in positional_actions:
            idx = _draw_eligible_index(rng, s, preserve_first_last)
            if idx is None:
                continue  # nothing eligible; skip

            if action == "char_swap":
                # Try swapping to the right; if not possible, optionally try left
                j = idx + 1
                if j < len(s) and (
                    not preserve_first_last or _eligible_idx(s, j, True)
                ):
                    s = s[:idx] + s[j] + s[idx] + s[j + 1 :]
                else:
                    j = idx - 1
                    if j >= 0 and (
                        not preserve_first_last or _eligible_idx(s, j, True)
                    ):
                        s = s[:j] + s[idx] + s[j] + s[idx + 1 :]
                    # else: give up this action

            elif action == "missing_char":
                s = s[:idx] + s[idx + 1 :]

            elif action == "extra_char":
                ch = s[idx]
                neighbors = layout.get(ch.lower(), []) or [ch]
                ins = choose(neighbors) or ch
                s = s[:idx] + ins + s[idx:]

            elif action == "nearby_char":
                ch = s[idx]
                neighbors = layout.get(ch.lower(), [])
                if neighbors:
                    rep = choose(neighbors)
                    s = s[:idx] + rep + s[idx + 1 :]

        else:
            # "Global" actions that internally pick their own positions
            if action == "skipped_space":
                s = skipped_space(s, rng)
            elif action == "random_space":
                s = random_space(s, rng)
            elif action == "unichar":
                s = unichar(s, rng)
            elif action == "repeated_char":
                s = repeated_char(s, rng)

    return s


typogre = Glitchling(
    name="Typogre",
    corruption_function=fatfinger,
    scope=AttackWave.CHARACTER,
    order=AttackOrder.EARLY,
)

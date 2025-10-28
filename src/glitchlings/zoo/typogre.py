from __future__ import annotations

import math
import random
from typing import Any, Optional, cast

from ..util import KEYNEIGHBORS
from ._rate import resolve_rate
from ._rust_extensions import get_rust_operation
from .core import AttackOrder, AttackWave, Glitchling

# Load Rust-accelerated operation if available
_fatfinger_rust = get_rust_operation("fatfinger")


def _python_unichar(text: str, rng: random.Random) -> str:
    """Collapse one random doubled letter (like 'ee' in 'seed') to a single occurrence."""
    import re

    matches = list(re.finditer(r"((.)\2)(?=\w)", text))
    if not matches:
        return text
    start, end = rng.choice(matches).span(1)
    return text[:start] + text[start] + text[end:]


def _python_skipped_space(text: str, rng: random.Random) -> str:
    import re

    space_positions = [m.start() for m in re.finditer(r" ", text)]
    if not space_positions:
        return text
    idx = rng.choice(space_positions)
    return text[:idx] + text[idx + 1 :]


def _python_random_space(text: str, rng: random.Random) -> str:
    if len(text) < 2:
        return text
    idx = rng.randrange(1, len(text))
    return text[:idx] + " " + text[idx:]


def _python_repeated_char(text: str, rng: random.Random) -> str:
    positions = [i for i, c in enumerate(text) if not c.isspace()]
    if not positions:
        return text
    i = rng.choice(positions)
    return text[:i] + text[i] + text[i:]


def _python_is_word_char(c: str) -> bool:
    return c.isalnum() or c == "_"


def _python_eligible_idx(s: str, i: int) -> bool:
    if i < 0 or i >= len(s):
        return False
    if not _python_is_word_char(s[i]):
        return False
    left_ok = i > 0 and _python_is_word_char(s[i - 1])
    right_ok = i + 1 < len(s) and _python_is_word_char(s[i + 1])
    return left_ok and right_ok


def _python_draw_eligible_index(rng: random.Random, s: str, max_tries: int = 16) -> Optional[int]:
    n = len(s)
    if n == 0:
        return None
    for _ in range(max_tries):
        i = rng.randrange(n)
        if _python_eligible_idx(s, i):
            return i
    start = rng.randrange(n)
    i = start
    while True:
        if _python_eligible_idx(s, i):
            return i
        i += 1
        if i == n:
            i = 0
        if i == start:
            return None


def _fatfinger_python(
    text: str,
    *,
    rate: float,
    layout: dict[str, list[str]],
    rng: random.Random,
) -> str:
    if rate <= 0.0:
        return text

    s = text
    max_changes = math.ceil(len(s) * rate)
    if max_changes == 0:
        return s

    positional_actions = ("char_swap", "missing_char", "extra_char", "nearby_char")
    global_actions = ("skipped_space", "random_space", "unichar", "repeated_char")
    all_actions = positional_actions + global_actions

    actions_drawn = [rng.choice(all_actions) for _ in range(max_changes)]

    for action in actions_drawn:
        if action in positional_actions:
            idx = _python_draw_eligible_index(rng, s)
            if idx is None:
                continue
            if action == "char_swap":
                j = idx + 1
                s = s[:idx] + s[j] + s[idx] + s[j + 1 :]
            elif action == "missing_char":
                if _python_eligible_idx(s, idx):
                    s = s[:idx] + s[idx + 1 :]
            elif action == "extra_char":
                ch = s[idx]
                neighbors = layout.get(ch.lower(), []) or [ch]
                ins = rng.choice(neighbors) or ch
                s = s[:idx] + ins + s[idx:]
            elif action == "nearby_char":
                ch = s[idx]
                neighbors = layout.get(ch.lower(), [])
                if neighbors:
                    rep = rng.choice(neighbors)
                    s = s[:idx] + rep + s[idx + 1 :]
        else:
            if action == "skipped_space":
                s = _python_skipped_space(s, rng)
            elif action == "random_space":
                s = _python_random_space(s, rng)
            elif action == "unichar":
                s = _python_unichar(s, rng)
            elif action == "repeated_char":
                s = _python_repeated_char(s, rng)
    return s


def fatfinger(
    text: str,
    rate: float | None = None,
    keyboard: str = "CURATOR_QWERTY",
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Introduce character-level "fat finger" edits with a Rust fast path."""
    effective_rate = resolve_rate(rate=rate, default=0.02)

    if rng is None:
        rng = random.Random(seed)
    if not text:
        return ""

    clamped_rate = max(0.0, effective_rate)
    if clamped_rate == 0.0:
        return text

    layout = getattr(KEYNEIGHBORS, keyboard)

    if _fatfinger_rust is not None:
        return cast(
            str,
            _fatfinger_rust(text, max_change_rate=clamped_rate, layout=layout, rng=rng),
        )

    return _fatfinger_python(text, rate=clamped_rate, layout=layout, rng=rng)


class Typogre(Glitchling):
    """Glitchling that introduces deterministic keyboard-typing errors."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        keyboard: str = "CURATOR_QWERTY",
        seed: int | None = None,
    ) -> None:
        effective_rate = resolve_rate(rate=rate, default=0.02)
        super().__init__(
            name="Typogre",
            corruption_function=fatfinger,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.EARLY,
            seed=seed,
            rate=effective_rate,
            keyboard=keyboard,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            return None

        keyboard = self.kwargs.get("keyboard", "CURATOR_QWERTY")
        layout = getattr(KEYNEIGHBORS, str(keyboard), None)
        if layout is None:
            return None

        serialized_layout = {key: list(value) for key, value in layout.items()}

        return {
            "type": "typo",
            "rate": float(rate),
            "keyboard": str(keyboard),
            "layout": serialized_layout,
        }


typogre = Typogre()


__all__ = ["Typogre", "typogre"]

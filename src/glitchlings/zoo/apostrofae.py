"""Smart-quote glitchling that swaps straight quotes for fancy counterparts."""

from __future__ import annotations

import json
import random
from functools import cache
from importlib import resources
from typing import Any, Callable, Sequence, cast

from .core import AttackOrder, AttackWave, Gaggle, Glitchling

try:  # pragma: no cover - compiled extension not present in pure-Python envs
    from glitchlings._zoo_rust import apostrofae as _apostrofae_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _apostrofae_rust: Callable[[str, random.Random], str] | None = None


@cache
def _load_replacement_pairs() -> dict[str, list[tuple[str, str]]]:
    """Load the curated mapping of straight quotes to fancy pairs."""

    resource = resources.files(f"{__package__}.assets").joinpath("apostrofae_pairs.json")
    with resource.open("r", encoding="utf-8") as handle:
        data: dict[str, list[Sequence[str]]] = json.load(handle)

    parsed: dict[str, list[tuple[str, str]]] = {}
    for straight, replacements in data.items():
        parsed[straight] = [(pair[0], pair[1]) for pair in replacements if len(pair) == 2]
    return parsed


def _find_quote_pairs(text: str) -> list[tuple[int, int, str]]:
    """Return all balanced pairs of straight quotes in ``text``.

    The search walks the string once, pairing sequential occurrences of each quote
    glyph. Unmatched openers remain untouched so contractions (e.g. ``it's``)
    survive unmodified.
    """

    stacks: dict[str, int | None] = {'"': None, "'": None, "`": None}
    pairs: list[tuple[int, int, str]] = []

    for index, ch in enumerate(text):
        if ch not in stacks:
            continue
        start = stacks[ch]
        if start is None:
            stacks[ch] = index
        else:
            pairs.append((start, index, ch))
            stacks[ch] = None

    return pairs


def _apostrofae_python(text: str, *, rng: random.Random) -> str:
    """Python fallback that replaces paired straight quotes with fancy glyphs."""

    pairs = _load_replacement_pairs()
    candidates = _find_quote_pairs(text)
    if not candidates:
        return text

    chars = list(text)
    for start, end, glyph in candidates:
        options = pairs.get(glyph)
        if not options:
            continue
        left, right = rng.choice(options)
        chars[start] = left
        chars[end] = right
    return "".join(chars)


def smart_quotes(
    text: str,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Replace straight quotes, apostrophes, and backticks with fancy pairs."""

    if not text:
        return text

    if rng is None:
        rng = random.Random(seed)

    if _apostrofae_rust is not None:
        return cast(str, _apostrofae_rust(text, rng))

    return _apostrofae_python(text, rng=rng)


class Apostrofae(Glitchling):
    """Glitchling that swaps straight quotes for decorative Unicode pairs."""

    def __init__(self, *, seed: int | None = None) -> None:
        self._master_seed: int | None = seed
        super().__init__(
            name="Apostrofae",
            corruption_function=smart_quotes,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.NORMAL,
            seed=seed,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        return {"type": "apostrofae"}

    def reset_rng(self, seed: int | None = None) -> None:  # pragma: no cover - exercised indirectly
        if seed is not None:
            self._master_seed = seed
            super().reset_rng(seed)
            if self.seed is None:
                return
            derived = Gaggle.derive_seed(int(seed), self.name, 0)
            self.seed = int(derived)
            self.rng = random.Random(self.seed)
            self.kwargs["seed"] = self.seed
        else:
            super().reset_rng(None)


apostrofae = Apostrofae()


__all__ = ["Apostrofae", "apostrofae", "smart_quotes"]

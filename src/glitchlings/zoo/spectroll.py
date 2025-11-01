from __future__ import annotations

import random
import re
from itertools import zip_longest

from .core import AttackOrder, AttackWave, Glitchling

_CANONICAL_COLOR_MAP: dict[str, str] = {
    "red": "blue",
    "blue": "red",
    "green": "lime",
    "lime": "green",
    "yellow": "purple",
    "purple": "yellow",
    "orange": "cyan",
    "cyan": "orange",
    "magenta": "teal",
    "teal": "magenta",
    "black": "white",
    "white": "black",
}

_VALID_MODES = {"literal", "drift"}

_COLOR_PATTERN = re.compile(
    r"\b(?P<color>"
    + "|".join(sorted(_CANONICAL_COLOR_MAP, key=len, reverse=True))
    + r")(?P<suffix>[a-zA-Z]*)\b",
    re.IGNORECASE,
)

_COLOR_ADJACENCY: dict[str, tuple[str, ...]] = {
    "red": ("orange", "magenta", "purple"),
    "blue": ("cyan", "teal", "purple"),
    "green": ("teal", "cyan", "yellow"),
    "lime": ("yellow", "white", "cyan"),
    "yellow": ("orange", "lime", "white"),
    "purple": ("magenta", "red", "blue"),
    "orange": ("red", "yellow", "magenta"),
    "cyan": ("blue", "green", "teal"),
    "magenta": ("purple", "red", "blue"),
    "teal": ("cyan", "green", "blue"),
    "black": ("purple", "blue", "teal"),
    "white": ("yellow", "lime", "cyan"),
}


def _apply_case(template: str, replacement: str) -> str:
    if not template:
        return replacement
    if template.isupper():
        return replacement.upper()
    if template.islower():
        return replacement.lower()
    if template[0].isupper() and template[1:].islower():
        return replacement.capitalize()

    characters: list[str] = []
    for repl_char, template_char in zip_longest(replacement, template, fillvalue=""):
        if template_char.isupper():
            characters.append(repl_char.upper())
        elif template_char.islower():
            characters.append(repl_char.lower())
        else:
            characters.append(repl_char)
    return "".join(characters)


def _harmonize_suffix(original: str, replacement: str, suffix: str) -> str:
    if not suffix:
        return suffix

    if (
        original
        and suffix
        and original[-1].lower() == suffix[0].lower()
        and replacement[-1].lower() != suffix[0].lower()
    ):
        return suffix[1:]
    return suffix


def _normalize_mode(mode: str | None) -> str:
    normalized = "literal" if mode is None else mode.lower()
    if normalized not in _VALID_MODES:
        valid = ", ".join(sorted(_VALID_MODES))
        raise ValueError(f"Unsupported Spectroll mode '{mode}'. Expected one of: {valid}")
    return normalized


def swap_colors(
    text: str,
    *,
    seed: int | None = None,
    mode: str = "literal",
    rng: random.Random | None = None,
) -> str:
    """Swap canonical colour words for their partners.

    Examples:
        >>> swap_colors("red green blue")
        'blue lime red'
        >>> swap_colors("red green blue", mode="drift", seed=42)
        'purple teal cyan'
    """

    normalized_mode = _normalize_mode(mode)
    active_rng = rng if rng is not None else random.Random(seed)

    def replace(match: re.Match[str]) -> str:
        base = match.group("color")
        suffix = match.group("suffix") or ""
        canonical = base.lower()

        replacement_base: str | None
        if normalized_mode == "literal":
            replacement_base = _CANONICAL_COLOR_MAP.get(canonical)
        else:
            palette = _COLOR_ADJACENCY.get(canonical)
            if palette:
                replacement_base = active_rng.choice(palette)
            else:
                replacement_base = _CANONICAL_COLOR_MAP.get(canonical)

        if not replacement_base:
            return match.group(0)

        suffix_fragment = _harmonize_suffix(base, replacement_base, suffix)
        adjusted = _apply_case(base, replacement_base)
        return f"{adjusted}{suffix_fragment}"

    return _COLOR_PATTERN.sub(replace, text)


class Spectroll(Glitchling):
    """Glitchling that remaps colour terms to alternate hues."""

    def __init__(
        self,
        *,
        mode: str = "literal",
        seed: int | None = None,
    ) -> None:
        normalized_mode = _normalize_mode(mode)
        super().__init__(
            name="Spectroll",
            corruption_function=swap_colors,
            scope=AttackWave.WORD,
            order=AttackOrder.NORMAL,
            seed=seed,
            mode=normalized_mode,
        )


spectroll = Spectroll()


__all__ = ["Spectroll", "spectroll", "swap_colors"]

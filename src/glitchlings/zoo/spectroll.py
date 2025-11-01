from __future__ import annotations

import random
import re

from glitchlings.lexicon import compile_replacement_pattern, substitute_from_dictionary

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

_COLOR_PATTERN = compile_replacement_pattern(
    _CANONICAL_COLOR_MAP.keys(),
    suffix_pattern=r"(?P<suffix>[a-zA-Z]*)",
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

_LITERAL_COLOR_DICTIONARY: dict[str, tuple[str, ...]] = {
    color: (replacement,)
    for color, replacement in _CANONICAL_COLOR_MAP.items()
}

_DRIFT_COLOR_DICTIONARY: dict[str, tuple[str, ...]] = {
    color: tuple(_COLOR_ADJACENCY.get(color, ())) or (replacement,)
    for color, replacement in _CANONICAL_COLOR_MAP.items()
}

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
    dictionary = (
        _LITERAL_COLOR_DICTIONARY
        if normalized_mode == "literal"
        else _DRIFT_COLOR_DICTIONARY
    )

    def _spectroll_transform(match: re.Match[str], replacement: str) -> str:
        suffix = match.group("suffix") or ""
        base = match.group("key") or ""
        suffix_fragment = _harmonize_suffix(base, replacement, suffix)
        return f"{replacement}{suffix_fragment}"

    return substitute_from_dictionary(
        text,
        dictionary,
        rate=1.0,
        rng=active_rng,
        pattern=_COLOR_PATTERN,
        transform=_spectroll_transform,
    )


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

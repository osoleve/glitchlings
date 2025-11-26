"""Boundary validation layer for glitchling parameters.

This module centralizes all input validation, type coercion, and defensive checks
for glitchling parameters. Functions here are called at module boundaries (CLI,
public API entry points, configuration loaders) to ensure that invalid data is
rejected early.

**Design Philosophy:**

All functions in this module are *pure* - they perform validation and coercion
based solely on their inputs, without side effects. They are intended to be
called once at the boundary where untrusted input enters the system. Core
transformation functions that call these validation helpers can then trust
their inputs without re-validating.

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

import math
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeVar, cast

# ---------------------------------------------------------------------------
# Rate Validation (universal)
# ---------------------------------------------------------------------------


def clamp_rate(value: float, *, allow_nan: bool = False) -> float:
    """Clamp a rate value to [0.0, infinity), optionally treating NaN as 0.0.

    Args:
        value: The rate to clamp.
        allow_nan: If False (default), NaN values become 0.0.

    Returns:
        The clamped rate value.
    """
    if math.isnan(value):
        return 0.0 if not allow_nan else value
    return max(0.0, value)


def clamp_rate_unit(value: float, *, allow_nan: bool = False) -> float:
    """Clamp a rate value to [0.0, 1.0], optionally treating NaN as 0.0.

    Args:
        value: The rate to clamp.
        allow_nan: If False (default), NaN values become 0.0.

    Returns:
        The clamped rate value in range [0.0, 1.0].
    """
    if math.isnan(value):
        return 0.0 if not allow_nan else value
    return max(0.0, min(1.0, value))


def resolve_rate(
    value: float | None,
    default: float,
    *,
    clamp: bool = True,
    unit_interval: bool = False,
) -> float:
    """Resolve a rate parameter, applying defaults and optional clamping.

    Args:
        value: The user-provided rate, or None for default.
        default: The default rate to use when value is None.
        clamp: Whether to clamp the result to non-negative.
        unit_interval: If True, clamp to [0.0, 1.0] instead of [0.0, inf).

    Returns:
        The resolved, optionally clamped rate.
    """
    effective = default if value is None else value
    if not clamp:
        return effective
    return clamp_rate_unit(effective) if unit_interval else clamp_rate(effective)


# ---------------------------------------------------------------------------
# Mim1c Validation
# ---------------------------------------------------------------------------


def normalise_mim1c_classes(
    value: object,
) -> tuple[str, ...] | Literal["all"] | None:
    """Normalize Mim1c homoglyph class specification.

    Args:
        value: User input - None, "all", a single class name, or an iterable.

    Returns:
        Normalized tuple of class names, literal "all", or None.

    Raises:
        TypeError: If value is not None, string, or iterable.
    """
    if value is None:
        return None
    if isinstance(value, str):
        if value.lower() == "all":
            return "all"
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    raise TypeError("classes must be an iterable of strings or 'all'")


def normalise_mim1c_banned(value: object) -> tuple[str, ...] | None:
    """Normalize Mim1c banned character specification.

    Args:
        value: User input - None, a string of characters, or an iterable.

    Returns:
        Normalized tuple of banned characters, or None.

    Raises:
        TypeError: If value is not None, string, or iterable.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return tuple(value)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    raise TypeError("banned_characters must be an iterable of strings")


# ---------------------------------------------------------------------------
# Ekkokin Validation
# ---------------------------------------------------------------------------


def normalise_homophone_group(group: Sequence[str]) -> tuple[str, ...]:
    """Return a tuple of lowercase homophones preserving original order.

    Uses dict.fromkeys to preserve ordering while de-duplicating.

    Args:
        group: Sequence of homophone words.

    Returns:
        De-duplicated tuple of lowercase words.
    """
    return tuple(dict.fromkeys(word.lower() for word in group if word))


def build_homophone_lookup(
    groups: Iterable[Sequence[str]],
) -> Mapping[str, tuple[str, ...]]:
    """Return a mapping from word -> homophone group.

    Args:
        groups: Iterable of homophone word groups.

    Returns:
        Dictionary mapping each word to its normalized group.
    """
    lookup: dict[str, tuple[str, ...]] = {}
    for group in groups:
        normalised = normalise_homophone_group(group)
        if len(normalised) < 2:
            continue
        for word in normalised:
            lookup[word] = normalised
    return lookup


# ---------------------------------------------------------------------------
# Rushmore Validation
# ---------------------------------------------------------------------------

# Import enum locally to avoid circular dependencies at module level
# The RushmoreMode enum is defined in rushmore.py but we need its values here
# for mode validation. We use string-based validation to avoid the import cycle.

_RUSHMORE_MODE_ALIASES: dict[str, str] = {
    "delete": "delete",
    "drop": "delete",
    "rushmore": "delete",
    "duplicate": "duplicate",
    "reduplicate": "duplicate",
    "repeat": "duplicate",
    "swap": "swap",
    "adjacent": "swap",
}

_RUSHMORE_EXECUTION_ORDER: tuple[str, ...] = ("delete", "duplicate", "swap")


def normalize_rushmore_mode_item(value: str) -> list[str]:
    """Parse a single Rushmore mode specification into canonical mode names.

    Args:
        value: A mode name, alias, or compound expression like "delete+duplicate".

    Returns:
        List of canonical mode names ("delete", "duplicate", "swap").

    Raises:
        ValueError: If the mode name is not recognized.
    """
    text = str(value).strip().lower()
    if not text:
        return []

    if text in {"all", "any", "full"}:
        return list(_RUSHMORE_EXECUTION_ORDER)

    tokens = [token for token in re.split(r"[+,\s]+", text) if token]
    if not tokens:
        return []

    modes: list[str] = []
    for token in tokens:
        mode = _RUSHMORE_MODE_ALIASES.get(token)
        if mode is None:
            raise ValueError(f"Unsupported Rushmore mode '{value}'")
        modes.append(mode)
    return modes


def normalize_rushmore_modes(
    modes: str | Iterable[str] | None,
    *,
    default: str = "delete",
) -> tuple[str, ...]:
    """Normalize Rushmore mode specification to canonical tuple.

    Args:
        modes: User input - None, single mode string, or iterable of modes.
        default: Default mode when input is None or empty.

    Returns:
        Tuple of unique canonical mode names in insertion order.
    """
    if modes is None:
        candidates: Sequence[str] = (default,)
    elif isinstance(modes, str):
        candidates = (modes,)
    else:
        collected = tuple(modes)
        candidates = collected if collected else (default,)

    resolved: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        for mode in normalize_rushmore_mode_item(candidate):
            if mode not in seen:
                seen.add(mode)
                resolved.append(mode)

    if not resolved:
        return (default,)
    return tuple(resolved)


@dataclass(frozen=True)
class RushmoreRateConfig:
    """Resolved rate configuration for a single Rushmore mode."""

    mode: str
    rate: float
    is_default: bool = False


def resolve_rushmore_mode_rate(
    *,
    mode: str,
    global_rate: float | None,
    specific_rate: float | None,
    default_rates: Mapping[str, float],
    allow_default: bool,
) -> float | None:
    """Resolve the effective rate for a single Rushmore mode.

    Args:
        mode: The canonical mode name ("delete", "duplicate", "swap").
        global_rate: User-provided global rate, or None.
        specific_rate: User-provided mode-specific rate, or None.
        default_rates: Mapping of mode names to default rates.
        allow_default: Whether to fall back to defaults when no rate provided.

    Returns:
        The resolved rate, or None if no rate available and defaults disallowed.
    """
    baseline = specific_rate if specific_rate is not None else global_rate
    if baseline is None:
        if not allow_default:
            return None
        baseline = default_rates.get(mode)
        if baseline is None:
            return None

    value = float(baseline)
    value = max(0.0, value)
    if mode == "swap":
        value = min(1.0, value)
    return value


# ---------------------------------------------------------------------------
# Keyboard Layout Validation
# ---------------------------------------------------------------------------

T = TypeVar("T")


def validate_keyboard_layout(
    keyboard: str,
    layouts: object,
    *,
    context: str = "keyboard layout",
) -> Mapping[str, Sequence[str]]:
    """Validate that a keyboard layout name exists and return its mapping.

    Args:
        keyboard: The layout name to look up.
        layouts: Object with layout names as attributes (e.g., KEYNEIGHBORS).
        context: Description for error messages.

    Returns:
        The keyboard neighbor mapping.

    Raises:
        RuntimeError: If the layout name is not found.
    """
    layout = getattr(layouts, keyboard, None)
    if layout is None:
        raise RuntimeError(f"Unknown {context} '{keyboard}'")
    return cast(Mapping[str, Sequence[str]], layout)


def get_keyboard_layout_or_default(
    keyboard: str,
    layouts: object,
    *,
    default: Mapping[str, Sequence[str]] | None = None,
) -> Mapping[str, Sequence[str]] | None:
    """Look up a keyboard layout, returning None or default if not found.

    Args:
        keyboard: The layout name to look up.
        layouts: Object with layout names as attributes.
        default: Value to return if layout not found.

    Returns:
        The keyboard neighbor mapping, or default if not found.
    """
    layout = getattr(layouts, keyboard, None)
    if layout is None:
        return default
    return cast(Mapping[str, Sequence[str]], layout)


# ---------------------------------------------------------------------------
# Zeedub Validation
# ---------------------------------------------------------------------------


def normalize_zero_width_palette(
    characters: Sequence[str] | None,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    """Normalize zero-width character palette, filtering empty entries.

    Args:
        characters: User-provided character sequence, or None for default.
        default: Default character palette.

    Returns:
        Tuple of non-empty characters.
    """
    palette: Sequence[str] = tuple(characters) if characters is not None else default
    return tuple(char for char in palette if char)


# ---------------------------------------------------------------------------
# Redactyl Validation
# ---------------------------------------------------------------------------


def normalize_replacement_char(
    replacement_char: str | None,
    default: str,
) -> str:
    """Normalize redaction replacement character.

    Args:
        replacement_char: User-provided character, or None for default.
        default: Default replacement character.

    Returns:
        The replacement character as a string.
    """
    return default if replacement_char is None else str(replacement_char)


# ---------------------------------------------------------------------------
# Boolean Flag Helpers
# ---------------------------------------------------------------------------


def resolve_bool_flag(
    specific: bool | None,
    global_default: bool,
) -> bool:
    """Resolve a boolean flag with specific/global precedence.

    Args:
        specific: Specific override value, or None to use global.
        global_default: Global default when specific is None.

    Returns:
        The resolved boolean flag.
    """
    return bool(specific if specific is not None else global_default)


# ---------------------------------------------------------------------------
# Collection Helpers
# ---------------------------------------------------------------------------


def normalize_string_collection(
    value: str | Collection[str] | None,
) -> tuple[str, ...] | None:
    """Normalize a string or collection of strings to a tuple.

    Args:
        value: Single string, collection of strings, or None.

    Returns:
        Tuple of strings, or None if input is None.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    return tuple(value)


__all__ = [
    # Rate validation
    "clamp_rate",
    "clamp_rate_unit",
    "resolve_rate",
    # Mim1c
    "normalise_mim1c_classes",
    "normalise_mim1c_banned",
    # Ekkokin
    "normalise_homophone_group",
    "build_homophone_lookup",
    # Rushmore
    "normalize_rushmore_mode_item",
    "normalize_rushmore_modes",
    "resolve_rushmore_mode_rate",
    "RushmoreRateConfig",
    # Keyboard
    "validate_keyboard_layout",
    "get_keyboard_layout_or_default",
    # Zeedub
    "normalize_zero_width_palette",
    # Redactyl
    "normalize_replacement_char",
    # Flags and helpers
    "resolve_bool_flag",
    "normalize_string_collection",
]

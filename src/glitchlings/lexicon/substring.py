"""Dictionary-driven substring substitution utilities."""

from __future__ import annotations

import math
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Callable

ReplacementDictionary = Mapping[str, Sequence[str]]
ReplacementTransform = Callable[[re.Match[str], str], str | None]


def apply_casing(template: str, candidate: str) -> str:
    """Return ``candidate`` adjusted to mirror the casing pattern of ``template``."""

    if not candidate:
        return candidate
    if template.isupper():
        return candidate.upper()
    if template.islower():
        return candidate.lower()
    if template[:1].isupper() and template[1:].islower():
        return candidate.capitalize()

    characters: list[str] = []
    for repl_char, template_char in zip(candidate, template, strict=False):
        if template_char.isupper():
            characters.append(repl_char.upper())
        elif template_char.islower():
            characters.append(repl_char.lower())
        else:
            characters.append(repl_char)

    if len(candidate) > len(characters):
        characters.extend(candidate[len(characters) :])
    return "".join(characters)


def compile_replacement_pattern(
    keys: Iterable[str],
    *,
    prefix: str = r"\b",
    suffix: str = r"\b",
    suffix_pattern: str = "",
    case_sensitive: bool = False,
) -> re.Pattern[str]:
    """Return a compiled pattern matching entries from ``keys`` with a ``key`` group."""

    normalized = [re.escape(key) for key in sorted(set(keys), key=len, reverse=True) if key]
    if not normalized:
        raise ValueError("replacement dictionary must define at least one key")
    joined = "|".join(normalized)
    pattern = f"{prefix}(?P<key>{joined}){suffix_pattern}{suffix}"
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern, flags)


def substitute_from_dictionary(
    text: str,
    dictionary: ReplacementDictionary,
    *,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    pattern: re.Pattern[str] | None = None,
    case_sensitive: bool = False,
    preserve_case: bool = True,
    transform: ReplacementTransform | None = None,
) -> str:
    """Replace substrings in ``text`` using a dictionary-driven sampler."""

    if not text:
        return text

    effective_rate = 1.0 if rate is None else rate
    if math.isnan(effective_rate):
        return text

    clamped_rate = max(0.0, min(1.0, effective_rate))
    if clamped_rate <= 0.0:
        return text

    normalized: dict[str, tuple[str, ...]] = {}
    for key, values in dictionary.items():
        options = tuple(value for value in values if value) or None
        if not options:
            continue
        normalized_key = key if case_sensitive else key.lower()
        normalized[normalized_key] = options

    if not normalized:
        return text

    compiled = pattern or compile_replacement_pattern(
        normalized.keys(), case_sensitive=case_sensitive
    )

    matches = list(compiled.finditer(text))
    if not matches:
        return text

    active_rng = rng if rng is not None else random.Random(seed)

    replacements: dict[int, str] = {}
    for idx, match in enumerate(matches):
        key_fragment = match.group("key")
        if key_fragment is None:
            continue
        lookup_key = key_fragment if case_sensitive else key_fragment.lower()
        options = normalized.get(lookup_key, None)
        if not options:
            continue
        if clamped_rate < 1.0 and active_rng.random() >= clamped_rate:
            continue

        replacement: str = active_rng.choice(options)
        adjusted: str | None = (
            apply_casing(key_fragment, replacement) if preserve_case else replacement
        )
        if adjusted is None:
            continue
        if transform is not None and adjusted is not None:
            adjusted = transform(match, adjusted)
            if adjusted is None:
                continue

        replacements[idx] = adjusted

    if not replacements:
        return text

    pieces: list[str] = []
    last_end = 0
    for idx, match in enumerate(matches):
        start, end = match.span()
        pieces.append(text[last_end:start])
        if idx in replacements:
            pieces.append(replacements[idx])
        else:
            pieces.append(match.group(0))
        last_end = end
    pieces.append(text[last_end:])
    return "".join(pieces)


__all__ = [
    "ReplacementDictionary",
    "ReplacementTransform",
    "apply_casing",
    "compile_replacement_pattern",
    "substitute_from_dictionary",
]

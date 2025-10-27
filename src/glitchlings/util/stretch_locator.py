"""Identify where expressive stretches should occur within a token."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

VOWELS = set("aeiouyAEIOUY")
SONORANTS = set("rlmnwyhRLMNWYH")
SIBILANTS = set("sSzZxXcCjJ") | {"sh", "Sh", "sH", "SH", "zh", "Zh"}
DIGRAPHS = {
    "aa",
    "ae",
    "ai",
    "ay",
    "ee",
    "ei",
    "ey",
    "ie",
    "io",
    "oa",
    "oe",
    "oi",
    "oo",
    "ou",
    "ua",
    "ue",
    "ui",
    "ya",
    "yo",
    "yu",
}


@dataclass(slots=True)
class StretchSite:
    """Location of a stretchable grapheme."""

    start: int
    end: int
    category: str

    def unit(self, token: str) -> str:
        return token[self.start : self.end]


def _alpha_indices(token: str) -> list[int]:
    return [idx for idx, char in enumerate(token) if char.isalpha()]


def _vowel_clusters(token: str, indices: Iterable[int]) -> list[tuple[int, int]]:
    clusters: list[tuple[int, int]] = []
    start: int | None = None
    prev_idx: int | None = None
    for idx in indices:
        char = token[idx]
        if char in VOWELS:
            if start is None:
                start = idx
            elif prev_idx is not None and idx != prev_idx + 1:
                clusters.append((start, prev_idx + 1))
                start = idx
        else:
            if start is not None:
                clusters.append((start, idx))
                start = None
        prev_idx = idx
    if start is not None and prev_idx is not None:
        clusters.append((start, prev_idx + 1))
    return clusters


def find_stretch_site(token: str) -> StretchSite | None:
    """Return the most suitable stretch site for ``token``."""

    alpha_indices = _alpha_indices(token)
    if not alpha_indices:
        return None

    lower = token.lower()
    clusters = _vowel_clusters(lower, alpha_indices)
    candidates: list[tuple[int, StretchSite]] = []

    # Sibilant/sonorant coda extension (yes -> yesss, hmm -> hmmmm)
    last_idx = alpha_indices[-1]
    last_char = lower[last_idx]
    if len(alpha_indices) >= 2:
        prev_char = lower[alpha_indices[-2]]
    else:
        prev_char = ""
    has_multi_vowel = any(
        (end - start >= 2) and not (lower[start] == 'y' and start == 0)
        for start, end in clusters
    )
    if last_char in {"s", "z"} and prev_char in VOWELS and not has_multi_vowel:
        candidates.append((5, StretchSite(last_idx, last_idx + 1, "coda")))
    elif last_char in SONORANTS and prev_char in VOWELS and not has_multi_vowel:
        candidates.append((4, StretchSite(last_idx, last_idx + 1, "coda")))
    elif not clusters:
        candidates.append((2, StretchSite(last_idx, last_idx + 1, "consonant")))

    # CVCe pattern (cute -> cuuute)
    if lower.endswith("e") and len(alpha_indices) >= 3:
        final_letter = alpha_indices[-1]
        if token[final_letter].lower() == "e":
            c_idx = alpha_indices[-2]
            v_idx = alpha_indices[-3]
            if token[c_idx].lower() not in VOWELS and token[v_idx].lower() in VOWELS:
                candidates.append((4, StretchSite(v_idx, v_idx + 1, "cvce")))

    for cluster in clusters:
        start, end = cluster
        substring = lower[start:end]
        category = "vowel"
        if any(substring[i : i + 2] in DIGRAPHS for i in range(max(0, len(substring) - 1))):
            category = "digraph"
        priority = 3 if cluster == clusters[-1] else 2
        candidates.append((priority, StretchSite(start, end, category)))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1].end - item[1].start, -item[1].start))
    return candidates[-1][1]


def apply_stretch(token: str, site: StretchSite, repeats: int) -> str:
    """Return ``token`` with ``repeats`` extra copies of the grapheme at ``site``."""

    if repeats <= 0:
        return token
    chars = list(token)
    stretched: list[str] = []
    for idx, char in enumerate(chars):
        stretched.append(char)
        if site.start <= idx < site.end:
            stretched.append(char * repeats)
    return "".join(stretched)


__all__ = ["StretchSite", "find_stretch_site", "apply_stretch"]

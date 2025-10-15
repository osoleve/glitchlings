from __future__ import annotations

from typing import Mapping, Sequence

from glitchlings.types_rust import (
    GlitchDescriptor,
    PlanInputLike,
    RngLike,
)

def reduplicate_words(
    text: str,
    reduplication_rate: float,
    unweighted: bool,
    rng: RngLike,
) -> str: ...
def delete_random_words(
    text: str,
    max_deletion_rate: float,
    unweighted: bool,
    rng: RngLike,
) -> str: ...
def swap_adjacent_words(
    text: str,
    swap_rate: float,
    rng: RngLike,
) -> str: ...
def ocr_artifacts(text: str, error_rate: float, rng: RngLike) -> str: ...
def redact_words(
    text: str,
    replacement_char: str,
    redaction_rate: float,
    merge_adjacent: bool,
    unweighted: bool,
    rng: RngLike,
) -> str: ...
def plan_glitchlings(
    glitchlings: Sequence[PlanInputLike],
    master_seed: int,
) -> list[tuple[int, int]]: ...
def compose_glitchlings(
    text: str,
    descriptors: Sequence[GlitchDescriptor],
    master_seed: int,
) -> str: ...
def fatfinger(
    text: str,
    max_change_rate: float,
    layout: Mapping[str, Sequence[str]],
    rng: RngLike,
) -> str: ...
def inject_zero_widths(
    text: str,
    rate: float,
    characters: Sequence[str],
    rng: RngLike,
) -> str: ...

"""Adapter helpers shared across Python and DLC integrations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..zoo import Gaggle, Glitchling, summon
from .transcripts import TranscriptTarget


def coerce_gaggle(
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    *,
    seed: int,
    apply_seed_to_existing: bool = False,
    transcript_target: TranscriptTarget | None = None,
) -> Gaggle:
    """Return a :class:`Gaggle` built from any supported glitchling specifier.

    Args:
        glitchlings: A single Glitchling, Gaggle, string specification, or iterable
            of glitchlings/specs.
        seed: Seed to use when constructing a new Gaggle from the input.
        apply_seed_to_existing: When True, also apply the seed to an existing
            Gaggle instance. When False (default), existing Gaggles keep their
            current seed.
        transcript_target: Which transcript turns to corrupt. When None (default),
            uses the Gaggle default ("last"). Accepts:
            - "last": corrupt only the last turn (default)
            - "all": corrupt all turns
            - "assistant": corrupt only assistant turns
            - "user": corrupt only user turns
            - int: corrupt a specific index (negative indexing supported)
            - Sequence[int]: corrupt specific indices
    """
    if isinstance(glitchlings, Gaggle):
        if apply_seed_to_existing:
            glitchlings.seed = seed
            glitchlings.sort_glitchlings()
        if transcript_target is not None:
            glitchlings.transcript_target = transcript_target
        return glitchlings

    if isinstance(glitchlings, (Glitchling, str)):
        resolved: Iterable[Any] = [glitchlings]
    else:
        resolved = glitchlings

    # Validate entries before passing to summon to give better error messages
    resolved_list = list(resolved)
    for index, entry in enumerate(resolved_list):
        if not isinstance(entry, (str, Glitchling)):
            raise TypeError(
                f"glitchlings sequence entries must be Glitchling instances "
                f"or string specifications (index {index})"
            )

    gaggle = summon(resolved_list, seed=seed)
    if transcript_target is not None:
        gaggle.transcript_target = transcript_target
    return gaggle


__all__ = ["coerce_gaggle"]

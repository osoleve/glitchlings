"""Adapter helpers shared across Python and DLC integrations."""

from __future__ import annotations

from collections.abc import Iterable

from ..zoo import Gaggle, Glitchling, summon


def coerce_gaggle(
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    *,
    seed: int,
) -> Gaggle:
    """Return a :class:`Gaggle` built from any supported glitchling specifier."""

    if isinstance(glitchlings, Gaggle):
        return glitchlings

    if isinstance(glitchlings, (Glitchling, str)):
        resolved: Iterable[str | Glitchling] = [glitchlings]
    else:
        resolved = glitchlings

    return summon(list(resolved), seed=seed)


__all__ = ["coerce_gaggle"]

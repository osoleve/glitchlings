from .typogre import typogre
from .mim1c import mim1c
from .jargoyle import jargoyle
from .reduple import reduple
from .rushmore import rushmore
from .redactyl import redactyl
from .core import Glitchling, Gaggle

__all__ = [
    "typogre",
    "mim1c",
    "jargoyle",
    "reduple",
    "rushmore",
    "redactyl",
    "Glitchling",
    "Gaggle",
    "summon",
]


def summon(glitchlings: list[str | Glitchling], seed: int = 151) -> Gaggle:
    """Summon glitchlings by name (using defaults) or instance (to change parameters)."""
    available = {
        g.name.lower(): g
        for g in [typogre, mim1c, jargoyle, reduple, rushmore, redactyl]
    }
    summoned = []
    for entry in glitchlings:
        if isinstance(entry, Glitchling):
            summoned.append(entry)
            continue

        g = available.get(entry.lower())
        if g:
            summoned.append(g)
        else:
            raise ValueError(f"Glitchling '{entry}' not found.")

    return Gaggle(summoned, seed=seed)

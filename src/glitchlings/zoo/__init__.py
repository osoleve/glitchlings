from .typogre import Typogre, typogre
from .mim1c import Mim1c, mim1c
from .jargoyle import Jargoyle, jargoyle
from .reduple import Reduple, reduple
from .rushmore import Rushmore, rushmore
from .redactyl import Redactyl, redactyl
from .scannequin import Scannequin, scannequin
from .core import Glitchling, Gaggle

__all__ = [
    "Typogre",
    "typogre",
    "Mim1c",
    "mim1c",
    "Jargoyle",
    "jargoyle",
    "Reduple",
    "reduple",
    "Rushmore",
    "rushmore",
    "Redactyl",
    "redactyl",
    "Scannequin",
    "scannequin",
    "Glitchling",
    "Gaggle",
    "summon",
]


def summon(glitchlings: list[str | Glitchling], seed: int = 151) -> Gaggle:
    """Summon glitchlings by name (using defaults) or instance (to change parameters)."""
    available = {
        g.name.lower(): g
        for g in [
            typogre,
            mim1c,
            jargoyle,
            reduple,
            rushmore,
            redactyl,
            scannequin,
        ]
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

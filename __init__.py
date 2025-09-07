from zoo import (
    typogre,
    mim1c,
    jargoyle,
    redactyl,
    reduple,
    rushmore,
    Glitchling,
    Gaggle,
)
from util import SAMPLE_TEXT

__all__ = [
    "typogre",
    "mim1c",
    "jargoyle",
    "reduple",
    "rushmore",
    "redactyl",
    "summon",
    "Glitchling",
    "Gaggle",
    "SAMPLE_TEXT",
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
            entry.reset_rng(seed)
            summoned.append(entry)
            continue

        g = available.get(entry.lower())
        if g:
            g.set_param("seed", seed)
            summoned.append(g)
        else:
            raise ValueError(f"Glitchling '{entry}' not found.")

    return Gaggle(summoned)


if __name__ == "__main__":
    # Example usage

    redactyl.set_param("redaction_rate", 0.5)
    jargoyle.set_param("replacement_rate", 0.25)

    gaggle = summon(["reduple", "mim1c", "typogre", jargoyle, "rushmore", redactyl])
    corrupted = gaggle(SAMPLE_TEXT)
    # print(SAMPLE_TEXT, end="\n\n")
    # print(gaggle.pretty_diff(SAMPLE_TEXT), end="\n\n")
    print(corrupted)

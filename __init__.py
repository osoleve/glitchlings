from zoo import typogre, mim1c, jargoyle, reduple, rushmore, Glitchling, Horde
from util import SAMPLE_TEXT

__all__ = ["typogre", "mim1c", "jargoyle", "reduple", "rushmore"]


def summon(glitchlings: list[str]) -> Horde:
    """Summon glitchlings by name."""
    available = {
        g.name.lower(): g for g in [typogre, mim1c, jargoyle, reduple, rushmore]
    }
    summoned = []
    for name in glitchlings:
        g = available.get(name.lower())
        if g:
            summoned.append(g)
        else:
            raise ValueError(f"Glitchling '{name}' not found.")

    return Horde(summoned)


if __name__ == "__main__":
    horde = summon(["reduple", "mim1c", "typogre", "rushmore"])
    corrupted = horde(SAMPLE_TEXT)
    print(SAMPLE_TEXT, end="\n\n")
    print(horde.pretty_diff(SAMPLE_TEXT), end="\n\n")
    print(corrupted)

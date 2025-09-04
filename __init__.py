from zoo import typogre, mim1c, jargoyle, reduple, rushmore, Glitchling, Gaggle
from util import SAMPLE_TEXT

__all__ = ["typogre", "mim1c", "jargoyle", "reduple", "rushmore", "summon", "Glitchling", "Gaggle", "SAMPLE_TEXT"]


def summon(glitchlings: list[str]) -> Gaggle:
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

    return Gaggle(summoned)


if __name__ == "__main__":
    gaggle = summon(["reduple", "mim1c", "typogre", "jargoyle", "rushmore"])
    corrupted = gaggle(SAMPLE_TEXT)
    print(SAMPLE_TEXT, end="\n\n")
    print(gaggle.pretty_diff(SAMPLE_TEXT), end="\n\n")
    print(corrupted)

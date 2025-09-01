from .core import Glitchling
import random
from confusable_homoglyphs import confusables


def swap_homoglyphs(
    text: str, max_replacement_rate: float = 0.02, seed: int = 151
) -> str:
    """Corrupt the text by replacing characters with their homoglyphs."""
    random.seed(seed)
    nonspace_chars = [char for char in text if not char.isspace()]
    confusable_chars = [
        char for char in nonspace_chars if char in confusables.confusables_data
    ]
    max_replacements = int(len(text) * max_replacement_rate)
    choices = random.choices(
        confusable_chars,
        k=min(random.randint(1, max_replacements), len(confusable_chars)),
    )
    for char in choices:
        text = text.replace(
            char, random.choice(confusables.confusables_data[char])["c"], 1
        )
    return text


mim1c = Glitchling(name="Mim1c", corruption_function=swap_homoglyphs)
mim1c.img = r"""         ___________
        / /       \ \
       / /         \ \
      | |___________| |
      |  ___________  |
      | |           | |
      | |           | |
      | |     O     | |
      | |           | |
      | |___________| |
      \_______________/
"""

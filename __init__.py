import random
from confusable_homoglyphs import confusables
import typo


class Glitchling:
    def __init__(self, name: str, corruption_function: callable):
        self.name = name
        self.corruption_function = corruption_function

    def corrupt(self, text: str, *args, **kwargs) -> str:
        return self.corruption_function(text, *args, **kwargs)

    def __call__(self, text: str, *args, **kwds) -> str:
        return self.corrupt(text, *args, **kwds)

    def __repr__(self) -> str:
        return rf"""
      ____
     /___/\_
    _\   \/_/\__
  __\       \/_/\
  \   __    __ \ \
 __\  \_\   \_\ \ \   __
/_/\\   __   __  \ \_/_/\
\_\/_\__\/\__\/\__\/_\_\/
   \_\/_/\       /_\_\/
      \_\/       \_\/
      
      {self.name}
"""


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


def fatfinger(
    text: str,
    max_change_rate: float = 0.02,
    preserve_first: bool = True,
    preserve_last: bool = True,
    seed: int = 151,
) -> str:
    """Simulate a 'fat finger' typing error by randomly duplicating/dropping/adding/swapping characters."""
    random.seed(seed)
    max_changes = int(len(text) * max_change_rate)
    new_text = typo.StrErrer(text, seed=seed)
    for _ in range(max_changes):
        action = random.choice(
            [
                "char_swap",
                "missing_char",
                "extra_char",
                "nearby_char",
                "skipped_space",
                "unichar",
                "repeated_char",
                "random_space",
            ]
        )
        kwargs = {}
        if action in ["char_swap", "missing_char", "extra_char", "nearby_char"]:
            kwargs = {"preservefirst": preserve_first, "preservelast": preserve_last}
        new_text = new_text.__getattribute__(action)(**kwargs)
    return new_text.result


doppeltexter = Glitchling(name="Doppeltexter", corruption_function=swap_homoglyphs)
typogre = Glitchling(name="Typogre", corruption_function=fatfinger)

if __name__ == "__main__":
    # Example usage
    text = "Hello, world!"
    print(f"{'Original text: ':>31}{text}")
    random.seed(42)
    print(f"{'Corrupted text (Typogre): ':>31}{typogre(text, 0.5)}")
    random.seed(42)
    print(f"{'Corrupted text (Both:D.T): ':>31}{doppeltexter(typogre(text, 0.5), 0.5)}")
    print(f"{'Corrupted text (Both:T.D): ':>31}{typogre(doppeltexter(text, 0.5), 0.5)}")

    print(doppeltexter)
    print(f"{doppeltexter(text, 0.5)}")
    print()

    print(typogre)
    print(f"{typogre(text, 0.5)}")
    print()

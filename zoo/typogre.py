from .core import Glitchling, TextLevel
import random
import typo


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


typogre = Glitchling(
    name="Typogre", corruption_function=fatfinger, level=TextLevel.CHARACTER
)

typogre.img = r"""          ,      ,
         /|      |\
        /  '.  .'  \
       |    ò__ó    |
       |     U     |
       /   \_w_/   \
      /_____________\
     /               \
    /     /     \     \   .--.
   |     |       |     | (O%%O)
   |     |       |     | 8%%%%%8
   \     |       |     / (%%O%%)
    \    |       |    /   |  |
     '._.'`--.__.--'`._(  '--'
      /`-.________.-`\
     /   /        \   \
    |   |          |   |
    |   |          |   |
    /  /            \  \
   (__/              \__)"""

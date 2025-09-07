import random
import re
from .core import Glitchling, AttackWave


def delete_random_words(
    text: str,
    max_deletion_rate: float = 0.01,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """
    Delete random words from the input text.

    Args:
        text (str): The input text.
        max_deletion_rate (float): The maximum proportion of words to delete (default: 0.1, 10%).
        seed (int): The random seed for reproducibility (default: 151).

    Returns:
        str: The text with random words deleted.
    """
    if rng is None:
        rng = random.Random(seed)

    # Preserve exact spacing and punctuation by using regex
    tokens = re.split(r"(\s+)", text)  # Split but keep separators

    for i in range(
        2, len(tokens), 2
    ):  # Every other token is a word, but skip the first word
        if i >= len(tokens):
            break

        word = tokens[i]
        if not word or word.isspace():  # Skip empty or whitespace
            continue

        # Only consider actual words for deletion
    if rng.random() < max_deletion_rate:
        # Check if word has trailing punctuation
        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        if match:
            prefix, _, suffix = match.groups()
            tokens[i] = f"{prefix.strip()}{suffix.strip()}"
        else:
            tokens[i] = ""

    text = "".join(tokens)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    return text


rushmore = Glitchling("rushmore", delete_random_words, scope=AttackWave.WORD)
rushmore.img = r"""
                                            ,;,.
                    ,;,.                   /`_`'\                   ,;,.
                   /`_`'\                 | - - |                 /`_`'\
                  | - - |                 { \_/ }                 | - - |
                  { \_/ }                   `~`                   { \_/ }
                    `~`                                             `~`
          ,         `\                                          /`         ,
         / \          ~.                                      .~          / \
        |o.o|           ~.                                  .~           |o.o|
        <--->             \                               /             <--->
         ` `               \                             /               ` `
         /                  ~.                         .~                  \
        /                     ~.                     .~                     \
       `~.                      `--'             '--`                      .~`
          `~.                /`--.__.           .__.--'`\                .~`
             `~.            /  ########         ########  \            .~`
                `~.        |  ##########       ##########  |        .~`
                   `~.      \  ########         ########  /      .~`
                      `~.    `--..__.'    /`_`'\   `..__..--'    .~`
                         `~.  /        \   | - - |   /        \  .~`
                            `|          |  { \_/ }  |          |`
                             |          |    `~`    |          |
                           ,--|        |--.  |   .--|        |--.
                          /   |        |   \/ \ /   |        |   \
                         '---'        '---' `~`'---'        '---'
"""

import re
import random
from .core import Glitchling, AttackWave


def reduplicate_words(
    text: str,
    reduplication_rate: float = 0.05,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    if rng is None:
        rng = random.Random(seed)

    # Preserve exact spacing and punctuation by using regex
    tokens = re.split(r"(\s+)", text)  # Split but keep separators

    for i in range(0, len(tokens), 2):  # Every other token is a word
        if i >= len(tokens):
            break

        word = tokens[i]
        if not word or word.isspace():  # Skip empty or whitespace
            continue

        # Only consider actual words for reduplication
    if rng.random() < reduplication_rate:
        # Check if word has trailing punctuation
        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        if match:
            prefix, core, suffix = match.groups()
            # Reduplicate with a space: "word" -> "word word"
            tokens[i] = f"{prefix}{core} {core}{suffix}"
        else:
            tokens[i] = f"{word} {word}"

    return "".join(tokens)


reduple = Glitchling(
    name="Reduple", corruption_function=reduplicate_words, scope=AttackWave.WORD
)
reduple.img = r"""                                            ,;,.
                    ,;,.                   /`_`'\                   ,;,.
                   /`_`'\                 | o o |                 /`_`'\
                  | o o |                 { \_/ }                 | o o |
                  { \_/ }                   `~`                   { \_/ }
                    `~`                      |                      `~`
          ,         `\                    /                      /`         ,
         / \          ~.                 /                      .~          / \
        |o.o|           ~.              /                      .~           |o.o|
        <VVV>             \            /                      /             <VVV>
         `v`               \          /                      /               `v`
         /                  ~.       /                      .~                  \
        /                     ~.    /                      .~                     \
       `~.                      `--'----------------------'--`                      .~`
          `~.                /`--.__.--'`\                .~`
             `~.            /  SSSSSSSS  \            .~`
                `~.        |  SSSSSSSSSS  |        .~`
                   `~.      \  SSSSSSSS  /      .~`
                      `~.    `--..__..--'    .~`
                         `~.  /        \  .~`
                            `|          |`
                             |          |
                           ,--|        |--.
                          /   |        |   \
                         '---'        '---'
"""

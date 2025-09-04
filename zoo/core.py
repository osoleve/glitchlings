from enum import IntEnum, auto
from typing import Any, Callable
from util import string_diffs

import functools as ft


# Text levels for glitchlings, to enforce a sort order
# Work from highest level down, because e.g.
# duplicating a word then adding a typo is potentially different than
# adding a typo then duplicating a word
class TextLevel(IntEnum):
    DOCUMENT = auto()
    PARAGRAPH = auto()
    SENTENCE = auto()
    WORD = auto()
    CHARACTER = auto()


class Glitchling:
    def __init__(
        self,
        name: str,
        corruption_function: Callable,
        level: TextLevel,
        *args,
        **kwargs,
    ):
        self.name: str = name
        self.corruption_function: Callable[..., str] = corruption_function
        self.img: str = ""
        self.translations: dict[str, str] = {}
        self.kwargs: dict[str, Any] = kwargs
        self.args: tuple[Any] = args
        self.level: TextLevel = level

    def __corrupt(self, text, *args, **kwargs):
        corrupted = self.corruption_function(text, *args, **kwargs)
        self.translations[text] = corrupted
        return corrupted

    def corrupt(self, text: str, *args, **kwargs) -> str:
        if (not self.args) and args:
            self.args = args
        if (not self.kwargs) and kwargs:
            self.kwargs = kwargs

        return self.__corrupt(text, *args, **kwargs)

    def pretty_diff(self, text_in):
        text_out = self.translations[text_in]
        diff = string_diffs(text_in, text_out)
        return diff

    def __call__(self, text: str, *args, **kwds) -> str:
        return self.corrupt(text, *args, **kwds)

    def __repr__(self) -> str:
        return f"""{self.name} says {self.corrupt("Hello, world!", 1.0)}"""

    def get_translations(self) -> dict:
        return self.translations


class Horde(Glitchling):
    def __init__(self, glitchlings: list[Glitchling] = [], seed=151):
        self.glitchlings = {level: [] for level in TextLevel}
        for g in glitchlings:
            self.glitchlings[g.level].append(g)
        print(self.glitchlings)
        self.sort_glitchlings()
        print(self.glitchlings)
        super().__init__("Horde", self.corrupt, TextLevel.DOCUMENT)

    def sort_glitchlings(self):
        self.apply_order = [
            g
            for _, glitchlings in sorted(self.glitchlings.items())
            for g in glitchlings
        ]

    def corrupt(self, text: str, *args, **kwargs) -> str:
        corrupted = text
        for glitchling in self.apply_order:
            corrupted = glitchling.corrupt(corrupted, *args, **kwargs)
        self.translations[text] = corrupted
        return corrupted

    def pretty_diff(self, text_in):
        result = []
        for glitchling in self.apply_order:
            diff = glitchling.pretty_diff(text_in)
            result.append(f"{glitchling.name}:\n{diff}\n")
            text_in = glitchling.get_translations().get(text_in, text_in)

        return "\n".join(result)

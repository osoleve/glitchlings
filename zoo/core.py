import difflib


class Glitchling:
    def __init__(self, name: str, corruption_function: callable):
        self.name = name
        self.corruption_function = corruption_function
        self.img = ""
        self.translations = {}
        self.edits = {}

    def corrupt(self, text: str, *args, **kwargs) -> str:
        corrupted = self.corruption_function(text, *args, **kwargs)
        self.translations[(text, args, frozenset(kwargs.items()))] = corrupted
        self.edits[(text, args, frozenset(kwargs.items()))] = list(
            difflib.ndiff(text.splitlines(), corrupted.splitlines())
        )
        return corrupted

    def __call__(self, text: str, *args, **kwds) -> str:
        return self.corrupt(text, *args, **kwds)

    def __repr__(self) -> str:
        return f"""\
{self.img}
{self.name} says {self.corrupt("Hello, world!", 1)}
"""

    def get_translations(self) -> dict:
        return self.translations

    def get_edits(self) -> dict:
        return self.edits

    def review(self, text: str, *args, **kwargs) -> dict:
        return {
            "translations": self.get_translations()[
                text, args, frozenset(kwargs.items())
            ],
            "edits": self.get_edits()[text, args, frozenset(kwargs.items())],
        }

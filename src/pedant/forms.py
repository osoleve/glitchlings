"""Concrete pedant evolutions and their moves."""

from __future__ import annotations

import re

from .core import Pedant


def _match_casing(source: str, replacement: str) -> str:
    """Return ``replacement`` adjusted to match ``source`` casing."""

    if source.isupper():
        return replacement.upper()
    if source.islower():
        return replacement.lower()
    if source.istitle():
        return replacement.capitalize()
    return replacement


class Whomst(Pedant):
    name = "Whomst"
    type = "Ghost"
    flavor = "Insists upon objective-case precision."

    def move(self, text: str) -> str:
        pattern = re.compile(r"\bwho\b", re.IGNORECASE)

        def repl(match: re.Match[str]) -> str:
            word = match.group(0)
            if word.isupper():
                return "WHOM"
            if word[0].isupper():
                return "Whom"
            return "whom"

        return pattern.sub(repl, text)


class Fewerling(Pedant):
    name = "Fewerling"
    type = "Fairy"
    flavor = "Counts only countable nouns."

    _pattern = re.compile(
        r"(?P<prefix>\b(?:\d[\d,]*|many|few)\b[^.?!]*?\b)"
        r"(?P<or>or)"
        r"(?P<space>\s+)"
        r"(?P<less>less)\b",
        re.IGNORECASE,
    )

    def move(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            prefix = match.group("prefix")
            or_word = match.group("or")
            space = match.group("space")
            less_word = match.group("less")
            fewer = _match_casing(less_word, "fewer")
            return f"{prefix}{or_word}{space}{fewer}"

        return self._pattern.sub(repl, text)


class Aetherial(Pedant):
    name = "Aetherial"
    type = "Psychic"
    flavor = "Resurrects archaic ligatures and diacritics."

    _cooperate_pattern = re.compile(r"cooperate", re.IGNORECASE)
    _coordinate_pattern = re.compile(r"coordinate", re.IGNORECASE)
    _aether_pattern = re.compile(r"ae")

    def move(self, text: str) -> str:
        text = self._cooperate_pattern.sub(self._cooperate_replacement, text)
        text = self._coordinate_pattern.sub(lambda m: self._coordinate_replacement(m, text), text)
        text = self._apply_ligatures(text)
        return text

    @staticmethod
    def _cooperate_replacement(match: re.Match[str]) -> str:
        word = match.group(0)
        if word.isupper():
            return "COÖPERATE"
        if word[0].isupper():
            return "Coöperate"
        return "coöperate"

    def _coordinate_replacement(self, match: re.Match[str], text: str) -> str:
        rng = self.get_rng("coordinate", text, match.start())
        word = match.group(0)
        if rng.random() < 0.5:
            return self._apply_diaeresis(word)
        return word

    @staticmethod
    def _apply_diaeresis(word: str) -> str:
        if word.isupper():
            return word.replace("OO", "OÖ", 1)
        if word[0].isupper():
            return word.replace("oo", "oö", 1).replace("Oo", "Öo", 1)
        return word.replace("oo", "oö", 1)

    def _apply_ligatures(self, text: str) -> str:
        matches = [m.start() for m in self._aether_pattern.finditer(text)]
        if not matches:
            return text

        rng = self.get_rng("aetherial", text)
        chosen = {pos for pos in matches if rng.random() < 0.6}
        if not chosen:
            chosen = {matches[rng.randrange(len(matches))]}

        result: list[str] = []
        index = 0
        while index < len(text):
            if index in chosen:
                digraph = text[index : index + 2]
                if digraph.isupper():
                    result.append("Æ")
                elif digraph[0].isupper():
                    result.append("Æ")
                else:
                    result.append("æ")
                index += 2
            else:
                result.append(text[index])
                index += 1
        return "".join(result)


class Subjunic(Pedant):
    name = "Subjunic"
    type = "Psychic"
    flavor = "Corrects the subjunctive wherever it can."

    _pattern = re.compile(r"(?P<prefix>\bif\s+i\s+)(?P<verb>was)\b", re.IGNORECASE)

    def move(self, text: str) -> str:
        return self._pattern.sub(
            lambda m: f"{m.group('prefix')}{_match_casing(m.group('verb'), 'were')}", text
        )


class SerialComma(Pedant):
    name = "SerialComma"
    type = "Steel"
    flavor = "Oxonian hero of the list."

    _pattern = re.compile(r"(,\s*)([^,]+)\s+and\s+([^,]+)")

    def move(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            prefix, penultimate, last = match.groups()
            if penultimate.endswith(","):
                return match.group(0)
            return f"{prefix}{penultimate}, and {last}"

        return self._pattern.sub(repl, text)


class Oxforda(Pedant):
    name = "Oxforda"
    type = "Electric"
    flavor = "Measures the world in rational units."

    _pattern = re.compile(r"\b(?P<distance>\d[\d,]*)\s+(?P<unit>mile(?:s)?)\b", re.IGNORECASE)

    def move(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            raw_distance = match.group("distance")
            miles = int(raw_distance.replace(",", ""))
            kilometres = round(miles * 1.60934)
            km_unit = "kilometre" if kilometres == 1 else "kilometres"
            km_unit = _match_casing(match.group("unit"), km_unit)
            return f"{kilometres} {km_unit}"

        return self._pattern.sub(repl, text)


class Pedagorgon(Pedant):
    name = "Pedagorgon"
    type = "Dragon"
    flavor = "The final editor, breathing blue ink."

    def move(self, text: str) -> str:
        return text.upper()


__all__ = [
    "Whomst",
    "Fewerling",
    "Aetherial",
    "Subjunic",
    "SerialComma",
    "Oxforda",
    "Pedagorgon",
]


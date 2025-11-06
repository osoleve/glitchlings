"""Pedant evolution forms delegating to the Rust-backed core."""

from __future__ import annotations

from .core import PedantEvolution
from .stones import PedantStone


class Whomst(PedantEvolution):
    stone = PedantStone.WHOM
    name = "Whomst"
    type = "Ghost"
    flavor = "Insists upon objective-case precision."


class Fewerling(PedantEvolution):
    stone = PedantStone.FEWERITE
    name = "Fewerling"
    type = "Fairy"
    flavor = "Counts only countable nouns."


class Aetheria(PedantEvolution):
    stone = PedantStone.COEURITE
    name = "Aetheria"
    type = "Psychic"
    flavor = "Resurrects archaic ligatures and diacritics."


class Apostrofae(PedantEvolution):
    stone = PedantStone.CURLITE
    name = "Apostrofae"
    type = "Fairy"
    flavor = "Curves quotes into typeset perfection."


class Subjunic(PedantEvolution):
    stone = PedantStone.SUBJUNCTITE
    name = "Subjunic"
    type = "Psychic"
    flavor = "Corrects the subjunctive wherever it can."


class Commama(PedantEvolution):
    stone = PedantStone.OXFORDIUM
    name = "Commama"
    type = "Steel"
    flavor = "Oxonian hero of the list."


class Kiloa(PedantEvolution):
    stone = PedantStone.METRICITE
    name = "Kiloa"
    type = "Electric"
    flavor = "Measures the world in rational units."


class Correctopus(PedantEvolution):
    stone = PedantStone.ORTHOGONITE
    name = "Correctopus"
    type = "Dragon"
    flavor = "The final editor, breathing blue ink."


__all__ = [
    "Whomst",
    "Fewerling",
    "Aetheria",
    "Apostrofae",
    "Subjunic",
    "Commama",
    "Kiloa",
    "Correctopus",
]

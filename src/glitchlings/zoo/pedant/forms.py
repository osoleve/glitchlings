"""Pedant evolution forms delegating to the Rust-backed core."""

from __future__ import annotations

from .core import PedantEvolution
from .stones import PedantStone


class Andi(PedantEvolution):
    stone = PedantStone.HYPERCORRECTITE
    name = "Andi"
    type = "Ghost"
    flavor = "Learned that 'me' is wrong and now overcorrects everywhere."


class Infinitoad(PedantEvolution):
    stone = PedantStone.UNSPLITTIUM
    name = "Infinitoad"
    type = "Steel"
    flavor = "To never split what was never whole."


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


class Commama(PedantEvolution):
    stone = PedantStone.OXFORDIUM
    name = "Commama"
    type = "Steel"
    flavor = "Oxonian hero of the list."


__all__ = [
    "Andi",
    "Infinitoad",
    "Aetheria",
    "Apostrofae",
    "Commama",
]

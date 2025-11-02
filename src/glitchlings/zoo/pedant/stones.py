"""Evolution stones recognised by the pedant."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Stone:
    """Descriptor for an evolution stone."""

    name: str
    type: str
    effect: str


class PedantStone(Enum):
    """Enumeration of evolution stones available to the pedant."""

    WHOM = Stone("Whom Stone", "Ghost", "Encourages object-pronoun precision.")
    FEWERITE = Stone("Fewerite", "Fairy", "Obsesses over countable quantities.")
    COEURITE = Stone("Coeurite", "Psychic", "Restores archaic ligatures to modern words.")
    SUBJUNCTITE = Stone("Subjunctite", "Psychic", "Demands contrary-to-fact phrasing.")
    OXFORDIUM = Stone("Oxfordium", "Steel", "Polishes serial comma usage.")
    ORTHOGONITE = Stone("Orthogonite", "Dragon", "Unlocks the legendary Correctopus.")
    METRICITE = Stone("Metricite", "Electric", "Compels metrication of measures.")

    @property
    def descriptor(self) -> Stone:
        """Return the metadata describing this stone."""

        return self.value

    @property
    def label(self) -> str:
        """Return the display name for this stone."""

        return self.value.name

    def __str__(self) -> str:  # pragma: no cover - convenience for reprs/CLI echo
        return self.label

    @classmethod
    def from_value(cls, value: object) -> "PedantStone":
        """Normalise ``value`` into a :class:`PedantStone` member."""

        if isinstance(value, cls):
            return value
        if isinstance(value, Stone):
            for member in cls:
                if member.value == value:
                    return member
            msg = f"Unknown pedant stone descriptor: {value!r}"
            raise ValueError(msg)

        try:
            return _STONE_BY_NAME[str(value)]
        except KeyError as exc:
            raise ValueError(f"Unknown pedant stone: {value!r}") from exc


_STONE_BY_NAME: dict[str, PedantStone] = {stone.value.name: stone for stone in PedantStone}


STONES: dict[str, Stone] = {stone.label: stone.descriptor for stone in PedantStone}


__all__ = ["Stone", "PedantStone", "STONES"]

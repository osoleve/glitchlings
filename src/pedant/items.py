"""Item definitions for pedant evolutions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Item:
    """Base class for items the pedant can hold."""

    name: str
    consumable: bool = True

    def on_evolution_attempt(self, pedant, stone_name: str) -> bool:
        """Hook invoked before an evolution attempt.

        Returning ``True`` blocks the evolution.
        """

        return False


class StyleGuide(Item):
    """Strict style guide that forbids evolution when consulted."""

    def __init__(self) -> None:
        super().__init__(name="Style Guide", consumable=True)

    def on_evolution_attempt(self, pedant, stone_name: str) -> bool:
        return True


class CopyeditBadge(Item):
    """A decorative badge that survives evolution attempts."""

    def __init__(self) -> None:
        super().__init__(name="Copyedit Badge", consumable=False)


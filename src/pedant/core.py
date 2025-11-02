"""Core classes for the pedant evolution chain."""

from __future__ import annotations

import hashlib
import random
from typing import TYPE_CHECKING, Dict, Iterable, List, Sequence, Tuple, Type

if TYPE_CHECKING:
    from .items import Item


class Pedant:
    """Base pedant capable of evolving into specialised grammar forms."""

    name: str = "Pedant"
    type: str = "Normal"
    flavor: str = "A novice grammarian waiting to evolve."

    def __init__(
        self,
        seed: int,
        *,
        root_seed: int | None = None,
        lineage: Sequence[str] | None = None,
        items: Iterable[Item] | None = None,
    ) -> None:
        self.seed = int(seed)
        self.root_seed = int(seed if root_seed is None else root_seed)
        self.lineage: Tuple[str, ...] = tuple(lineage or (self.name,))
        self.items: List[Item] = list(items or [])

    # --- Item management -------------------------------------------------
    def give_item(self, item: Item) -> None:
        """Add an item to the pedant's inventory."""

        self.items.append(item)

    # --- Randomness helpers ----------------------------------------------
    def derive_seed(self, *parts: object) -> int:
        """Derive a deterministic seed from the root seed and lineage."""

        h = hashlib.sha256()
        h.update(str(self.root_seed).encode("utf-8"))
        for stage in self.lineage:
            h.update(stage.encode("utf-8"))
        for part in parts:
            h.update(repr(part).encode("utf-8"))
        return int.from_bytes(h.digest()[:8], "big", signed=False)

    def get_rng(self, *parts: object) -> random.Random:
        """Return a deterministic RNG derived from the pedant's seed data."""

        return random.Random(self.derive_seed(*parts))

    # --- Core behaviour ---------------------------------------------------
    def evolve(self, stone_name: str) -> "Pedant":
        """Evolve the pedant using the provided stone."""

        blocked_index: int | None = None
        for index, item in enumerate(list(self.items)):
            if item.on_evolution_attempt(self, stone_name):
                blocked_index = index
                if item.consumable:
                    self.items.pop(index)
                break
        if blocked_index is not None:
            raise RuntimeError("Evolution prevented by style enforcement")

        try:
            form_cls = EVOLUTIONS[stone_name]
        except KeyError as exc:  # pragma: no cover - sanity guard
            raise KeyError(f"Unknown stone: {stone_name}") from exc

        new_seed = self.derive_seed(stone_name)
        lineage = self.lineage + (stone_name, form_cls.name)
        # Pass a shallow copy of items to avoid mutating the original inventory
        return form_cls(
            new_seed,
            root_seed=self.root_seed,
            lineage=lineage,
            items=list(self.items),
        )

    def move(self, text: str) -> str:
        """Default move leaves the text unchanged."""

        return text

    # Representation helpers
    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<{self.__class__.__name__} seed={self.seed} type={self.type}>"


EVOLUTIONS: Dict[str, Type[Pedant]] = {}


try:  # pragma: no cover - import resolution occurs at runtime
    from .forms import Aetherial, Fewerling, Oxforda, Pedagorgon, SerialComma, Subjunic, Whomst
except ImportError:  # pragma: no cover - partial imports during type checking
    # Forms are imported lazily by consumers during runtime.
    pass
else:
    EVOLUTIONS = {
        "Whom Stone": Whomst,
        "Fewerite": Fewerling,
        "Aetherite": Aetherial,
        "Subjunctite": Subjunic,
        "Oxfordium": SerialComma,
        "Orthogonite": Pedagorgon,
        "Metricite": Oxforda,
    }

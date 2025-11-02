"""Pedant glitchling integrating grammar evolutions with optional Rust acceleration."""

from __future__ import annotations

import random
from typing import Iterable, Sequence, cast

from .._rust_extensions import get_rust_operation
from ..core import AttackOrder, AttackWave, Glitchling
from .core import EVOLUTIONS, PedantBase
from .items import CopyeditBadge, Item, StyleGuide
from .stones import STONES

_PEDANT_RUST = get_rust_operation("pedant")

_ITEM_REGISTRY: dict[str, type[Item]] = {
    "Style Guide": StyleGuide,
    "Copyedit Badge": CopyeditBadge,
}


def _materialise_items(items: Sequence[str | Item] | None) -> list[Item]:
    """Return concrete `Item` instances for the provided specification."""

    if not items:
        return []

    inventory: list[Item] = []
    for entry in items:
        if isinstance(entry, Item):
            inventory.append(entry)
            continue

        name = str(entry)
        factory = _ITEM_REGISTRY.get(name)
        if factory is None:  # pragma: no cover - defensive guard
            raise ValueError(f"Unknown pedant item: {name}")
        inventory.append(factory())
    return inventory


def _serialise_items(items: Sequence[str | Item] | None) -> tuple[str, ...] | None:
    if not items:
        return None
    serialised: list[str] = []
    for entry in items:
        if isinstance(entry, Item):
            serialised.append(entry.name)
        else:
            serialised.append(str(entry))
    return tuple(serialised)


def pedant_transform(
    text: str,
    *,
    stone: str = "Aetherite",
    seed: int | None = None,
    items: Sequence[str | Item] | None = None,
    rng: random.Random | None = None,
) -> str:
    """Apply a pedant evolution to text."""

    if stone not in EVOLUTIONS:
        raise ValueError(f"Unknown pedant stone: {stone}")

    materialised_items = _materialise_items(items)

    effective_seed: int
    if seed is not None:
        effective_seed = int(seed)
    else:
        if rng is None:
            rng = random.Random()
        effective_seed = rng.randrange(2**63)

    if _PEDANT_RUST is not None:
        return cast(
            str,
            _PEDANT_RUST(
                text,
                stone=stone,
                seed=effective_seed,
                items=[item.name for item in materialised_items],
                rng=rng,
            ),
        )

    pedant = PedantBase(effective_seed, items=list(materialised_items))
    evolved = pedant.evolve(stone)
    return evolved.move(text)


def _build_pipeline_descriptor(glitch: "Pedant") -> dict[str, object] | None:
    stone = glitch.kwargs.get("stone")
    if not isinstance(stone, str):
        return None

    descriptor: dict[str, object] = {"type": "pedant", "stone": stone}
    items = glitch.kwargs.get("items")
    if items:
        descriptor["items"] = list(items)
    return descriptor


class Pedant(Glitchling):
    """Glitchling that deterministically applies pedant evolutions."""

    _param_aliases = {
        "form": "stone",
        "stone_name": "stone",
        "inventory": "items",
    }

    def __init__(
        self,
        *,
        stone: str = "Aetherite",
        items: Sequence[str | Item] | None = None,
        seed: int | None = None,
    ) -> None:
        serialised_items = _serialise_items(items)
        super().__init__(
            name="Pedant",
            corruption_function=pedant_transform,
            scope=AttackWave.WORD,
            order=AttackOrder.LATE,
            seed=seed,
            pipeline_operation=_build_pipeline_descriptor,
            stone=stone,
            items=serialised_items,
        )

    def set_param(self, key: str, value: object) -> None:
        if key in {"items", "inventory"}:
            serialised = _serialise_items(cast(Sequence[str | Item] | None, value))
            super().set_param("items", serialised)
            return
        super().set_param(key, value)


pedant = Pedant()

__all__ = [
    "PedantBase",
    "Pedant",
    "pedant",
    "pedant_transform",
    "EVOLUTIONS",
    "STONES",
    "StyleGuide",
    "CopyeditBadge",
]


"""Pedant glitchling integrating grammar evolutions with optional Rust acceleration."""

from __future__ import annotations

import random
from typing import Any, cast

from .._rust_extensions import get_rust_operation
from ..core import AttackOrder, AttackWave, Glitchling
from .core import EVOLUTIONS, PedantBase
from .stones import STONES, PedantStone

_PEDANT_RUST = get_rust_operation("pedant")


def _coerce_stone(value: Any) -> PedantStone:
    """Return a :class:`PedantStone` enum member for ``value``."""

    return PedantStone.from_value(value)


def pedant_transform(
    text: str,
    *,
    stone: PedantStone | str = PedantStone.COEURITE,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Apply a pedant evolution to text."""

    pedant_stone = _coerce_stone(stone)
    if pedant_stone not in EVOLUTIONS:
        raise ValueError(f"Unknown pedant stone: {stone!r}")

    effective_rng = rng
    if seed is not None:
        effective_seed = int(seed)
    else:
        if effective_rng is None:
            effective_rng = random.Random()
        effective_seed = effective_rng.randrange(2**63)

    if _PEDANT_RUST is not None:
        return cast(
            str,
            _PEDANT_RUST(
                text,
                stone=pedant_stone.label,
                seed=effective_seed,
                rng=effective_rng,
            ),
        )

    pedant = PedantBase(effective_seed)
    evolved = pedant.evolve(pedant_stone)
    return evolved.move(text)


def _build_pipeline_descriptor(glitch: Glitchling) -> dict[str, object] | None:
    stone_value = glitch.kwargs.get("stone")
    if stone_value is None:
        return None

    try:
        pedant_stone = _coerce_stone(stone_value)
    except ValueError:
        return None

    return {"type": "pedant", "stone": pedant_stone.label}


class Pedant(Glitchling):
    """Glitchling that deterministically applies pedant evolutions."""

    _param_aliases = {
        "form": "stone",
        "stone_name": "stone",
    }

    def __init__(
        self,
        *,
        stone: PedantStone | str = PedantStone.COEURITE,
        seed: int | None = None,
    ) -> None:
        super().__init__(
            name="Pedant",
            corruption_function=pedant_transform,
            scope=AttackWave.WORD,
            order=AttackOrder.LATE,
            seed=seed,
            pipeline_operation=_build_pipeline_descriptor,
            stone=_coerce_stone(stone),
        )
        if seed is not None:
            self.set_param("seed", int(seed))

    def set_param(self, key: str, value: object) -> None:
        if key in {"stone", "form", "stone_name"}:
            super().set_param(key, _coerce_stone(value))
            return
        super().set_param(key, value)

    def reset_rng(self, seed: int | None = None) -> None:
        super().reset_rng(seed)
        if self.seed is None:
            self.kwargs.pop("seed", None)
            return
        self.kwargs["seed"] = int(self.seed)


pedant = Pedant()

__all__ = [
    "PedantBase",
    "Pedant",
    "pedant",
    "pedant_transform",
    "EVOLUTIONS",
    "STONES",
    "PedantStone",
]

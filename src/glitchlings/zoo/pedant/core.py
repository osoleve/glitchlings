"""Core classes for the pedant evolution chain backed by the Rust pipeline."""

from __future__ import annotations

from typing import Dict, Type, cast

from glitchlings.internal.rust import get_rust_operation

from ..core import Gaggle
from .stones import PedantStone

_PEDANT_RUST = get_rust_operation("pedant")


def apply_pedant(
    text: str,
    *,
    stone: PedantStone,
    seed: int,
) -> str:
    """Apply a pedant transformation via the Rust extension."""

    return cast(
        str,
        _PEDANT_RUST(
            text,
            stone=stone.label,
            seed=int(seed),
        ),
    )


class PedantEvolution:
    """Concrete pedant form that delegates to the Rust implementation."""

    stone: PedantStone

    def __init__(
        self,
        seed: int,
        *,
        stone: PedantStone | None = None,
    ) -> None:
        resolved_stone = stone or getattr(self, "stone", None)
        if resolved_stone is None:  # pragma: no cover - defensive guard
            raise ValueError("PedantEvolution requires a PedantStone")
        self.seed = int(seed)
        self.stone = resolved_stone

    def move(self, text: str) -> str:
        result = apply_pedant(text, stone=self.stone, seed=self.seed)
        return result


class PedantBase:
    """Base pedant capable of evolving into specialised grammar forms."""

    name: str = "Pedant"
    type: str = "Normal"
    flavor: str = "A novice grammarian waiting to evolve."

    def __init__(self, seed: int, *, root_seed: int | None = None) -> None:
        self.seed = int(seed)
        self.root_seed = int(seed if root_seed is None else root_seed)

    def evolve(self, stone: PedantStone | str) -> PedantEvolution:
        pedant_stone = PedantStone.from_value(stone)
        form_cls = EVOLUTIONS.get(pedant_stone)
        if form_cls is None:  # pragma: no cover - sanity guard
            raise KeyError(f"Unknown stone: {stone}")
        derived_seed = Gaggle.derive_seed(self.root_seed, pedant_stone.label, 0)
        return form_cls(seed=int(derived_seed))

    def move(self, text: str) -> str:
        return text

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<{self.__class__.__name__} seed={self.seed} type={self.type}>"


EVOLUTIONS: Dict[PedantStone, Type[PedantEvolution]] = {}


try:  # pragma: no cover - import resolution occurs at runtime
    from .forms import (
        Aetheria,
        Apostrofae,
        Commama,
        Correctopus,
        Fewerling,
        Kiloa,
        Subjunic,
        Whomst,
    )
except ImportError:  # pragma: no cover - partial imports during type checking
    pass
else:
    EVOLUTIONS = {
        PedantStone.WHOM: Whomst,
        PedantStone.FEWERITE: Fewerling,
        PedantStone.COEURITE: Aetheria,
        PedantStone.CURLITE: Apostrofae,
        PedantStone.SUBJUNCTITE: Subjunic,
        PedantStone.OXFORDIUM: Commama,
        PedantStone.ORTHOGONITE: Correctopus,
        PedantStone.METRICITE: Kiloa,
    }


__all__ = ["PedantBase", "PedantEvolution", "EVOLUTIONS", "apply_pedant"]

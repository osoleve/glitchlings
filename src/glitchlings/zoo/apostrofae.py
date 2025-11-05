"""Smart-quote glitchling that swaps straight quotes for fancy counterparts."""

from __future__ import annotations

import random
from typing import cast

from ._rust_extensions import get_rust_operation, resolve_seed
from .core import AttackOrder, AttackWave, Gaggle, Glitchling, PipelineOperationPayload

# Load the mandatory Rust implementation
_apostrofae_rust = get_rust_operation("apostrofae")

def smart_quotes(
    text: str,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Replace straight quotes, apostrophes, and backticks with fancy pairs."""

    if not text:
        return text

    seed_value = resolve_seed(seed, rng)
    return cast(str, _apostrofae_rust(text, seed_value))


class Apostrofae(Glitchling):
    """Glitchling that swaps straight quotes for decorative Unicode pairs."""

    def __init__(self, *, seed: int | None = None) -> None:
        self._master_seed: int | None = seed
        super().__init__(
            name="Apostrofae",
            corruption_function=smart_quotes,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.NORMAL,
            seed=seed,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        return cast(PipelineOperationPayload, {"type": "apostrofae"})

    def reset_rng(self, seed: int | None = None) -> None:  # pragma: no cover - exercised indirectly
        if seed is not None:
            self._master_seed = seed
            super().reset_rng(seed)
            if self.seed is None:
                return
            derived = Gaggle.derive_seed(int(seed), self.name, 0)
            self.seed = int(derived)
            self.rng = random.Random(self.seed)
            self.kwargs["seed"] = self.seed
        else:
            super().reset_rng(None)


apostrofae = Apostrofae()


__all__ = ["Apostrofae", "apostrofae", "smart_quotes"]

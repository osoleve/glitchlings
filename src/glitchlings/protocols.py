"""Protocols for dependency inversion across submodules.

This module defines protocol classes that allow submodules to depend on
abstract interfaces rather than concrete implementations. This eliminates
circular imports and improves testability.

Design Philosophy
-----------------
The attack submodule needs to work with glitchlings but shouldn't depend
on the concrete zoo.core.Glitchling class. Instead, it depends on the
Corruptor protocol which defines the minimal interface needed.

This follows the Dependency Inversion Principle (the D in SOLID):
- High-level modules (attack) should not depend on low-level modules (zoo)
- Both should depend on abstractions (protocols)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .util.transcripts import Transcript, TranscriptTarget


@runtime_checkable
class Corruptor(Protocol):
    """Protocol for objects that can corrupt text.

    This protocol defines the minimal interface that the attack submodule
    needs from glitchlings. Any object implementing these methods can be
    used with Attack, SeedSweep, GridSearch, and TokenizerComparison.

    The zoo.core.Glitchling and zoo.core.Gaggle classes satisfy this protocol.

    Attributes:
        seed: The RNG seed for deterministic corruption.
        transcript_target: Which transcript turns to target for corruption.

    Example:
        >>> class MockCorruptor:
        ...     seed = 42
        ...     transcript_target = "last"
        ...     def corrupt(self, text): return text.upper()
        ...     def clone(self): return MockCorruptor()
        >>> attack = Attack(MockCorruptor())  # Works with protocol
    """

    seed: int | None
    transcript_target: "TranscriptTarget | None"

    def corrupt(
        self,
        text: "str | Transcript",
    ) -> "str | Transcript":
        """Apply corruption to text or transcript.

        Args:
            text: Input text string or chat transcript.

        Returns:
            Corrupted text or transcript (same type as input).
        """
        ...

    def clone(self) -> "Corruptor":
        """Create a copy of this corruptor.

        Returns:
            A new Corruptor instance with the same configuration.
        """
        ...


@runtime_checkable
class Clonable(Protocol):
    """Protocol for objects that support cloning.

    This minimal protocol is used when we only need to clone objects
    without caring about their other capabilities.
    """

    def clone(self) -> "Clonable":
        """Create a copy of this object."""
        ...


__all__ = ["Clonable", "Corruptor"]

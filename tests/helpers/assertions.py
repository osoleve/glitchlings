"""Reusable assertion helpers for common test patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from glitchlings.zoo.core import Glitchling


def assert_deterministic(glitchling: "Glitchling", text: str, seed: int) -> tuple[str, str]:
    """Assert that a glitchling produces identical output with the same seed.

    This is the primary test for verifying that a glitchling's corruption
    is deterministic when given the same seed.

    Args:
        glitchling: The glitchling instance to test
        text: Input text to corrupt
        seed: Seed value for deterministic behavior

    Returns:
        Tuple of (first_output, second_output) for additional assertions

    Raises:
        AssertionError: If outputs differ

    Example:
        >>> from glitchlings import typogre
        >>> glitch = typogre.clone()
        >>> glitch.set_param("rate", 0.05)
        >>> assert_deterministic(glitch, "test input", seed=42)
    """
    glitchling.reset_rng(seed)
    first = glitchling(text)
    glitchling.reset_rng(seed)
    second = glitchling(text)

    assert first == second, (
        f"{glitchling.name} not deterministic with seed {seed}\n"
        f"First:  {first!r}\n"
        f"Second: {second!r}"
    )

    return first, second

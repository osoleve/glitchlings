"""Jargoyle glitchling: Dictionary-based word drift.

Jargoyle swaps words with alternatives from bundled lexeme dictionaries.
Multiple dictionaries are supported:
- "colors": Color term swapping (formerly Spectroll)
- "synonyms": General synonym substitution
- "corporate": Business jargon alternatives
- "academic": Scholarly word substitutions

Two modes are available:
- "literal": First entry in each word's alternatives (deterministic mapping)
- "drift": Random selection from alternatives (probabilistic)
"""

from __future__ import annotations

from typing import Literal, cast

from glitchlings.constants import DEFAULT_JARGOYLE_RATE
from glitchlings.internal.rust_ffi import (
    jargoyle_drift_rust,
    list_lexeme_dictionaries_rust,
    resolve_seed,
)

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload

# Valid dictionary names
VALID_LEXEMES = ("colors", "synonyms", "corporate", "academic")
DEFAULT_LEXEMES = "synonyms"

# Valid modes
JargoyleMode = Literal["literal", "drift"]
VALID_MODES = ("literal", "drift")
DEFAULT_MODE: JargoyleMode = "drift"


def list_lexeme_dictionaries() -> list[str]:
    """Return the list of available lexeme dictionaries.

    Returns:
        List of dictionary names that can be used with Jargoyle.
    """
    return list_lexeme_dictionaries_rust()


def jargoyle_drift(
    text: str,
    *,
    lexemes: str = DEFAULT_LEXEMES,
    mode: JargoyleMode = DEFAULT_MODE,
    rate: float | None = None,
    seed: int | None = None,
) -> str:
    """Apply dictionary-based word drift to text.

    Args:
        text: Input text to transform.
        lexemes: Name of the dictionary to use.
        mode: "literal" for deterministic first-entry swaps,
              "drift" for random selection from alternatives.
        rate: Probability of transforming each matching word (0.0 to 1.0).
        seed: Seed for deterministic randomness (only used in "drift" mode).

    Returns:
        Text with word substitutions applied.

    Raises:
        ValueError: If lexemes or mode is invalid.
    """
    # Validate inputs
    normalized_lexemes = lexemes.lower()
    if normalized_lexemes not in VALID_LEXEMES:
        raise ValueError(f"Invalid lexemes '{lexemes}'. Must be one of: {', '.join(VALID_LEXEMES)}")

    normalized_mode = mode.lower()
    if normalized_mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}")

    effective_rate = DEFAULT_JARGOYLE_RATE if rate is None else float(rate)
    resolved_seed = resolve_seed(seed, None) if normalized_mode == "drift" else None

    return jargoyle_drift_rust(
        text,
        normalized_lexemes,
        normalized_mode,
        effective_rate,
        resolved_seed,
    )


class Jargoyle(Glitchling):
    """Glitchling that swaps words using bundled lexeme dictionaries.

    Jargoyle replaces words with alternatives from one of several dictionaries:

    - **colors**: Swap color terms (e.g., "red" → "blue"). Formerly Spectroll.
    - **synonyms**: General synonym substitution (e.g., "fast" → "rapid").
    - **corporate**: Business jargon alternatives.
    - **academic**: Scholarly word substitutions.

    Two modes are supported:

    - **literal**: Use the first (canonical) entry for each word.
    - **drift**: Randomly select from available alternatives.

    Example:
        >>> from glitchlings import Jargoyle
        >>> jargoyle = Jargoyle(lexemes="colors", mode="literal")
        >>> jargoyle("The red balloon floated away.")
        'The blue balloon floated away.'

        >>> jargoyle = Jargoyle(lexemes="synonyms", mode="drift", rate=0.5, seed=42)
        >>> jargoyle("The quick fox jumps fast.")
        'The swift fox jumps rapid.'
    """

    flavor = "Oh no... The worst person you know just bought a thesaurus..."

    def __init__(
        self,
        *,
        lexemes: str = DEFAULT_LEXEMES,
        mode: JargoyleMode = DEFAULT_MODE,
        rate: float | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize Jargoyle with the specified dictionary and mode.

        Args:
            lexemes: Name of the dictionary to use. One of:
                "colors", "synonyms", "corporate", "academic".
            mode: Transformation mode. "literal" for deterministic swaps,
                "drift" for random selection.
            rate: Probability of transforming each matching word (0.0 to 1.0).
                Defaults to 0.01.
            seed: Seed for deterministic randomness.
        """
        # Validate inputs
        normalized_lexemes = lexemes.lower()
        if normalized_lexemes not in VALID_LEXEMES:
            raise ValueError(
                f"Invalid lexemes '{lexemes}'. Must be one of: {', '.join(VALID_LEXEMES)}"
            )

        normalized_mode = mode.lower()
        if normalized_mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}")

        effective_rate = DEFAULT_JARGOYLE_RATE if rate is None else rate

        super().__init__(
            name="Jargoyle",
            corruption_function=jargoyle_drift,
            scope=AttackWave.WORD,
            order=AttackOrder.NORMAL,
            seed=seed,
            lexemes=normalized_lexemes,
            mode=normalized_mode,
            rate=effective_rate,
            # Pass seed explicitly to kwargs so corruption_function receives it
            # (seed is stored separately in base class but needed by jargoyle_drift)
        )
        # Ensure seed is in kwargs for the corruption function
        self.kwargs["seed"] = seed

    def pipeline_operation(self) -> PipelineOperationPayload:
        """Return the pipeline descriptor for the Rust backend."""
        lexemes = self.kwargs.get("lexemes", DEFAULT_LEXEMES)
        mode = self.kwargs.get("mode", DEFAULT_MODE)
        rate = self.kwargs.get("rate", DEFAULT_JARGOYLE_RATE)
        return cast(
            PipelineOperationPayload,
            {
                "type": "jargoyle",
                "lexemes": str(lexemes),
                "mode": str(mode),
                "rate": float(rate),
            },
        )


# Module-level singleton for convenience
jargoyle = Jargoyle()


__all__ = [
    "DEFAULT_LEXEMES",
    "DEFAULT_MODE",
    "Jargoyle",
    "JargoyleMode",
    "VALID_LEXEMES",
    "VALID_MODES",
    "jargoyle",
    "jargoyle_drift",
    "list_lexeme_dictionaries",
]

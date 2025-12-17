"""Jargoyle glitchling: Dictionary-based word drift.

Jargoyle swaps words with alternatives from bundled lexeme dictionaries.
Multiple dictionaries are supported:
- "colors": Color term swapping
- "synonyms": General synonym substitution
- "corporate": Business jargon alternatives
- "academic": Scholarly word substitutions
- "cyberpunk": Neon cyberpunk slang and gadgetry
- "lovecraftian": Cosmic horror terminology
You can also drop additional dictionaries into ``assets/lexemes`` to make
them available without modifying the code. The backend discovers any
``*.json`` file in that directory at runtime.

Two modes are available:
- "literal": First entry in each word's alternatives (deterministic mapping)
- "drift": Random selection from alternatives (probabilistic)
"""

from __future__ import annotations

import os
import random
from importlib import resources
from pathlib import Path
from typing import Any, Literal, cast

from glitchlings.constants import DEFAULT_JARGOYLE_RATE
from glitchlings.internal.rust_ffi import (
    is_bundled_lexeme_rust,
    list_bundled_lexeme_dictionaries_rust,
    list_lexeme_dictionaries_rust,
    resolve_seed,
    substitute_lexeme_rust,
)

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload

_LEXEME_ENV_VAR = "GLITCHLINGS_LEXEME_DIR"
_lexeme_directory_configured = False


def _configure_lexeme_directory() -> Path | None:
    """Expose the bundled lexeme directory to the Rust backend via an env var.

    This is only needed for discovering custom lexeme files at runtime.
    Built-in lexemes (synonyms, colors, corporate, academic, cyberpunk, lovecraftian)
    are embedded directly in the Rust binary and require no file I/O.
    """
    global _lexeme_directory_configured
    if _lexeme_directory_configured:
        return None

    try:
        lexeme_root = resources.files("glitchlings.assets.lexemes")
    except (ModuleNotFoundError, AttributeError):
        _lexeme_directory_configured = True
        return None

    try:
        with resources.as_file(lexeme_root) as resolved:
            path = Path(resolved)
    except FileNotFoundError:
        _lexeme_directory_configured = True
        return None

    if not path.is_dir():
        _lexeme_directory_configured = True
        return None

    os.environ.setdefault(_LEXEME_ENV_VAR, str(path))
    _lexeme_directory_configured = True
    return path


# NOTE: We intentionally do NOT call _configure_lexeme_directory() at module load.
# Built-in lexemes are embedded in the Rust binary and require no file I/O.
# The directory configuration is only needed for custom lexeme discovery.

DEFAULT_LEXEMES = "synonyms"

# Valid modes
JargoyleMode = Literal["literal", "drift"]
VALID_MODES = ("literal", "drift")
DEFAULT_MODE: JargoyleMode = "drift"


def _bundled_lexemes() -> list[str]:
    """Return the list of bundled (embedded) lexeme dictionaries."""
    return sorted({name.lower() for name in list_bundled_lexeme_dictionaries_rust()})


def _available_lexemes() -> list[str]:
    """Return all available lexeme dictionaries (bundled + custom)."""
    return sorted({name.lower() for name in list_lexeme_dictionaries_rust()})


def _validate_lexemes(name: str) -> str:
    """Validate and normalize a lexeme dictionary name.

    For built-in lexemes (bundled in the Rust binary), no file I/O is performed.
    For custom lexemes, the lexeme directory is configured on-demand to discover them.
    """
    normalized = name.lower()

    # Fast path: check if it's a bundled lexeme (no file I/O needed)
    if is_bundled_lexeme_rust(normalized):
        return normalized

    # Slow path: configure directory to discover custom lexemes
    _configure_lexeme_directory()

    available = _available_lexemes()
    if normalized not in available:
        raise ValueError(f"Invalid lexemes '{name}'. Must be one of: {', '.join(available)}")
    return normalized


def _validate_mode(mode: JargoyleMode | str) -> JargoyleMode:
    normalized = mode.lower()
    if normalized not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}")
    return cast(JargoyleMode, normalized)


VALID_LEXEMES = tuple(_bundled_lexemes())


def list_lexeme_dictionaries() -> list[str]:
    """Return the list of available lexeme dictionaries.

    This includes both built-in dictionaries (embedded in the binary) and any
    custom dictionaries found in the lexeme directory.

    Returns:
        List of dictionary names that can be used with Jargoyle.
    """
    # Configure directory to discover any custom lexemes
    _configure_lexeme_directory()
    return _available_lexemes()


def list_bundled_lexeme_dictionaries() -> list[str]:
    """Return the list of bundled (built-in) lexeme dictionaries.

    These dictionaries are embedded directly in the Rust binary and require
    no file I/O to access.

    Returns:
        List of built-in dictionary names: academic, colors, corporate,
        cyberpunk, lovecraftian, synonyms.
    """
    return _bundled_lexemes()


def jargoyle_drift(
    text: str,
    *,
    lexemes: str = DEFAULT_LEXEMES,
    mode: JargoyleMode = DEFAULT_MODE,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Apply dictionary-based word drift to text.

    Args:
        text: Input text to transform.
        lexemes: Name of the dictionary to use.
        mode: "literal" for deterministic first-entry swaps,
              "drift" for random selection from alternatives.
        rate: Probability of transforming each matching word (0.0 to 1.0).
        seed: Seed for deterministic randomness (only used in "drift" mode).
        rng: Random number generator (alternative to seed).

    Returns:
        Text with word substitutions applied.

    Raises:
        ValueError: If lexemes or mode is invalid.
    """
    normalized_lexemes = _validate_lexemes(lexemes)
    normalized_mode = _validate_mode(mode)

    effective_rate = DEFAULT_JARGOYLE_RATE if rate is None else float(rate)
    resolved_seed = resolve_seed(seed, rng) if normalized_mode == "drift" else None

    return substitute_lexeme_rust(
        text,
        normalized_lexemes,
        normalized_mode,
        effective_rate,
        resolved_seed,
    )


class Jargoyle(Glitchling):
    """Glitchling that swaps words using bundled lexeme dictionaries.

    Jargoyle replaces words with alternatives from one of several dictionaries:

    - **colors**: Swap color terms (e.g., "red" -> "blue").
    - **synonyms**: General synonym substitution (e.g., "fast" -> "rapid").
    - **corporate**: Business jargon alternatives.
    - **academic**: Scholarly word substitutions.
    - **cyberpunk**: Neon cyberpunk slang and gadgetry.
    - **lovecraftian**: Cosmic horror terminology.
    - **custom**: Any ``*.json`` dictionary placed in ``assets/lexemes``.

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
        **kwargs: Any,
    ) -> None:
        """Initialize Jargoyle with the specified dictionary and mode.

        Args:
            lexemes: Name of the dictionary to use. See ``list_lexeme_dictionaries()``
                for the full, dynamic list (including any custom ``*.json`` files).
            mode: Transformation mode. "literal" for deterministic swaps,
                "drift" for random selection.
            rate: Probability of transforming each matching word (0.0 to 1.0).
                Defaults to 0.01.
            seed: Seed for deterministic randomness.
        """
        # Validate inputs
        normalized_lexemes = _validate_lexemes(lexemes)
        normalized_mode = _validate_mode(mode)

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
            **kwargs,
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
    "list_bundled_lexeme_dictionaries",
    "list_lexeme_dictionaries",
]

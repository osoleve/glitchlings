"""Hokey glitchling that extends vowels in short words for emphasis.

Flavor text: "She's so cooooooool"
"""

from __future__ import annotations

import random
import re
from typing import Any, cast

from ._rust_extensions import get_rust_operation
from .core import AttackOrder, AttackWave, Gaggle, Glitchling

# Load Rust-accelerated operation if available
_hokey_rust = get_rust_operation("hokey")


def _python_extend_vowels(
    text: str,
    *,
    rate: float = 0.3,
    extension_min: int = 2,
    extension_max: int = 5,
    word_length_threshold: int = 6,
    rng: random.Random,
) -> str:
    """Python implementation that extends vowels in short words.

    Args:
        text: Input text to corrupt.
        rate: Proportion of eligible short words to affect (0.0 to 1.0).
        extension_min: Minimum number of extra repetitions of the vowel.
        extension_max: Maximum number of extra repetitions of the vowel.
        word_length_threshold: Maximum word length to be considered "short".
        rng: Random number generator for deterministic behavior.

    Returns:
        Text with extended vowels in some short words.
    """
    if not text:
        return text

    # Define vowels (both cases)
    vowels = set("aeiouAEIOU")

    # Split text into words while preserving whitespace and punctuation
    # Use regex to split on word boundaries but keep delimiters
    tokens = re.findall(r"\w+|\W+", text)

    # First pass: identify eligible word positions
    eligible_positions = []
    for i, token in enumerate(tokens):
        if re.match(r"\w+", token):
            if len(token) <= word_length_threshold:
                # Check if word has any vowels
                if any(c in vowels for c in token):
                    eligible_positions.append(i)

    # Determine how many words to affect based on rate
    num_to_affect = int(len(eligible_positions) * rate)

    # Shuffle eligible positions to get random selection (deterministic with rng)
    # Sort first to ensure determinism, then shuffle
    shuffled_positions = sorted(eligible_positions)
    rng.shuffle(shuffled_positions)
    positions_to_extend = set(shuffled_positions[:num_to_affect])

    # Second pass: apply extensions
    result_tokens = []
    for i, token in enumerate(tokens):
        if i in positions_to_extend:
            # This is a word position we should extend
            # Find all vowel positions in the word
            vowel_positions = [j for j, c in enumerate(token) if c in vowels]

            if vowel_positions:
                # Choose a vowel position to extend
                # For consistency, we'll extend the last vowel (like "cool" -> "cooool")
                vowel_idx = vowel_positions[-1]
                vowel_char = token[vowel_idx]

                # Determine how many times to repeat the vowel
                num_extra = rng.randint(extension_min, extension_max)

                # Build the extended word
                extended_word = (
                    token[:vowel_idx + 1] +
                    vowel_char * num_extra +
                    token[vowel_idx + 1:]
                )

                result_tokens.append(extended_word)
            else:
                result_tokens.append(token)
        else:
            result_tokens.append(token)

    return "".join(result_tokens)


def extend_vowels(
    text: str,
    rate: float = 0.3,
    extension_min: int = 2,
    extension_max: int = 5,
    word_length_threshold: int = 6,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Extend vowels in short words for emphasis effect.

    Parameters
    ----------
    text : str
        Input text to corrupt.
    rate : float, optional
        Proportion of eligible short words to affect (default 0.3).
    extension_min : int, optional
        Minimum number of extra vowel repetitions (default 2).
    extension_max : int, optional
        Maximum number of extra vowel repetitions (default 5).
    word_length_threshold : int, optional
        Maximum word length to be considered "short" (default 6).
    seed : int, optional
        Random seed if rng not provided.
    rng : random.Random, optional
        Random number generator; overrides seed.

    Returns
    -------
    str
        Text with extended vowels in short words.

    Examples
    --------
    >>> extend_vowels("cool code", rate=1.0, seed=42)
    'coooool coooode'
    """
    if not text:
        return text

    if rng is None:
        rng = random.Random(seed)

    if _hokey_rust is not None:
        return cast(
            str,
            _hokey_rust(
                text,
                rate,
                extension_min,
                extension_max,
                word_length_threshold,
                rng,
            ),
        )

    return _python_extend_vowels(
        text,
        rate=rate,
        extension_min=extension_min,
        extension_max=extension_max,
        word_length_threshold=word_length_threshold,
        rng=rng,
    )


class Hokey(Glitchling):
    """Glitchling that extends vowels in short words for emphasis.

    Flavor text: "She's so cooooooool"

    Hokey makes short words more emphatic by extending their vowels,
    like turning "cool" into "cooooool". Perfect for adding that
    enthusiastic, drawn-out emphasis to your text.
    """

    def __init__(
        self,
        *,
        rate: float = 0.3,
        extension_min: int = 2,
        extension_max: int = 5,
        word_length_threshold: int = 6,
        seed: int | None = None,
    ) -> None:
        """Initialize Hokey with parameters.

        Args:
            rate: Proportion of eligible short words to affect (default 0.3).
            extension_min: Minimum extra vowel repetitions (default 2).
            extension_max: Maximum extra vowel repetitions (default 5).
            word_length_threshold: Max word length to be "short" (default 6).
            seed: Random seed for deterministic behavior.
        """
        self._master_seed: int | None = seed
        super().__init__(
            name="Hokey",
            corruption_function=extend_vowels,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.FIRST,
            seed=seed,
            rate=rate,
            extension_min=extension_min,
            extension_max=extension_max,
            word_length_threshold=word_length_threshold,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        """Return the Rust pipeline operation descriptor."""
        return {
            "type": "hokey",
            "rate": self.kwargs.get("rate", 0.3),
            "extension_min": self.kwargs.get("extension_min", 2),
            "extension_max": self.kwargs.get("extension_max", 5),
            "word_length_threshold": self.kwargs.get("word_length_threshold", 6),
        }

    def reset_rng(self, seed: int | None = None) -> None:
        """Reset the RNG with optional new seed."""
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


# Create a default instance
hokey = Hokey()


__all__ = ["Hokey", "hokey", "extend_vowels"]

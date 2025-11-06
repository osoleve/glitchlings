from __future__ import annotations

from collections.abc import Iterable
from types import ModuleType
from typing import Any, Literal, cast

from glitchlings.lexicon import Lexicon, get_default_lexicon

from ._rust_extensions import get_rust_operation, resolve_seed
from .core import AttackWave, Glitchling

_wordnet_module: ModuleType | None

try:  # pragma: no cover - optional WordNet dependency
    import glitchlings.lexicon.wordnet as _wordnet_module
except (
    ImportError,
    ModuleNotFoundError,
    AttributeError,
):  # pragma: no cover - triggered when nltk unavailable
    _wordnet_module = None

_wordnet_runtime: ModuleType | None = _wordnet_module

WordNetLexicon: type[Lexicon] | None
if _wordnet_runtime is None:

    def _lexicon_dependencies_available() -> bool:
        return False

    def _lexicon_ensure_wordnet() -> None:
        raise RuntimeError(
            "The WordNet backend is no longer bundled by default. Install NLTK "
            "and download its WordNet corpus manually if you need legacy synonyms."
        )

    WordNetLexicon = None
else:
    WordNetLexicon = cast(type[Lexicon], _wordnet_runtime.WordNetLexicon)
    _lexicon_dependencies_available = _wordnet_runtime.dependencies_available
    _lexicon_ensure_wordnet = _wordnet_runtime.ensure_wordnet


ensure_wordnet = _lexicon_ensure_wordnet


def dependencies_available() -> bool:
    """Return ``True`` when a synonym backend is accessible."""
    if _lexicon_dependencies_available():
        return True

    try:
        # Fall back to the configured default lexicon (typically the bundled vector cache).
        get_default_lexicon(seed=None)
    except (RuntimeError, ImportError, ModuleNotFoundError, AttributeError):
        return False
    return True


# Backwards compatibility for callers relying on the previous private helper name.
_ensure_wordnet = ensure_wordnet


PartOfSpeech = Literal["n", "v", "a", "r"]
PartOfSpeechInput = PartOfSpeech | Iterable[PartOfSpeech] | Literal["any"]
NormalizedPartsOfSpeech = tuple[PartOfSpeech, ...]

_VALID_POS: tuple[PartOfSpeech, ...] = ("n", "v", "a", "r")


def _normalize_parts_of_speech(
    part_of_speech: PartOfSpeechInput,
) -> NormalizedPartsOfSpeech:
    """Coerce user input into a tuple of valid WordNet POS tags."""
    if isinstance(part_of_speech, str):
        lowered = part_of_speech.lower()
        if lowered == "any":
            return _VALID_POS
        if lowered not in _VALID_POS:
            raise ValueError("part_of_speech must be one of 'n', 'v', 'a', 'r', or 'any'")
        return (cast(PartOfSpeech, lowered),)

    normalized: list[PartOfSpeech] = []
    for pos in part_of_speech:
        if pos not in _VALID_POS:
            raise ValueError("part_of_speech entries must be one of 'n', 'v', 'a', or 'r'")
        if pos not in normalized:
            normalized.append(pos)
    if not normalized:
        raise ValueError("part_of_speech iterable may not be empty")
    return tuple(normalized)


_SUBSTITUTE_RANDOM_SYNONYMS = get_rust_operation("substitute_random_synonyms")


def substitute_random_synonyms(
    text: str,
    rate: float | None = None,
    part_of_speech: PartOfSpeechInput = "n",
    seed: int | None = None,
    rng: Any | None = None,
    *,
    lexicon: Lexicon | None = None,
) -> str:
    """Replace words with random lexicon-driven synonyms."""

    effective_rate = 0.1 if rate is None else float(rate)

    if lexicon is not None and not isinstance(lexicon, Lexicon):
        raise TypeError("lexicon must be a Lexicon instance or None")

    active_lexicon = lexicon
    restore_lexicon_seed = False
    original_lexicon_seed: int | None = None

    if active_lexicon is None:
        active_lexicon = get_default_lexicon(seed=seed)

    if seed is not None and isinstance(active_lexicon, Lexicon):
        if lexicon is not None:
            original_lexicon_seed = active_lexicon.seed
            if original_lexicon_seed != seed:
                active_lexicon.reseed(seed)
                restore_lexicon_seed = True
        elif active_lexicon.seed != seed:
            active_lexicon.reseed(seed)

    if isinstance(active_lexicon, Lexicon):
        lexicon_seed_repr = None if active_lexicon.seed is None else str(active_lexicon.seed)
    else:
        lexicon_seed_repr = None if seed is None else str(seed)

    try:
        target_pos = _normalize_parts_of_speech(part_of_speech)
        resolved_seed = resolve_seed(seed, rng)
        return cast(
            str,
            _SUBSTITUTE_RANDOM_SYNONYMS(
                text,
                effective_rate,
                list(target_pos),
                resolved_seed,
                active_lexicon,
                lexicon_seed_repr,
            ),
        )
    finally:
        if restore_lexicon_seed and isinstance(active_lexicon, Lexicon):
            active_lexicon.reseed(original_lexicon_seed)


class Jargoyle(Glitchling):
    """Glitchling that swaps words with lexicon-driven synonyms."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        part_of_speech: PartOfSpeechInput = "n",
        seed: int | None = None,
        lexicon: Lexicon | None = None,
    ) -> None:
        if lexicon is not None and not isinstance(lexicon, Lexicon):
            raise TypeError("lexicon must be a Lexicon instance or None")

        if lexicon is None:
            prepared_lexicon = get_default_lexicon(seed=seed)
            owns_lexicon = True
            if not isinstance(prepared_lexicon, Lexicon):
                message = "Default Jargoyle lexicon must be a Lexicon instance"
                raise TypeError(message)
        else:
            prepared_lexicon = lexicon
            owns_lexicon = False

        self._owns_lexicon = owns_lexicon
        self._external_lexicon_original_seed = (
            None if owns_lexicon else prepared_lexicon.seed
        )
        self._initializing = True
        effective_rate = 0.01 if rate is None else rate
        if not owns_lexicon and seed is not None:
            prepared_lexicon.reseed(seed)
        try:
            super().__init__(
                name="Jargoyle",
                corruption_function=substitute_random_synonyms,
                scope=AttackWave.WORD,
                seed=seed,
                rate=effective_rate,
                part_of_speech=part_of_speech,
                lexicon=lexicon,
            )
        finally:
            self._initializing = False

    def set_param(self, key: str, value: Any) -> None:
        super().set_param(key, value)

        aliases = getattr(self, "_param_aliases", {})
        canonical = aliases.get(key, key)

        if canonical == "seed":
            current_lexicon = getattr(self, "lexicon", None)
            if isinstance(current_lexicon, Lexicon):
                if getattr(self, "_owns_lexicon", False):
                    current_lexicon.reseed(self.seed)
                else:
                    if self.seed is not None:
                        current_lexicon.reseed(self.seed)
                    else:
                        if hasattr(self, "_external_lexicon_original_seed"):
                            original_seed = getattr(
                                self, "_external_lexicon_original_seed", None
                            )
                            current_lexicon.reseed(original_seed)
        elif canonical == "lexicon" and isinstance(value, Lexicon):
            if getattr(self, "_initializing", False):
                if getattr(self, "_owns_lexicon", False):
                    if self.seed is not None:
                        value.reseed(self.seed)
                else:
                    if getattr(self, "_external_lexicon_original_seed", None) is None:
                        self._external_lexicon_original_seed = value.seed
                    if self.seed is not None:
                        value.reseed(self.seed)
                return

            self._owns_lexicon = False
            self._external_lexicon_original_seed = value.seed
            if self.seed is not None:
                value.reseed(self.seed)
            elif value.seed != self._external_lexicon_original_seed:
                value.reseed(self._external_lexicon_original_seed)


jargoyle = Jargoyle()


__all__ = ["Jargoyle", "dependencies_available", "ensure_wordnet", "jargoyle"]

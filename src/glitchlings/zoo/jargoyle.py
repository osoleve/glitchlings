import random
import re
from collections.abc import Iterable
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Literal, cast

from glitchlings.lexicon import Lexicon, get_default_lexicon

from ._rate import resolve_rate
from .core import AttackWave, Glitchling

_wordnet_module: ModuleType | None

try:  # pragma: no cover - optional WordNet dependency
    import glitchlings.lexicon.wordnet as _wordnet_module
except (ImportError, ModuleNotFoundError, AttributeError):  # pragma: no cover - triggered when nltk unavailable
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


def _split_token(token: str) -> tuple[str, str, str]:
    """Split a token into leading punctuation, core word, and trailing punctuation."""
    match = re.match(r"^(\W*)(.*?)(\W*)$", token)
    if not match:
        return "", token, ""
    prefix, core, suffix = match.groups()
    return prefix, core, suffix


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


@dataclass(frozen=True)
class CandidateInfo:
    """Metadata for a candidate token that may be replaced."""

    prefix: str
    core_word: str
    suffix: str
    part_of_speech: str | None
    synonyms: list[str]


def substitute_random_synonyms(
    text: str,
    rate: float | None = None,
    part_of_speech: PartOfSpeechInput = "n",
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    replacement_rate: float | None = None,
    lexicon: Lexicon | None = None,
) -> str:
    """Replace words with random lexicon-driven synonyms.

    Parameters
    ----------
    - text: Input text.
    - rate: Max proportion of candidate words to replace (default 0.01).
    - part_of_speech: WordNet POS tag(s) to target. Accepts "n", "v", "a", "r",
      any iterable of those tags, or "any" to include all four. Backends that do
      not differentiate parts of speech simply ignore the setting.
    - rng: Optional RNG instance used for deterministic sampling.
    - seed: Optional seed if `rng` not provided.
    - lexicon: Optional :class:`~glitchlings.lexicon.Lexicon` implementation to
      supply synonyms. Defaults to the configured lexicon priority, typically the
      packaged vector cache.

    Determinism
    - Candidates collected in left-to-right order; no set() reordering.
    - Replacement positions chosen via rng.sample.
    - Synonyms sourced through the lexicon; the default backend derives
      deterministic subsets per word and part-of-speech using the active seed.

    """
    effective_rate = resolve_rate(
        rate=rate,
        legacy_value=replacement_rate,
        default=0.1,
        legacy_name="replacement_rate",
    )

    active_rng: random.Random
    if rng is not None:
        active_rng = rng
    else:
        active_rng = random.Random(seed)

    active_lexicon: Lexicon
    restore_lexicon_seed = False
    original_lexicon_seed: int | None = None

    if lexicon is None:
        active_lexicon = get_default_lexicon(seed=seed)
    else:
        active_lexicon = lexicon
        if seed is not None:
            original_lexicon_seed = active_lexicon.seed
            if original_lexicon_seed != seed:
                active_lexicon.reseed(seed)
                restore_lexicon_seed = True

    try:
        target_pos = _normalize_parts_of_speech(part_of_speech)

        # Split but keep whitespace separators so we can rebuild easily
        tokens = re.split(r"(\s+)", text)

        # Collect candidate word indices (even positions are words because separators are kept)
        candidate_indices: list[int] = []
        candidate_metadata: dict[int, CandidateInfo] = {}
        for idx, tok in enumerate(tokens):
            if idx % 2 != 0 or not tok or tok.isspace():
                continue

            prefix, core_word, suffix = _split_token(tok)
            if not core_word:
                continue

            chosen_pos: str | None = None
            synonyms: list[str] = []

            for tag in target_pos:
                if not active_lexicon.supports_pos(tag):
                    continue
                synonyms = active_lexicon.get_synonyms(core_word, pos=tag)
                if synonyms:
                    chosen_pos = tag
                    break

            if not synonyms and active_lexicon.supports_pos(None):
                synonyms = active_lexicon.get_synonyms(core_word, pos=None)

            if synonyms:
                candidate_indices.append(idx)
                candidate_metadata[idx] = CandidateInfo(
                    prefix=prefix,
                    core_word=core_word,
                    suffix=suffix,
                    part_of_speech=chosen_pos,
                    synonyms=synonyms,
                )

        if not candidate_indices:
            return text

        clamped_rate = max(0.0, effective_rate)
        if clamped_rate == 0.0:
            return text

        population = len(candidate_indices)
        effective_fraction = min(clamped_rate, 1.0)
        expected_replacements = population * effective_fraction
        max_replacements = int(expected_replacements)
        remainder = expected_replacements - max_replacements
        if remainder > 0.0 and active_rng.random() < remainder:
            max_replacements += 1
        if clamped_rate >= 1.0:
            max_replacements = population
        max_replacements = min(population, max_replacements)
        if max_replacements <= 0:
            return text

        # Choose which positions to replace deterministically via rng.sample
        replace_positions = active_rng.sample(candidate_indices, k=max_replacements)
        # Process in ascending order to avoid affecting later indices
        replace_positions.sort()

        for pos in replace_positions:
            metadata = candidate_metadata[pos]
            if not metadata.synonyms:
                continue

            replacement = active_rng.choice(metadata.synonyms)
            tokens[pos] = f"{metadata.prefix}{replacement}{metadata.suffix}"

        return "".join(tokens)
    finally:
        if restore_lexicon_seed:
            active_lexicon.reseed(original_lexicon_seed)


class Jargoyle(Glitchling):
    """Glitchling that swaps words with lexicon-driven synonyms."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        replacement_rate: float | None = None,
        part_of_speech: PartOfSpeechInput = "n",
        seed: int | None = None,
        lexicon: Lexicon | None = None,
    ) -> None:
        self._param_aliases = {"replacement_rate": "rate"}
        self._owns_lexicon = lexicon is None
        self._external_lexicon_original_seed = (
            lexicon.seed if isinstance(lexicon, Lexicon) else None
        )
        self._initializing = True
        effective_rate = resolve_rate(
            rate=rate,
            legacy_value=replacement_rate,
            default=0.01,
            legacy_name="replacement_rate",
        )
        prepared_lexicon = lexicon or get_default_lexicon(seed=seed)
        if lexicon is not None and seed is not None:
            prepared_lexicon.reseed(seed)
        try:
            super().__init__(
                name="Jargoyle",
                corruption_function=substitute_random_synonyms,
                scope=AttackWave.WORD,
                seed=seed,
                rate=effective_rate,
                part_of_speech=part_of_speech,
                lexicon=prepared_lexicon,
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
                            original_seed = getattr(self, "_external_lexicon_original_seed", None)
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

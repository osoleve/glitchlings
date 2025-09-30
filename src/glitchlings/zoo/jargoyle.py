import random
from collections.abc import Iterable
from typing import Literal, Any, cast
import nltk
import re
from nltk.corpus import wordnet as wn
from .core import Glitchling, AttackWave

_wordnet_ready = False


def _ensure_wordnet() -> None:
    """Ensure the WordNet corpus is available before use."""

    global _wordnet_ready
    if _wordnet_ready:
        return

    try:
        wn.ensure_loaded()
    except LookupError:
        nltk.download("wordnet", quiet=True)
        try:
            wn.ensure_loaded()
        except LookupError as exc:  # pragma: no cover - only triggered when download fails
            raise RuntimeError(
                "Unable to load NLTK WordNet corpus for the jargoyle glitchling."
            ) from exc

    _wordnet_ready = True


PartOfSpeech = Literal["n", "v", "a", "r"]
PartOfSpeechInput = PartOfSpeech | Iterable[PartOfSpeech] | Literal["any"]

_VALID_POS: tuple[PartOfSpeech, ...] = ("n", "v", "a", "r")


def _normalize_parts_of_speech(part_of_speech: PartOfSpeechInput) -> tuple[PartOfSpeech, ...]:
    """Coerce user input into a tuple of valid WordNet POS tags."""

    if isinstance(part_of_speech, str):
        lowered = part_of_speech.lower()
        if lowered == "any":
            return _VALID_POS
        if lowered not in _VALID_POS:
            raise ValueError(
                "part_of_speech must be one of 'n', 'v', 'a', 'r', or 'any'"
            )
        return (cast(PartOfSpeech, lowered),)

    normalized: list[PartOfSpeech] = []
    for pos in part_of_speech:
        if pos not in _VALID_POS:
            raise ValueError(
                "part_of_speech entries must be one of 'n', 'v', 'a', or 'r'"
            )
        if pos not in normalized:
            normalized.append(pos)
    if not normalized:
        raise ValueError("part_of_speech iterable may not be empty")
    return tuple(normalized)


def substitute_random_synonyms(
    text: str,
    replacement_rate: float = 0.1,
    part_of_speech: PartOfSpeechInput = "n",
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Replace words with random WordNet synonyms.

    Parameters
    - text: Input text.
    - replacement_rate: Max proportion of candidate words to replace (default 0.1).
    - part_of_speech: WordNet POS tag(s) to target. Accepts "n", "v", "a", "r",
      any iterable of those tags, or "any" to include all four.
    - rng: Optional RNG instance used for deterministic sampling.
    - seed: Optional seed if `rng` not provided.

    Determinism
    - Candidates collected in left-to-right order; no set() reordering.
    - Replacement positions chosen via rng.sample.
    - Synonyms sorted before rng.choice to fix ordering.
    - Only first synset is used for stability.
    """
    _ensure_wordnet()

    if rng is None and seed is not None:
        rng = random.Random(seed)
    elif rng is None:
        rng = random.Random()

    target_pos = _normalize_parts_of_speech(part_of_speech)

    # Split but keep whitespace separators so we can rebuild easily
    tokens = re.split(r"(\s+)", text)

    # Collect indices of candidate tokens (even positions 0,2,.. are words given our split design)
    candidate_indices: list[int] = []
    candidate_pos_map: dict[int, tuple[PartOfSpeech, ...]] = {}
    for idx, tok in enumerate(tokens):
        if idx % 2 == 0 and tok and not tok.isspace():
            available_pos = tuple(
                pos for pos in target_pos if wn.synsets(tok, pos=pos)
            )
            if available_pos:
                candidate_indices.append(idx)
                candidate_pos_map[idx] = available_pos

    if not candidate_indices:
        return text

    max_replacements = int(len(candidate_indices) * replacement_rate)
    if max_replacements <= 0:
        return text

    # Choose which positions to replace deterministically via rng.sample
    replace_positions = rng.sample(candidate_indices, k=max_replacements)
    # Process in ascending order to avoid affecting later indices
    replace_positions.sort()

    for pos in replace_positions:
        word = tokens[pos]
        synonyms: set[str] = set()
        for pos_tag in candidate_pos_map.get(pos, target_pos):
            synsets = wn.synsets(word, pos=pos_tag)
            if not synsets:
                continue
            synset0: Any = synsets[0]
            lemmas_list = [lemma.name() for lemma in cast(Any, synset0).lemmas()]
            if not lemmas_list:
                continue
            for lemma_str in lemmas_list:
                cleaned = lemma_str.replace("_", " ")
                if cleaned.lower() != word.lower():
                    synonyms.add(cleaned)

        if not synonyms:
            continue

        replacement = rng.choice(sorted(synonyms))
        tokens[pos] = replacement

    return "".join(tokens)


class Jargoyle(Glitchling):
    """Glitchling that swaps words with random WordNet synonyms."""

    def __init__(
        self,
        *,
        replacement_rate: float = 0.1,
        part_of_speech: PartOfSpeechInput = "n",
        seed: int | None = None,
    ) -> None:
        super().__init__(
            name="Jargoyle",
            corruption_function=substitute_random_synonyms,
            scope=AttackWave.WORD,
            seed=seed,
            replacement_rate=replacement_rate,
            part_of_speech=part_of_speech,
        )


jargoyle = Jargoyle()


__all__ = ["Jargoyle", "jargoyle"]

import random
from typing import Literal, Any, cast
import nltk
import re
from nltk.corpus import wordnet as wn
from .core import Glitchling, AttackWave

nltk.download("wordnet", quiet=True)


def substitute_random_synonyms(
    text: str,
    replacement_rate: float = 0.1,
    part_of_speech: Literal["n", "v", "a", "r"] = wn.NOUN,
    rng: random.Random | None = None,
) -> str:
    """Replace words with random WordNet synonyms.

    Parameters
    - text: Input text.
    - replacement_rate: Max proportion of candidate words to replace (default 0.1).
    - part_of_speech: WordNet POS to target. One of wn.NOUN (default), wn.VERB, wn.ADJ, wn.ADV.
    - rng: Optional RNG instance used for deterministic sampling.

    Determinism
    - Candidates collected in left-to-right order; no set() reordering.
    - Replacement positions chosen via rng.sample.
    - Synonyms sorted before rng.choice to fix ordering.
    - Only first synset is used for stability.
    """
    if rng is None:
        rng = random.Random()

    # Split but keep whitespace separators so we can rebuild easily
    tokens = re.split(r"(\s+)", text)

    # Collect indices of candidate tokens (even positions 0,2,.. are words given our split design)
    candidate_indices: list[int] = []
    for idx, tok in enumerate(tokens):
        if idx % 2 == 0 and tok and not tok.isspace():
            if wn.synsets(tok, pos=part_of_speech):
                candidate_indices.append(idx)

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
        synsets = wn.synsets(word, pos=part_of_speech)
        if not synsets:
            continue
        synset0: Any = synsets[0]
        lemmas_list = [lemma.name() for lemma in cast(Any, synset0).lemmas()]
        if not lemmas_list:
            continue
        # Normalize & dedupe deterministically
        synonyms = sorted(
            {
                lemma_str.replace("_", " ")
                for lemma_str in lemmas_list
                if lemma_str.lower() != word.lower()
            }
        )
        if not synonyms:
            continue
        replacement = rng.choice(synonyms)
        tokens[pos] = replacement

    return "".join(tokens)


jargoyle = Glitchling(
    name="Jargoyle",
    corruption_function=substitute_random_synonyms,
    scope=AttackWave.WORD,
)

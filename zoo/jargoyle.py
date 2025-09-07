import random
from typing import Literal
import nltk
import re
from nltk.corpus import wordnet as wn
from .core import Glitchling, AttackWave

nltk.download("wordnet", quiet=True)


def substitute_random_synonyms(
    text: str,
    replacement_rate: float = 0.1,
    part_of_speech: Literal[wn.NOUN, wn.VERB, wn.ADJ, wn.ADV] = wn.NOUN,
    rng: random.Random | None = None,
) -> str:
    """Replace words having a WordNet synset with a random synonym deterministically for a given rng.

    Determinism considerations:
    - Candidate words collected in original order of appearance (left to right), no set()-induced reordering.
    - Replacement indices chosen by rng.sample over the index list.
    - Synonym list sorted before rng selection to avoid underlying order variability.
    - Only first synset used (WordNet order is stable across runs for fixed version).
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
        lemmas = [lemma.name() for lemma in synsets[0].lemmas()]
        if not lemmas:
            continue
        # Normalize & dedupe deterministically
        synonyms = sorted(
            {l.replace("_", " ") for l in lemmas if l.lower() != word.lower()}
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
jargoyle.img = r""""""

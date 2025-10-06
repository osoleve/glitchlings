# Jargoyle

Jargoyle swaps words with WordNet synonyms to inject domain drift and vocabulary variety.

- **Scope**: word level.
- **Signature**: `Jargoyle(replacement_rate=0.1, part_of_speech="n", seed=None)`.
- **Behaviour**: swaps nouns/verbs/adjectives/adverbs with WordNet synonyms. Downloads the WordNet corpus on demand when missing and maintains deterministic sampling by sorting candidate lemmas.
- **Usage tips**:
  - Target specific POS tags (e.g., `part_of_speech=("n", "v")`) to limit changes to content words.
  - Lower `replacement_rate` (0.02–0.05) for subtle lexical variety; higher rates explore paraphrasing extremes.
  - Ensure your environment has the WordNet data pre-cached to avoid first-run download delays.

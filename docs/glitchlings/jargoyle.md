# Jargoyle

Jargoyle swaps words with deterministic synonyms supplied by the active lexicon backend to inject domain drift and vocabulary variety.

- **Scope**: word level.
- **Signature**: `Jargoyle(rate=0.01, part_of_speech="n", seed=None)`.
- **Behaviour**: swaps nouns/verbs/adjectives/adverbs with synonyms sourced from the configured lexicon priority. The default install ships a lightweight vector cache; add ConceptNet caches or WordNet as fallbacks by editing `config.toml`.
- **Usage tips**:
  - Target specific POS tags (e.g., `part_of_speech=("n", "v")`) to limit changes to content words.
  - Use the default `rate=0.01` for gentle lexical drift; raise it (0.02–0.05) when you need bolder paraphrases.
  - Rebuild the vector cache with `glitchlings build-lexicon` when you have richer embeddings or bespoke vocabularies. Install `nltk` and download the WordNet corpus if you want the legacy synonym set as a fallback.

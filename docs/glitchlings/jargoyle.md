# Jargoyle

Jargoyle swaps words with deterministic synonyms supplied by the active lexicon backend to inject domain drift and vocabulary variety.

- **Scope**: word level.
- **Signature**: `Jargoyle(rate=0.01, part_of_speech="n", seed=None)`.
- **Behaviour**: swaps nouns/verbs/adjectives/adverbs with synonyms sourced from the configured lexicon priority. The default install ships a lightweight cache derived from the `sentence-transformers/all-mpnet-base-v2` checkpoint; add WordNet or bespoke caches (vector or transformer-backed) by editing `config.toml`.
- **Usage tips**:
  - Target specific POS tags (e.g., `part_of_speech=("n", "v")`) to limit changes to content words.
  - Use the default `rate=0.01` for gentle lexical drift; raise it (0.02–0.05) when you need bolder paraphrases.
  - Rebuild the vector cache with `glitchlings build-lexicon` when you have richer embeddings or bespoke vocabularies. Pass `--source sentence-transformers:sentence-transformers/all-mpnet-base-v2 --tokens words.txt` to mirror the bundled behaviour, and install `nltk`/WordNet if you want the legacy synonym set as a fallback.

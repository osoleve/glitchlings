# Lexicon backends

## Precomputing vector lexicon caches

The vector backend prefers cached nearest neighbours for fast, deterministic lookups. Build a cache from a spaCy pipeline or a gensim `KeyedVectors` file:

```bash
glitchlings build-lexicon \
    --source spacy:en_core_web_md \
    --output data/vector_lexicon.json \
    --overwrite
```

Provide a newline-delimited vocabulary with `--tokens words.txt` when you only care about a subset of words, or point `--source` at a KeyedVectors/word2vec file to work from pre-trained embeddings stored on disk. SentenceTransformer checkpoints are supported via `--source sentence-transformers:<model>` (pair them with `--tokens` to define the vocabulary). The repo ships a compact default cache (`lexicon/data/default_vector_cache.json`) derived from the `sentence-transformers/all-mpnet-base-v2` model so the CLI and tests work out of the box; regenerate it when you have richer embeddings or bespoke vocabularies.

## Lexicon evaluation metrics

Compare alternative synonym sources or refreshed caches with `glitchlings.lexicon.metrics`. The `compare_lexicons(...)` helper reports average synonym diversity, the share of tokens with three or more substitutes, and mean cosine similarity using any embedding table you pass in. These utilities underpin the lexicon regression tests so new backends stay deterministic without sacrificing coverage or semantic cohesion.

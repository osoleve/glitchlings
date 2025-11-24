# Glitchlings development setup

This guide walks through preparing a local development environment, running the automated checks, and working with the Rust acceleration layer that now powers the core runtime. It is the source of truth for contributor workflow details.

## Prerequisites

- Python 3.10+
- `pip` and a virtual environment tool of your choice (the examples below use `python -m venv`)
- A Rust toolchain (`rustup` or system packages) and [`maturin`](https://www.maturin.rs/) for compiling the PyO3 extensions

## Install the project

1. Clone the repository and create an isolated environment:

   ```bash
   git clone https://github.com/osoleve/glitchlings.git
   cd glitchlings
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the package in editable mode with the development dependencies:

   ```bash
   pip install -e .[dev]
   ```

   Add the `prime` extra (`pip install -e .[dev,prime]`) when you need the Prime Intellect integration and its `verifiers` dependency.
   Enable the embedding-backed lexicon helpers with the `vectors` extra (`pip install -e .[dev,vectors]`) to pull in `numpy`, `spaCy`, and `gensim`.

3. Install the git hooks so the shared formatting, linting, and type checks run automatically:

   ```bash
   pre-commit install
   ```

3. The package ships a compact vector-cache for Jargoyle so you can exercise synonym swaps without heavyweight models. Regenerate or extend that cache with the bundled CLI when you have larger embeddings available:

   ```bash
   glitchlings build-lexicon \
       --source spacy:en_core_web_md \
       --output data/vector_lexicon.json \
       --limit 50000 \
       --overwrite
   ```

   The command accepts gensim-compatible KeyedVectors or Word2Vec formats via `--source /path/to/vectors.kv`. Pass `--tokens words.txt` to restrict caching to a curated vocabulary, tweak `--min-similarity`/`--max-neighbors` to trade breadth for precision, and bake in deterministic seeds with `--seed`. HuggingFace SentenceTransformer checkpoints work too: install the `st` extra and call `--source sentence-transformers:sentence-transformers/all-mpnet-base-v2 --tokens words.txt` to mirror the bundled cache.

   Need to sanity-check new lexical sources? Import `glitchlings.lexicon.metrics` and call `compare_lexicons(...)` to benchmark synonym diversity, ≥3-substitute coverage, and mean cosine similarity against previously captured baselines.

   Prefer the legacy WordNet behaviour? Install `nltk`, download its WordNet corpus (`python -m nltk.downloader wordnet`), and update `config.toml` so the `lexicon.priority` includes `"wordnet"` ahead of the vector cache.

## Run the test suite

Execute the automated tests from the repository root:

```bash
pytest
```

The suite covers determinism guarantees, dataset integrations, and the compiled Rust implementation that now backs orchestration. Vector-backed lexicons ship with the repository so the Jargoyle tests run without external downloads, while optional WordNet checks are gated behind the legacy backend being available.

## Automated checks

Run the shared quality gates before opening a pull request:

```bash
ruff check .
black --check .
isort --check-only .
python -m mypy --config-file pyproject.toml
pytest --maxfail=1 --disable-warnings -q
```

## Additional tips

- Rebuild the Rust extension after editing files under `rust/zoo/`:

  ```bash
  maturin develop -m rust/zoo/Cargo.toml
  ```

- Regenerate the CLI reference page, Monster Manual (both repo root and docs site copies), and glitchling gallery together with:

  ```bash
  python -m glitchlings.dev.docs
  # or, once installed: glitchlings-refresh-docs
  ```

# Glitchlings development setup

This guide walks through preparing a local development environment, running the automated checks, and exercising the optional Rust acceleration layer.

## Prerequisites

- Python 3.10+
- `pip` and a virtual environment tool of your choice (the examples below use `python -m venv`)
- [Optional] A Rust toolchain (`rustup` or system packages) and [`maturin`](https://www.maturin.rs/) for compiling the PyO3 extensions

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

The suite covers determinism guarantees, dataset integrations, and parity between Python and Rust implementations. Vector-backed lexicons ship with the repository so the Jargoyle tests run without external downloads, while optional WordNet checks are gated behind the legacy backend being available.

Key regression guardrails live in:

- `tests/test_glitchling_core.py` for `Gaggle` orchestration and feature flags.
- `tests/test_cli.py` for CLI argument wiring and diff output.
- `tests/test_rust_backed_glitchlings.py` to ensure the acceleration layer mirrors the Python pipeline.

## Automated checks

Run the shared quality gates before opening a pull request:

```bash
ruff check .
black --check .
isort --check-only .
python -m mypy --config-file pyproject.toml
pytest --maxfail=1 --disable-warnings -q
```

## Rust acceleration

Glitchlings ships PyO3 extensions that accelerate Typogre, Mim1c, Rushmore, Adjax, Redactyl, and Scannequin. Compile them with `maturin`; the Python interfaces pick them up automatically when available:

```bash
# Compile the shared Rust crate (rerun after Rust or Python updates)
maturin develop -m rust/zoo/Cargo.toml

# Optional: disable the fast path before importing glitchlings
export GLITCHLINGS_RUST_PIPELINE=0
```

`Gaggle` prefers the compiled fast path whenever the extension is importable. Set the environment variable to `0`/`false` (or any other falsey value) to force the pure-Python orchestrator when debugging or profiling. The test suite automatically covers both code paths - re-run `pytest` once normally and once with the flag set to `0` to verify changes across implementations.


## Additional tips

- Rebuild the Rust extension after editing files under `rust/zoo/`:

  ```bash
  maturin develop -m rust/zoo/Cargo.toml
  ```

- Use `python -m glitchlings --help` to smoke-test CLI changes quickly.
- Check `docs/index.md` for end-user guidance - keep it in sync with behaviour changes when you ship new glitchlings or orchestration features.
- When a TestPyPI publish fails, re-trigger the "Build & Publish (TestPyPI)" GitHub Actions workflow or fast-forward `dev` to rerun the pipeline - see `docs/release-process.md` for the manual steps.
- Validate YAML attack rosters with `glitchlings.config.ATTACK_CONFIG_SCHEMA` (or `load_attack_config`) so CI catches unsupported fields before they reach users. Every glitchling mapping must declare `name:` explicitly.

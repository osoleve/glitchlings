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

## Functional Purity Architecture

The codebase follows a layered architecture that separates **pure** (deterministic, side-effect-free) code from **impure** (stateful, side-effectful) code. This separation makes the code more testable, predictable, and easier for AI coding agents to work with.

### What is Pure Code?

Pure functions:

- Return the same output given the same inputs
- Have no side effects (no IO, logging, or external state mutation)
- Do not manipulate RNG objects directly—they accept pre-computed random values

### What is Impure Code?

Impure code includes:

- File IO (configuration loading, cache reading/writing)
- Rust FFI calls via `get_rust_operation()`
- RNG state management (`random.Random` instantiation, seeding)
- Optional dependency imports (`compat.py` loaders)
- Global state access (`get_config()`, cached singletons)

### Module Organization

The zoo subpackage organizes code by purity:

| Module | Type | Purpose |
|--------|------|---------|
| `zoo/validation.py` | Pure | Boundary validation, rate clamping, parameter normalization |
| `zoo/transforms.py` | Pure | Text tokenization, keyboard processing, string diffs |
| `zoo/rng.py` | Pure boundary | Seed resolution, hierarchical derivation |
| `zoo/_text_utils.py` | Pure | Word splitting, token edge extraction |
| `internal/rust.py` | Impure | Rust FFI loader, operation dispatch |
| `compat.py` | Impure | Optional dependency detection |

### Boundary Layer Pattern

Validation and defensive code belong at **module boundaries** where untrusted input enters:

- CLI argument parsing (`main.py`)
- Public API entry points (`Glitchling.__init__`, `Attack.__init__`)
- Configuration loaders (`conf/` module)

Core transformation functions **inside** these boundaries should:

- Trust that inputs are already validated
- NOT check for `None` on required parameters
- NOT re-validate types that the boundary already checked
- NOT add defensive `try/except` around trusted calls

### Example: Correct Pattern

```python
# In validation.py (boundary layer - validate thoroughly)
def normalize_rate(value: float | None, default: float) -> float:
    """Validate and normalize a rate parameter."""
    effective = default if value is None else value
    if math.isnan(effective):
        return 0.0
    return max(0.0, effective)

# In typogre.py (uses boundary layer, trusts result)
def fatfinger(text: str, rate: float, ...) -> str:
    # rate is already validated - just use it
    clamped_rate = max(0.0, rate)  # Simple floor, not full validation
    return _fatfinger_rust(text, clamped_rate, ...)
```

### Example: Anti-Pattern

```python
# DON'T: Re-validate everywhere
def some_pure_transform(text: str, rate: float) -> str:
    # Bad: re-validating what boundary should have checked
    if rate is None:
        raise ValueError("rate cannot be None")
    if not isinstance(rate, (int, float)):
        raise TypeError("rate must be numeric")
    if math.isnan(rate):
        rate = 0.0
    # ... actual logic
```

### Import Conventions

Pure modules must follow strict import rules:

1. **Pure modules** can only import from:
   - Python standard library
   - Other pure modules

2. **Pure modules** must NOT import:
   - `glitchlings.internal.rust`
   - `glitchlings.config`
   - `glitchlings.compat`
   - Any module that triggers side effects at import time

3. **Use TYPE_CHECKING guards** for type-only imports:

   ```python
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from glitchlings.zoo.core import Glitchling
   ```

### Enforcement

The architecture is enforced by automated tests in `tests/test_purity_architecture.py`:

```bash
pytest tests/test_purity_architecture.py -v
```

These tests verify:

- Pure modules don't import impure modules
- Pure modules only use stdlib imports
- All pure modules have docstrings documenting their purity guarantees

### Why This Matters for AI Agents

AI coding agents tend to add defensive checks everywhere. This architecture makes it explicit:

- If you're in a `pure/` or `transforms/` module: **trust your inputs**
- If you're at a boundary: **validate thoroughly once**
- If you're unsure: check which layer the file belongs to

This reduces noise in the codebase and makes the agent-written code more consistent with human-written code.

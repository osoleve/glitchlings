# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Glitchlings is a Python package for deterministic, linguistically-principled text corruption. It provides utilities to augment text datasets by introducing realistic perturbations that test language model robustness. The project includes both pure Python implementations and an optional Rust acceleration layer via PyO3.

## Development Commands

### Setup
```bash
# Initial setup with development dependencies
pip install -e .[dev]

# Install pre-commit hooks for automated quality checks
pre-commit install

# Install with specific extras
pip install -e .[dev,prime]     # Adds Prime Intellect integration
pip install -e .[dev,vectors]   # Adds spaCy/gensim for vector lexicons
pip install -e .[all]            # All optional dependencies
```

### Testing
```bash
# Run full test suite
pytest

# Run with specific verbosity and fail-fast
pytest --maxfail=1 --disable-warnings -q

# Test a single file/module
pytest tests/core/test_glitchling_core.py

# Test Rust parity (run twice: once with and once without Rust)
pytest
GLITCHLINGS_RUST_PIPELINE=0 pytest
```

### Code Quality
```bash
# Lint (run all checks in order)
ruff check .
black --check .
isort --check-only .
python -m mypy --config-file pyproject.toml

# Auto-fix formatting
black .
isort .
ruff check --fix .
```

### Rust Extension
```bash
# Compile Rust extension for local development
maturin develop -m rust/zoo/Cargo.toml

# Force Python-only mode (disable Rust pipeline)
export GLITCHLINGS_RUST_PIPELINE=0
```

### CLI & Documentation
```bash
# Test CLI changes quickly
python -m glitchlings --help
glitchlings --list

# Rebuild CLI reference in README.md (run after CLI changes)
python docs/build_cli_reference.py
```

## Architecture

### Core Concepts

**Glitchlings** are text corruption classes that implement deterministic, reproducible transformations. Each glitchling has:
- **Scope**: The text unit it operates on (document, paragraph, sentence, word, character)
- **Order**: Execution priority within its scope (early, normal, late, last)
- **Determinism**: Owned Random instance for reproducible corruption

**Gaggle** is the orchestrator that automatically orders and chains multiple glitchlings based on their scope and order.

### Directory Structure

```
src/glitchlings/
├── zoo/              # Core glitchling implementations
│   ├── core.py       # Glitchling base class, Gaggle orchestrator, Rust integration
│   ├── typogre.py    # Keyboard typos
│   ├── mim1c.py      # Unicode confusables
│   ├── jargoyle.py   # Synonym replacement
│   └── ...           # Other glitchlings
├── lexicon/          # Synonym/word relationship systems
│   ├── vector.py     # Embedding-based lexicons (spaCy, gensim, sentence-transformers)
│   └── wordnet.py    # NLTK WordNet backend
├── dlc/              # External integrations ("downloadable content")
│   ├── huggingface.py    # HuggingFace datasets integration
│   ├── pytorch.py        # PyTorch DataLoader integration
│   ├── pytorch_lightning.py  # Lightning DataModule integration
│   └── prime.py          # Prime Intellect integration
├── compat.py         # Optional dependency management system
├── config.py         # YAML attack config loading/validation
└── main.py           # CLI entrypoint

rust/zoo/             # PyO3 acceleration layer (mirrors Python implementations)
tests/
├── core/             # Gaggle, determinism, base glitchling tests
├── rust/             # Rust/Python parity tests
├── dlc/              # Integration tests
└── cli/              # CLI tests
```

### Key Architectural Patterns

#### Deterministic Corruption
Every glitchling MUST maintain determinism:
- Each glitchling owns its own `random.Random` instance (never use global `random`)
- All randomness goes through the `rng` parameter internally
- Same seed + same input + same data = identical output
- Sort collections before shuffling/sampling to maintain stability

When debugging non-deterministic behavior:
1. Search for direct calls to `random.choice/shuffle` not using `rng`
2. Check for `set()` usage without sorting
3. Ensure stable sort keys when indices reference length-changing edits

#### Rust/Python Parity
The Rust extension (`glitchlings._zoo_rust`) provides optimized implementations of several glitchlings. The Python codebase automatically detects and uses Rust when available via:
- `is_rust_pipeline_supported()`: Checks if extension is compiled
- `is_rust_pipeline_enabled()`: Checks if extension is available AND not disabled via `GLITCHLINGS_RUST_PIPELINE=0`
- `pipeline_feature_flag_enabled()`: Checks environment flag

The Gaggle orchestrator in `zoo/core.py` automatically delegates to Rust when enabled. Tests in `tests/rust/` verify exact output parity between implementations.

#### Optional Dependencies
The `compat.py` module provides lazy loading of optional dependencies:
- `datasets`: HuggingFace datasets integration
- `pytorch_lightning`: Lightning DataModule
- `verifiers`: Prime Intellect
- `jellyfish`: Phonetic matching (for future glitchlings)
- `nltk`: WordNet lexicon backend
- `torch`: PyTorch DataLoader

Use `OptionalDependency.get()` to check availability, `.load()` to raise on missing, `.require(message)` for custom errors.

#### Lexicon System
Jargoyle (synonym replacement) uses a pluggable lexicon system:
- **Vector cache** (default): Pre-computed embeddings from spaCy/gensim/sentence-transformers in `lexicon/data/`
- **WordNet**: NLTK-based, legacy backend
- Priority configurable via `config.toml`

Build new vector caches with:
```bash
glitchlings build-lexicon --source spacy:en_core_web_md --output data/vector_lexicon.json
```

### Glitchling Scopes & Orders

Glitchlings execute in waves based on scope (coarse to fine) and order (within scope):

**Scopes** (from `zoo/core.py`):
1. Document
2. Paragraph
3. Sentence
4. Word
5. Character

**Orders** (within each scope):
1. Early
2. Normal
3. Late
4. Last

When creating new glitchlings, assign appropriate scope and order to ensure correct execution sequence in Gaggles.

## Adding New Glitchlings

1. Create new file in `src/glitchlings/zoo/` (e.g., `newling.py`)
2. Implement the `Glitchling` protocol with required methods
3. Add to `zoo/__init__.py` exports
4. Add to main `__init__.py` exports
5. Ensure determinism: own Random instance, all randomness via `rng` parameter
6. Add tests in `tests/core/`
7. Update `docs/glitchlings/newling.md` with documentation
8. If implementing Rust version:
   - Add to `rust/zoo/src/` mirroring Python structure
   - Add parity tests in `tests/rust/`
   - Rebuild with `maturin develop -m rust/zoo/Cargo.toml`

## Common Workflows

### Running a single test module
```bash
pytest tests/core/test_glitchling_core.py -v
```

### Testing determinism of a glitchling
```bash
# Tests automatically verify that running twice with same seed produces identical output
pytest tests/core/ -k determinism
```

### Adding a new integration
New integrations go in `src/glitchlings/dlc/`. Follow the pattern in `huggingface.py`:
- Use `compat.py` to gate on optional dependency
- Provide clear error messages when dependencies are missing
- Add integration tests in `tests/dlc/`

### Updating CLI help text
1. Modify argparse in `src/glitchlings/main.py`
2. Run `python docs/build_cli_reference.py` to update README.md
3. Commit both changes together

## CI/CD

GitHub Actions workflows in `.github/workflows/`:
- **ci.yml**: Runs on PRs and pushes to dev/main. Executes ruff, black, mypy, pytest
- **publish.yml**: Publishes to PyPI on release tags
- **publish-testpypi.yml**: Publishes to TestPyPI from dev branch
- **docs.yml**: Deploys MkDocs documentation

All code must pass quality gates before merge:
```bash
ruff check .
black --check .
isort --check-only .
python -m mypy --config-file pyproject.toml
pytest --maxfail=1 --disable-warnings -q
```

## Configuration Files

- **pyproject.toml**: Project metadata, dependencies, tool configs (black, ruff, mypy, pytest)
- **src/glitchlings/config.toml**: Runtime configuration for lexicon priority
- **YAML attack configs** (e.g., `experiments/chaos.yaml`): Version-controlled glitchling configurations loaded via `load_attack_config()`

## Important Notes

- **Never break determinism**: Glitchlings must produce identical output for same seed+input
- **Respect the RNG contract**: Each glitchling owns its Random instance; never use Python's global random
- **Maintain Rust/Python parity**: If modifying a glitchling with Rust implementation, update both and verify with tests
- **Test both pipelines**: Run pytest normally AND with `GLITCHLINGS_RUST_PIPELINE=0`
- **CLI changes require README update**: Run `python docs/build_cli_reference.py` after modifying CLI

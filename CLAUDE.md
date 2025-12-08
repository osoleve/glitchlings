# CLAUDE.md - AI Assistant Guide for Glitchlings

## Project Overview

Glitchlings is a Python library (with a Rust acceleration layer) for **deterministic, linguistically-principled text corruption**. It provides "glitchlings" - composable text transformers that introduce controlled noise into text inputs for language model testing and training.

**Repository:** https://github.com/osoleve/glitchlings
**Python:** 3.10+
**License:** Apache-2.0

### Core Purpose

- Test model robustness against real-world text corruption patterns
- Generate adversarial augmentations for training more generalizable models
- Provide deterministic, reproducible text transformations

## Quick Reference Commands

```bash
# Install for development
pip install -e .[dev]

# Quality gates (run all before committing)
ruff check src                                  # Lint
ruff format src                                 # Format
python -m mypy src                              # Type check
uv build                                        # Build (including Rust)
pytest                                          # Tests

# Rebuild Rust extension after changes
uv build -Uq

# Regenerate documentation
python -m glitchlings.dev.docs
```

## Repository Structure

```
src/glitchlings/
├── __init__.py          # Public API exports
├── __main__.py          # CLI entry: python -m glitchlings
├── main.py              # CLI implementation
├── auggie.py            # Fluent builder API
├── constants.py         # Default values (pure)
├── runtime_config.py    # Runtime configuration
├── zoo/                 # Glitchling implementations
│   ├── core.py          # Glitchling/Gaggle base classes (impure)
│   ├── core_planning.py # Execution planning (pure)
│   ├── core_execution.py# Rust pipeline dispatch (impure)
│   ├── corrupt_dispatch.py # Result assembly (pure)
│   ├── validation.py    # Parameter validation (pure)
│   ├── transforms.py    # Text tokenization/utilities (pure)
│   ├── rng.py           # Seed/RNG helpers (pure)
│   ├── typogre.py       # Character-level typos
│   ├── mim1c.py         # Unicode confusables
│   ├── wherewolf.py     # Homophone substitution
│   ├── hokey.py         # Word stretching
│   ├── jargoyle.py      # Synonym replacement
│   ├── rushmore.py      # Word drop/dup/swap
│   ├── redactyl.py      # Word redaction
│   ├── scannequin.py    # OCR-style errors
│   ├── zeedub.py        # Zero-width characters
│   └── pedant/          # Grammar pedantry
├── attack/              # Tokenization & metrics
│   ├── core.py          # Attack orchestrator (impure)
│   ├── compose.py       # Result assembly (pure)
│   ├── encode.py        # Encoding utilities (pure)
│   └── metrics_dispatch.py # Metric dispatch (pure)
├── conf/                # Configuration system
│   ├── types.py         # Dataclasses (pure)
│   ├── loaders.py       # YAML loading (impure)
│   └── schema.py        # Schema definitions
├── util/                # Shared utilities
│   ├── keyboards.py     # Keyboard layouts
│   └── transcripts.py   # Transcript handling
├── compat/              # Optional dependency loading
│   ├── types.py         # Type definitions (pure)
│   └── loaders.py       # Lazy imports (impure)
├── internal/            # Rust FFI layer
│   ├── rust.py          # FFI loader (impure)
│   └── rust_ffi.py      # Rust wrappers (impure)
├── dlc/                 # Optional integrations
│   ├── prime.py         # Prime Intellect/verifiers
│   ├── pytorch.py       # PyTorch datasets
│   ├── huggingface.py   # HF datasets
│   └── gutenberg.py     # Gutenberg corpus
├── dev/                 # Development tools
│   └── docs.py          # Doc generation
└── assets/              # Bundled data files
    └── lexemes/         # Word lists

rust/zoo/               # Rust extension (PyO3)
tests/                  # Pytest suite
├── core/               # Core functionality tests
├── attack/             # Attack module tests
├── cli/                # CLI tests
├── zoo/                # Individual glitchling tests
└── dlc/                # DLC integration tests
docs/                   # MkDocs documentation
benchmarks/             # Performance benchmarks
examples/               # Usage examples
```

## Public API

The main exports from `glitchlings`:

```python
# Core classes
from glitchlings import Glitchling, Gaggle, Auggie

# All glitchlings
from glitchlings import (
    Typogre, Mim1c, Wherewolf, Hokey, Jargoyle,
    Rushmore, Redactyl, Scannequin, Zeedub, Pedant
)

# Attack analysis
from glitchlings import Attack, AttackResult

# Configuration
from glitchlings import AttackConfig, load_attack_config, build_gaggle

# Utilities
from glitchlings import SAMPLE_TEXT, TranscriptTarget, summon
```

## Functional Purity Architecture

**Critical for AI assistants:** The codebase strictly separates pure and impure code. This is enforced by `tests/core/test_purity_architecture.py`.

### Pure Modules (no side effects, trust inputs)

| Module | Purpose |
|--------|---------|
| `zoo/validation.py` | Parameter validation/normalization |
| `zoo/transforms.py` | Text tokenization, word splitting |
| `zoo/rng.py` | Seed resolution, RNG helpers |
| `zoo/core_planning.py` | Execution plan construction |
| `zoo/corrupt_dispatch.py` | Result assembly |
| `compat/types.py` | Type definitions |
| `conf/types.py` | Configuration dataclasses |
| `constants.py` | Default values |
| `attack/compose.py` | Result assembly |
| `attack/encode.py` | Encoding utilities |
| `attack/metrics_dispatch.py` | Metric dispatch |

### Impure Modules (side effects allowed)

- `internal/rust.py`, `internal/rust_ffi.py` - Rust FFI
- `compat/loaders.py` - Optional dependency loading
- `conf/loaders.py` - File I/O, caching
- `zoo/core.py`, `zoo/core_execution.py` - Orchestration
- `attack/core.py`, `attack/tokenization.py`, `attack/metrics.py`

### Key Rules

1. **Pure modules**: Trust inputs are already validated. Do NOT add defensive `None` checks or re-validation.

2. **Boundary validation**: Validate once at entry points (`__init__`, CLI parsing, config loading).

3. **Import restrictions**: Pure modules cannot import from impure modules.

```python
# CORRECT: Validate at boundary, trust inside
class MyGlitchling(Glitchling):
    def __init__(self, *, rate: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.rate = clamp_rate(rate)  # boundary validation

    def _transform(self, text: str) -> str:
        # Trust self.rate is valid - no defensive checks
        return apply_transformation(text, self.rate)

# WRONG: Defensive checks inside pure function
def apply_transformation(text: str, rate: float) -> str:
    if rate is None:  # DON'T DO THIS
        rate = 0.1
    ...
```

## Creating New Glitchlings

Every new glitchling must:

1. **Subclass `Glitchling`** with proper `scope` and `order` via `AttackWave`/`AttackOrder`
2. **Accept keyword-only parameters** in `__init__`, forwarding through `super().__init__`
3. **Use instance RNG** via `zoo.rng` helpers - never global `random` state
4. **Provide `pipeline_operation`** descriptor when Rust can accelerate (return `None` for Python-only)
5. **Preserve transcript targeting** by routing through `Glitchling.corrupt`

```python
from glitchlings.zoo.core import Glitchling, AttackWave, AttackOrder
from glitchlings.zoo.validation import clamp_rate

class NewGlitchling(Glitchling):
    scope = AttackWave.WORD
    order = AttackOrder.SUBSTITUTE

    def __init__(self, *, rate: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.rate = clamp_rate(rate)

    @property
    def pipeline_operation(self):
        return None  # or pipeline descriptor for Rust

    def _corrupt(self, text: str) -> str:
        # Implementation using self.rng for randomness
        ...
```

## Determinism Requirements

All glitchlings must be deterministic given the same seed:

- Derive RNGs from `Gaggle.derive_seed` and `zoo.rng` helpers
- Stabilize candidate ordering before sampling
- Preserve transcript turn ordering and pattern masks
- Expose configurable parameters via `set_param` for test fixtures

## Quality Gates

Run these before every commit:

```bash
ruff check src                                   # Lint (must pass)
ruff format src                                  # Format (must pass)
python -m mypy src                               # Type check (must pass)
uv build                                         # Build (must succeed)
pytest                                           # Tests (must pass)
```

Pre-commit hooks run automatically if installed via `pre-commit install`.

## CLI Reference

```bash
glitchlings --list                    # List available glitchlings
glitchlings --help                    # Full CLI help
glitchlings -g typogre "text"         # Apply single glitchling
glitchlings -g "Typogre(rate=0.05)" "text"  # With parameters
glitchlings --config chaos.yaml "text"     # From config file
glitchlings --file input.txt --diff        # File input with diff
glitchlings --attack json --sample         # Summary with metrics
glitchlings --report json --sample         # Full report with tokens
```

## Test Structure

Key test files:

- `tests/core/test_purity_architecture.py` - Enforces pure/impure separation
- `tests/core/test_glitchlings_determinism.py` - Determinism guarantees
- `tests/core/test_core_planning.py` - Plan building
- `tests/core/test_corrupt_dispatch.py` - Transcript targeting
- `tests/core/test_hybrid_pipeline.py` - Rust/Python parity
- `tests/attack/test_attack.py` - Attack orchestration
- `tests/cli/test_cli.py` - CLI contract

Run specific tests:

```bash
pytest tests/core/test_purity_architecture.py -v  # Check architecture
pytest tests/core/test_glitchlings_determinism.py # Check determinism
pytest -k "test_typogre"                          # Pattern matching
```

## Rust Extension

The Rust extension (`rust/zoo/`) accelerates core operations:

- Rebuild after changes: `uv build -Uq`
- The Rust backend must import cleanly - no Python-only fallback mode
- Keep signatures synchronized with Python shims
- Test parity via `tests/core/test_hybrid_pipeline.py`

## Documentation

- Update `README.md`, `docs/index.md`, per-glitchling pages when behaviors change
- Regenerate generated docs: `python -m glitchlings.dev.docs`
- Generated files: `docs/cli.md`, `docs/monster-manual.md`, `docs/glitchling-gallery.md`

## Common Patterns

### Pattern Masking

Protect or target specific text regions:

```python
# Exclude patterns (protect from corruption)
typo = Typogre(rate=0.1, exclude_patterns=[r"<[^>]+>"])

# Include only patterns (corrupt only matched regions)
typo = Typogre(rate=0.5, include_only_patterns=[r"`[^`]+`"])
```

### Gaggle Usage

```python
from glitchlings import Gaggle, Typogre, Mim1c

gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)
result = gaggle("input text")
```

### Fluent Builder

```python
from glitchlings import Auggie

auggie = (
    Auggie(seed=404)
    .typo(rate=0.015)
    .confusable(rate=0.01)
    .homophone(rate=0.02)
)
result = auggie("input text")
```

## Avoid These Mistakes

1. **Don't add defensive code in pure modules** - trust validated inputs
2. **Don't use global `random` state** - use instance RNG via `zoo.rng`
3. **Don't import impure modules from pure modules** - architecture tests will fail
4. **Don't skip Rust rebuild** after `rust/zoo/` changes
5. **Don't break determinism** - sort before shuffle/sample, stabilize indices
6. **Don't over-engineer** - make only requested changes, keep solutions simple

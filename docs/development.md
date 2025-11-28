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

3. Install the git hooks so the shared formatting, linting, and type checks run automatically:

   ```bash
   pre-commit install
   ```

## Run the test suite

Execute the automated tests from the repository root:

```bash
pytest
```

The suite covers determinism guarantees, dataset integrations, and the compiled Rust implementation that now backs orchestration.

## Automated checks

Run the shared quality gates before opening a pull request:

```bash
ruff check .
python -m mypy --config-file pyproject.toml src
uv build
pytest
```

## Additional tips

- Rebuild the Rust extension after editing files under `rust/zoo/`:

  ```bash
  uv build -Uq
  ```

- Regenerate the CLI reference page, Monster Manual (both repo root and docs site copies), and glitchling gallery together with:

  ```bash
  python -m glitchlings.dev.docs
  # or, once installed: glitchlings-refresh-docs
  ```

## Functional Purity Architecture

The codebase follows a layered architecture that separates **pure** (deterministic, side-effect-free) code from **impure** (stateful, side-effectful) code, and requires all defensive coding to occur at **module boundaries** instead of all throughout. This pattern improves maintainability, testability, and clarity, especially when working with AI coding agents that tend to add defensive checks everywhere.

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
| `zoo/transforms.py` | Pure | Text tokenization, keyboard processing, string diffs, word splitting |
| `zoo/rng.py` | Pure | Seed resolution, hierarchical derivation |
| `compat/types.py` | Pure | Type definitions for optional dependency loading |
| `conf/types.py` | Pure | Configuration dataclasses (RuntimeConfig, AttackConfig) |
| `constants.py` | Pure | Centralized default values and constants |
| `attack/compose.py` | Pure | Result assembly helpers |
| `attack/encode.py` | Pure | Tokenization helpers |
| `attack/metrics_dispatch.py` | Pure | Metric dispatch logic |
| `internal/rust.py` | Impure | Low-level Rust FFI loader and primitives |
| `internal/rust_ffi.py` | Impure | Centralized Rust operation wrappers (preferred) |
| `compat/loaders.py` | Impure | Optional dependency lazy loading machinery |
| `conf/loaders.py` | Impure | Configuration file loading, caching, Gaggle construction |

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
# In validation.py (boundary layer)
def validate_rate(rate: float | None) -> float:
    if rate is None:
        raise ValueError("rate cannot be None")
    if not isinstance(rate, (int, float)):
        raise TypeError("rate must be numeric")
    if math.isnan(rate):
        return 0.0
    return max(0.0, min(1.0, float(rate)))

# In typogre.py (uses boundary layer, trusts result)
def fatfinger(text: str, rate: float, ...) -> str:
    # rate is already validated - just use it
    return _fatfinger_rust(text, rate, layout, seed, shift_slip_rate=slip_rate, shift_map=shift_map)
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

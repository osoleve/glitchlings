# Glitchlings - AGENTS.md

## Work Tracking

1. Install the [Beads `bd` CLI](https://github.com/steveyegge/beads) in every environment before writing code. The project ships prebuilt binaries—download the latest release (e.g. `curl -L https://github.com/steveyegge/beads/releases/download/v0.20.1/beads_0.20.1_linux_amd64.tar.gz -o beads.tar.gz && tar -xzf beads.tar.gz`) and move the `bd` executable onto `$PATH` (for example, `install -m 0755 bd /usr/local/bin/bd`). Verify the install with `bd version`. If `bd` is missing from the environment, you are expected—and explicitly allowed—to install it.
2. Run `bd quickstart` once after installation to review the workflow commands and confirm the CLI is operational.
3. Bootstrap new clones with `bd init --quiet` from the repository root; this keeps `.beads/` synchronised and ready for the agent workflow.
4. **Before starting any coding task, create or update a bead describing the scope, mark it `in_progress` while you work, and capture completion details in the same bead before finishing.** Use the CLI (`bd create`, `bd update`, `bd close`) instead of editing JSON by hand—beads are the source of truth for ongoing work.
5. Confirm the editable install succeeds with `pip install -e .[dev]` before making changes—this primes the tooling stack and validates that the repository builds cleanly.

## Quality Gates

After completing a task, always:

1. Lint with `ruff`
2. Type check `src/`  with `mypy`
3. Build the project with `uv`
4. Run tests with `pytest`

## Repository Tour

- **`src/glitchlings/`** - Installable Python package.
  - `__init__.py` exposes the public API (glitchlings, `Gaggle`, `summon`, `SAMPLE_TEXT`).
  - `__main__.py` wires `python -m glitchlings` to the CLI entry point in `main.py`.
  - `main.py` implements the CLI: parser construction, text sourcing, glitchling summoning, and optional diff output.
- **`src/glitchlings/zoo/`** - Core glitchling implementations.
  - `core.py` defines the `Glitchling` base class, `AttackWave`/`AttackOrder` enums, deterministic seed derivation, and the Rust pipeline bridge.
  - `typogre.py`, `mim1c.py`, `rushmore.py`, `redactyl.py`, `jargoyle.py`, `scannequin.py`, and `zeedub.py` provide concrete glitchlings. Word-level agents accept the canonical `rate` parameter and expose the `unweighted` toggle, with Rushmore covering duplication and adjacent swap modes.
- **`src/glitchlings/util/`** - Shared helpers including `SAMPLE_TEXT`, keyboard-neighbour layouts, diff utilities, and rate parsing helpers.
- **`src/glitchlings/lexicon/`** - Bundled synonym backends. The default config (`src/glitchlings/config.toml`) prioritises the shipped vector cache (`lexicon/data/default_vector_cache.json`), then optional graph caches, and finally WordNet when installed.
- **`src/glitchlings/dlc/prime/`** - Optional DLC integration with the `verifiers` environments (install via `pip install -e .[prime]`).
- **`benchmarks/`** - Performance harnesses (`pipeline_benchmark.py`, etc.) that exercise both the Python and Rust execution paths.
- **`docs/`** - Field guide, development notes, release process, and per-glitchling reference pages. Changes to behaviour should update the relevant doc alongside code.
- **`rust/`** - PyO3 crates that implement the required Rust backend.
  - `rust/zoo/` builds `glitchlings._zoo_rust` (fast paths for Typogre, Mim1c, Reduple, Rushmore, Redactyl, and Scannequin). Use `maturin develop -m rust/zoo/Cargo.toml` after touching Rust sources.
- **`tests/`** - Pytest suite covering determinism, dataset integrations, CLI behaviour, Rust parity, and DLC hooks.
  - Highlights: `test_glitchling_core.py` (Gaggle orchestration and feature flags), `test_parameter_effects.py` (argument coverage), `test_benchmarks.py` (pipeline smoke tests), `test_prime_echo_chamber.py` (Prime DLC), and `test_rust_backed_glitchlings.py` (parity checks).

## Coding Conventions

- Target **Python 3.10+** (see `pyproject.toml`).
- Follow the import order used in the package: standard library, third-party, then local modules.
- Every new glitchling must:
  - Subclass `Glitchling`, setting `scope` and `order` via `AttackWave` / `AttackOrder` from `core.py`.
  - Accept keyword-only parameters in `__init__`, forwarding them through `super().__init__` so they are tracked by `set_param`.
  - Drive all randomness through the instance's `rng` (do not rely on module-level RNG state) to keep `Gaggle` runs deterministic.
  - Provide a `pipeline_operation` descriptor when the Rust pipeline can accelerate the behaviour; return `None` when only the Python path is valid.
- Keep helper functions small and well-scoped; include docstrings that describe behaviour and note any determinism considerations.
- When mutating token sequences, preserve whitespace and punctuation via separator-preserving regex splits (see `rushmore.py`, `redactyl.py`).
- CLI work should continue the existing UX: validate inputs with `ArgumentParser.error`, keep deterministic output ordering, and gate optional behaviours behind explicit flags.
- Treat Rust failures as fatal: the compiled backend must import cleanly, surface identical signatures, and stay in lockstep with the Python shims.

## Testing & Tooling

- Run the full suite with `pytest` from the repository root.

## Determinism Checklist

- Expose configurable parameters via `set_param` so fixtures in `tests/test_glitchlings_determinism.py` can reset seeds predictably.
- Derive RNGs from the enclosing context (`Gaggle.derive_seed`) instead of using global state.
- When sampling subsets (e.g., replacements or deletions), stabilise candidate ordering before selecting to keep results reproducible.

## Workflow Tips

- The CLI lists built-in glitchlings (`glitchlings --list`) and can show diffs; update `BUILTIN_GLITCHLINGS` and help text when introducing new creatures.
- Keep documentation synchronised: update `README.md`, `docs/index.md`, per-glitchling reference pages, and `MONSTER_MANUAL.md` when behaviours or defaults change.
- When editing keyboard layouts or homoglyph mappings, ensure downstream consumers continue to work with lowercase keys (`util.KEYNEIGHBORS`).
- Verify the Rust backend builds in every environment (CI, local, release) and fix import errors immediately—there is no supported Python-only mode anymore.

## Functional Purity Architecture

The codebase explicitly separates **pure** (functionally deterministic) code from **impure** (side-effectful) code. This architecture discourages AI agents from adding unnecessary defensive code by keeping validation and transformation concerns separate. See `docs/development.md` for the full specification.

### Pure Modules (No Side Effects)

These modules contain only pure functions—same inputs always produce same outputs:

| Module | Purpose |
|--------|---------|
| `zoo/validation.py` | Parameter validation and normalization |
| `zoo/transforms.py` | Text tokenization and transformation utilities |
| `zoo/rng.py` | Seed resolution and RNG helpers |
| `zoo/_text_utils.py` | Text splitting and joining utilities |
| `compat/types.py` | Pure type definitions for optional dependency loading |

**When writing code in pure modules:**

- Trust that inputs are already validated—do NOT add defensive `None` checks
- Do NOT import from impure modules (`internal/rust.py`, `compat/loaders.py`, `config.py`)
- Do NOT use `random.Random()` instantiation—accept pre-computed random values
- Do NOT catch exceptions around trusted internal calls
- Use only standard library imports

### Impure Modules (Side Effects Allowed)

These modules handle IO, FFI, and mutable state:

- `internal/rust.py` — Low-level Rust FFI loader and primitives
- `internal/rust_ffi.py` — Centralized Rust operation wrappers (preferred entry point for FFI)
- `compat/loaders.py` — Optional dependency loading with lazy import machinery
- `config.py`, `runtime_config.py` — Configuration loading/caching
- `lexicon/` — Cache file IO

### Boundary Layer Pattern

Validation belongs at **module boundaries** where untrusted input enters:

- CLI argument parsing (`main.py`)
- Public API entry points (`Glitchling.__init__`, `Attack.__init__`)
- Configuration loaders

Use `zoo/validation.py` functions at these boundaries:

```python
# ✅ Correct: validate at boundary, trust inside
class MyGlitchling(Glitchling):
    def __init__(self, *, rate: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.rate = clamp_rate(rate)  # boundary validation

    def _transform(self, text: str) -> str:
        # Trust self.rate is valid—no defensive checks here
        return apply_transformation(text, self.rate)
```

```python
# ❌ Wrong: defensive checks inside transformation
def apply_transformation(text: str, rate: float) -> str:
    if rate is None:  # DON'T DO THIS
        rate = 0.1
    if not 0 <= rate <= 1:  # DON'T DO THIS
        raise ValueError("rate out of range")
    ...
```

### RNG Handling

For deterministic behaviour, accept seeds or pre-computed random values instead of RNG objects:

```python
# ✅ Pure function: accepts pre-computed value
def select_word(words: list[str], random_index: int) -> str:
    return words[random_index]

# ✅ Boundary: resolves seed, generates random values
def corrupt(self, text: str) -> str:
    seed = resolve_seed(self.seed, text)
    rng = create_rng(seed)
    index = sample_random_index(rng, len(words))
    return select_word(words, index)
```

### How to Recognize Module Layers

When adding new code, check which layer the file belongs to:

1. **Pure modules** (`zoo/validation.py`, `zoo/transforms.py`, `zoo/rng.py`): Trust inputs, no side effects
2. **Boundary modules** (`main.py`, `__init__` methods): Validate thoroughly once
3. **Impure modules** (`internal/rust.py`, `compat.py`): Side effects allowed

The test suite in `tests/test_purity_architecture.py` enforces import conventions automatically.

# Glitchlings - AGENTS.md

## Work Tracking

1. Install the [Beads `bd` CLI](https://github.com/steveyegge/beads) in every environment before writing code. The project ships prebuilt binaries; download the latest release (for example, `curl -L https://github.com/steveyegge/beads/releases/download/v0.20.1/beads_0.20.1_linux_amd64.tar.gz -o beads.tar.gz && tar -xzf beads.tar.gz`) and move the `bd` executable onto `$PATH` (for example, `install -m 0755 bd /usr/local/bin/bd`). Verify the install with `bd version`. If `bd` is missing from the environment, you are expected and explicitly allowed to install it.
2. Run `bd quickstart` once after installation to review the workflow commands and confirm the CLI is operational.
3. Bootstrap new clones with `bd init --quiet` from the repository root; this keeps `.beads/` synchronised and ready for the agent workflow.
4. **Before starting any coding task, create or update a bead describing the scope, mark it `in_progress` while you work, and capture completion details in the same bead before finishing.** Use the CLI (`bd create`, `bd update`, `bd close`) instead of editing JSON by hand; beads are the source of truth for ongoing work.
5. Confirm the editable install succeeds with `pip install -e .[dev]` (use `.[dev,prime]` when working on the Prime DLC) before making changes; this primes the tooling stack and validates that the repository builds cleanly.

## Quality Gates

After completing a task, always:

1. Lint with `ruff check .`
2. Type check `src/` with `python -m mypy --config-file pyproject.toml src`
3. Build the project with `uv build`
4. Run tests with `pytest`

## Repository Tour

- **`src/glitchlings/`** - Package entry point and CLI wiring.
  - `__init__.py` exposes the public API (Auggie builder, glitchlings, `Gaggle`, `summon`, `AttackConfig` helpers, `SAMPLE_TEXT`, `TranscriptTarget`).
  - `__main__.py` routes `python -m glitchlings` to the CLI entry point in `main.py`.
  - `main.py` implements the CLI: parser construction, attack config loading, glitchling summoning, and optional diff/report output.
  - `auggie.py` provides the fluent roster builder; `constants.py`/`runtime_config.py` hold defaults.
- **`src/glitchlings/attack/`** - Attack orchestrator and tokenization/metrics helpers.
  - `core.py` defines `Attack`, `AttackResult`, and tokenizer/metric resolution.
  - `compose.py`, `encode.py`, and `metrics_dispatch.py` are pure helpers used by the reports.
  - `tokenization.py` and `metrics.py` handle impure tokenizer loading and Rust metric bridges.
- **`src/glitchlings/zoo/`** - Core glitchling implementations and orchestration.
  - `core.py` houses `Glitchling`/`Gaggle`, dataset helpers, transcript targeting, and pipeline caching.
  - `core_planning.py` (pure) builds execution plans and normalises pipeline descriptors; `core_execution.py` dispatches plans through the Rust pipeline or Python fallbacks.
  - `corrupt_dispatch.py` (pure) resolves transcript targets and assembles corruption results; `rng.py` handles seed derivation.
  - Glitchlings: Typogre, Hokey, Mim1c, Ekkokin, Pedant (`zoo/pedant/`), Jargoyle, Rushmore (duplication/adjacent swap/zero-width), Redactyl, Scannequin, Zeedub.
- **`src/glitchlings/util/`** - Shared helpers including `SAMPLE_TEXT`, keyboard neighbour and shift maps, transcript helpers, adapters, and diff utilities.
- **`src/glitchlings/assets/`** - Bundled data (homoglyphs, homophones, Hokey assets, OCR confusions, pipeline assets) plus lexeme dictionaries under `lexemes/` (synonyms, colors, corporate, academic, cyberpunk, lovecraftian).
- **`src/glitchlings/conf/`** - Configuration schema, dataclasses, and loaders for YAML attack configs.
- **`src/glitchlings/compat/`** - Optional dependency loaders (datasets, tokenizers, PyTorch, Lightning, Hugging Face).
- **`src/glitchlings/dev/`** - Doc refresh helpers (`python -m glitchlings.dev.docs` / `glitchlings-refresh-docs`).
- **`src/glitchlings/dlc/prime/`** - Optional DLC integration with the `verifiers` environments and Prime/HF connectors.
- **`benchmarks/`** - Performance harnesses (`pipeline_benchmark.py`) covering Python and Rust execution paths.
- **`docs/`** - Field guide, development notes, CLI/Attack/config docs, and generated references (`cli.md`, `configuration.md`, `attack.md`, `monster-manual.md`, `glitchling-gallery.md`). Regenerate generated pages with `python -m glitchlings.dev.docs`.
- **`tests/`** - Pytest suite covering orchestration, determinism, DLC hooks, CLI, and Rust parity.
  - Highlights: `tests/core/test_core_planning.py` (plan building/pipeline descriptors), `tests/core/test_corrupt_dispatch.py` (transcript targeting), `tests/attack/test_attack.py` (Attack orchestration, tokenization, metrics), `tests/core/test_hybrid_pipeline.py` (Rust pipeline parity), `tests/cli/test_cli.py` (CLI contract), `tests/dlc/test_prime_echo_chamber.py` (Prime DLC), `tests/core/test_parameter_effects.py` (argument coverage).

## Coding Conventions

- Target **Python 3.10+** (see `pyproject.toml`).
- Follow the import order used in the package: standard library, third-party, then local modules.
- Every new glitchling must:
  - Subclass `Glitchling`, setting `scope` and `order` via `AttackWave` / `AttackOrder` from `core.py`.
  - Accept keyword-only parameters in `__init__`, forwarding them through `super().__init__` so they are tracked by `set_param`.
  - Drive all randomness through the instance's RNG and the boundary helpers in `zoo.rng`; do not rely on module-level RNG state.
  - Provide a `pipeline_operation` descriptor when the Rust pipeline can accelerate the behaviour (use `build_pipeline_descriptor` helpers when applicable); return `None` when only the Python path is valid.
  - Preserve transcript targeting and pattern masking by routing corruption through `Glitchling.corrupt` rather than bypassing it.
- Keep helper functions small and well-scoped; include docstrings that describe behaviour and note any determinism considerations.
- When mutating token sequences, preserve whitespace and punctuation via separator-preserving regex splits (see `zoo/transforms.py`).
- CLI work should continue the existing UX: validate inputs with `ArgumentParser.error`, keep deterministic output ordering, and gate optional behaviours behind explicit flags.
- Treat Rust failures as fatal: the compiled backend must import cleanly, surface identical signatures, and stay in lockstep with the Python shims.

## Testing & Tooling

- Run the full suite with `pytest` from the repository root.

## Determinism Checklist

- Expose configurable parameters via `set_param` so fixtures in `tests/test_glitchlings_determinism.py` can reset seeds predictably.
- Derive RNGs from the enclosing context (`Gaggle.derive_seed` and helpers in `zoo.rng`) instead of using global state.
- Keep pipeline descriptors and plan inputs deterministic (avoid unordered mappings, normalise layouts before returning).
- When sampling subsets (e.g., replacements or deletions), stabilise candidate ordering before selecting to keep results reproducible.
- Preserve transcript turn ordering and pattern masks when assembling results (use `corrupt_dispatch` helpers where appropriate).

## Workflow Tips

- The CLI lists built-in glitchlings (`glitchlings --list`) and can show diffs; update `BUILTIN_GLITCHLINGS` and help text when introducing new creatures.
- Keep documentation synchronised: update `README.md`, `docs/index.md`, per-glitchling reference pages, `MONSTER_MANUAL.md`, and generated docs (`docs/cli.md`, `docs/monster-manual.md`, `docs/glitchling-gallery.md`) when behaviours or defaults change. Regenerate generated pages via `python -m glitchlings.dev.docs` or `glitchlings-refresh-docs`.
- When editing keyboard layouts or homoglyph mappings, ensure downstream consumers continue to work with lowercase keys (`util.KEYNEIGHBORS`).
- Rebuild the Rust extension after touching `rust/zoo/` (e.g., `uv build -Uq`). Verify the Rust backend builds in every environment (CI, local, release) and fix import errors immediately - there is no supported Python-only mode anymore.

## Functional Purity Architecture

The codebase explicitly separates **pure** (functionally deterministic) code from **impure** (side-effectful) code. This architecture discourages AI agents from adding unnecessary defensive code by keeping validation and transformation concerns separate. See `docs/development.md` for the full specification.

### Pure Modules (No Side Effects)

These modules contain only pure functions - same inputs always produce same outputs:

| Module | Purpose |
|--------|---------|
| `zoo/validation.py` | Parameter validation and normalization |
| `zoo/transforms.py` | Text tokenization, transformation utilities, word splitting |
| `zoo/rng.py` | Seed resolution and RNG helpers |
| `zoo/core_planning.py` | Orchestration plan construction and pipeline descriptor normalization |
| `zoo/corrupt_dispatch.py` | Transcript target resolution and result assembly scaffolding |
| `compat/types.py` | Pure type definitions for optional dependency loading |
| `conf/types.py` | Pure dataclass definitions for configuration (RuntimeConfig, AttackConfig) |
| `constants.py` | Centralized default values and constants (no I/O operations) |
| `attack/compose.py` | Pure result assembly for Attack (extract_transcript_contents, build_*_result) |
| `attack/encode.py` | Pure encoding utilities (encode_single, encode_batch, describe_tokenizer) |
| `attack/metrics_dispatch.py` | Pure metric dispatch logic (is_batch, validate_batch_consistency) |

**When writing code in pure modules:**

- Trust that inputs are already validated - do NOT add defensive `None` checks
- Do NOT import from impure modules (`internal/rust.py`, `compat/loaders.py`, `conf/loaders.py`, `attack/core.py`, `attack/tokenization.py`, `attack/metrics.py`, `zoo/core.py`, `zoo/core_execution.py`)
- Do NOT use `random.Random()` instantiation - accept pre-computed random values
- Do NOT catch exceptions around trusted internal calls
- Use only standard library imports or other pure modules

### Impure Modules (Side Effects Allowed)

These modules handle IO, FFI, and mutable state:

- `internal/rust.py` / `internal/rust_ffi.py` - Low-level Rust FFI loader and primitives
- `compat/loaders.py` - Optional dependency loading with lazy import machinery
- `conf/loaders.py` - Configuration file loading, caching, and Gaggle construction
- `zoo/core.py` / `zoo/core_execution.py` - Glitchling orchestration, transcript-aware corruption, Rust pipeline execution
- `attack/core.py` - Attack orchestrator (coordinates impure operations)
- `attack/tokenization.py` / `attack/metrics.py` - Tokenizer resolution and Rust metric loading

### Boundary Layer Pattern

Validation belongs at **module boundaries** where untrusted input enters:

- CLI argument parsing (`main.py`)
- Public API entry points (`Glitchling.__init__`, `Attack.__init__`)
- Configuration loaders and orchestration bridges (`conf/`, `zoo/core.py`)

Use `zoo/validation.py` functions at these boundaries:

```python
# Correct: validate at boundary, trust inside
class MyGlitchling(Glitchling):
    def __init__(self, *, rate: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.rate = clamp_rate(rate)  # boundary validation

    def _transform(self, text: str) -> str:
        # Trust self.rate is valid - no defensive checks here
        return apply_transformation(text, self.rate)
```

```python
# Wrong: defensive checks inside transformation
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
# Pure function: accepts pre-computed value
def select_word(words: list[str], random_index: int) -> str:
    return words[random_index]

# Boundary: resolves seed, generates random values
def corrupt(self, text: str) -> str:
    seed = resolve_seed(self.seed, self.rng)
    rng = random.Random(seed)
    index = rng.randrange(len(words))
    return select_word(words, index)
```

### How to Recognize Module Layers

When adding new code, check which layer the file belongs to:

1. **Pure modules** (`zoo/validation.py`, `zoo/transforms.py`, `zoo/rng.py`, `zoo/core_planning.py`, `zoo/corrupt_dispatch.py`, `compat/types.py`, `conf/types.py`, `constants.py`, `attack/compose.py`, `attack/encode.py`, `attack/metrics_dispatch.py`): trust inputs, no side effects
2. **Boundary modules** (`main.py`, `__init__` methods, `zoo/core.py`, `attack/core.py`): validate thoroughly once
3. **Impure modules** (`internal/rust.py`, `compat/loaders.py`, `conf/loaders.py`, `attack/tokenization.py`, `attack/metrics.py`, `zoo/core_execution.py`): side effects allowed

The test suite in `tests/core/test_purity_architecture.py` enforces import conventions automatically.

# Glitchlings - AGENTS.md

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
  - `core_planning.py` (pure) builds attack plans; `core_execution.py` executes plans through tokenizers and glitchlings.
  - `analysis.py` provides `SeedSweep`, `GridSearch`, and `TokenizerComparison` tools for parameter exploration.
  - `compose.py`, `encode.py`, and `metrics_dispatch.py` are pure helpers used by the reports.
  - `tokenization.py` and `metrics.py` handle impure tokenizer loading and Rust metric bridges.
  - `tokenizer_metrics.py` provides tokenizer analysis metrics (compression ratio, vocabulary coverage).
- **`src/glitchlings/zoo/`** - Core glitchling implementations and orchestration.
  - `core.py` houses `Glitchling`/`Gaggle`, dataset helpers, transcript targeting, and pipeline caching.
  - `core_planning.py` (pure) builds execution plans and normalises pipeline descriptors; `core_execution.py` dispatches plans through the Rust pipeline or Python fallbacks.
  - `corrupt_dispatch.py` (pure) resolves transcript targets and assembles corruption results; `rng.py` handles seed derivation.
  - Glitchlings: Typogre, Hokey, Mim1c, Wherewolf, Pedant (`zoo/pedant/`), Jargoyle, Rushmore (duplication/adjacent swap/zero-width), Redactyl, Scannequin, Zeedub.
- **`src/glitchlings/util/`** - Shared helpers including `SAMPLE_TEXT`, keyboard neighbour and shift maps, transcript helpers, and diff utilities.
  - `adapters.py` provides `coerce_gaggle()` for normalizing glitchling inputs across DLC integrations.
- **`src/glitchlings/protocols.py`** - Protocol definitions for dependency inversion (e.g., `Corruptor` protocol allows attack module to work with glitchlings without circular imports).
- **`src/glitchlings/assets/`** - Bundled data (homoglyphs, homophones, Hokey assets, OCR confusions, pipeline assets) plus lexeme dictionaries under `lexemes/` (synonyms, colors, corporate, academic, cyberpunk, lovecraftian).
- **`src/glitchlings/conf/`** - Configuration schema, dataclasses, and loaders for YAML attack configs.
- **`src/glitchlings/compat/`** - Optional dependency loaders (datasets, tokenizers, PyTorch, Lightning, Hugging Face).
- **`src/glitchlings/dev/`** - Doc refresh helpers (`python -m glitchlings.dev.docs` / `glitchlings-refresh-docs`).
- **`src/glitchlings/dlc/`** - Optional DLC integrations.
  - `_shared.py` provides shared utilities for dataset column resolution and batch corruption.
  - `prime.py` integrates with the `verifiers` environments and Prime/HF connectors.
  - `pytorch.py` and `pytorch_lightning.py` provide PyTorch Dataset/DataModule wrappers.
  - `huggingface.py` wraps Hugging Face datasets with corruption transforms.
  - `langchain.py` provides LangChain integration helpers.
  - `nemo.py` provides NVIDIA NeMo DataDesigner column generator plugin.
  - `gutenberg.py` provides access to the Gutenberg corpus.
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

## Rust Extension

The Rust extension (`rust/zoo/`) provides high-performance implementations via PyO3.

### Structure

```
rust/zoo/src/
├── lib.rs              # PyO3 module, FFI boundary, PyOperationConfig dispatch
├── pipeline.rs         # Pipeline orchestration, batch execution
├── operations.rs       # TextOperation trait, OperationRng, common operations
├── text_buffer.rs      # Segment-aware text representation (protected regions)
├── rng.rs              # DeterministicRng for reproducible operations
├── cache.rs            # Content-addressed caching for layouts/assets
├── resources.rs        # Embedded asset loading (homophones, homoglyphs)
├── keyboard_typos.rs   # Typogre: keyboard proximity typos
├── homoglyphs.rs       # Mim1c: Unicode confusable substitution
├── homophones.rs       # Wherewolf: homophone replacement
├── word_stretching.rs  # Hokey: word elongation
├── lexeme_substitution.rs # Jargoyle: synonym/lexeme replacement
├── grammar_rules.rs    # Pedant: grammar rule application
├── zero_width.rs       # Zeedub: zero-width character insertion
└── metrics.rs          # Token metrics (delta, edit distance, compression)
```

### Key Conventions

1. **Rebuild after changes**: `uv build -Uq`
2. **No fallback mode**: Rust must compile and import - there is no Python-only mode
3. **Determinism**: Use `DeterministicRng` from `rng.rs` - never `thread_rng()` in operation logic
4. **Signature parity**: Keep exports synchronized with `internal/rust_ffi.py` shims
5. **Test parity**: `tests/core/test_hybrid_pipeline.py` verifies Rust/Python equivalence

### Adding Operations

1. Create `src/my_op.rs` implementing `TextOperation` trait
2. Add `mod my_op;` to `lib.rs`
3. Add variant to `PyOperationConfig` enum with `#[pyo3(from_item_all)]` fields
4. Add match arm in `build_operation()` to construct the operation
5. If direct Python access needed, add `#[pyfunction]` export
6. Add Python shim in `internal/rust_ffi.py`
7. Add parity tests comparing Rust vs Python output

### Benchmarking

```bash
cd rust/zoo
cargo bench --bench baseline_performance
```

Flamegraphs are generated in `target/criterion/*/profile/flamegraph.svg`.

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
| `protocols.py` | Protocol definitions for dependency inversion (Corruptor, etc.) |
| `attack/compose.py` | Pure result assembly for Attack (extract_transcript_contents, build_*_result) |
| `attack/encode.py` | Pure encoding utilities (encode_single, encode_batch, describe_tokenizer) |
| `attack/metrics_dispatch.py` | Pure metric dispatch logic (is_batch, validate_batch_consistency) |
| `attack/core_planning.py` | Pure attack plan construction and validation |

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
- `attack/core.py` / `attack/core_execution.py` - Attack orchestrator and execution dispatch
- `attack/tokenization.py` / `attack/metrics.py` - Tokenizer resolution and Rust metric loading
- `attack/analysis.py` - Analysis tools (SeedSweep, GridSearch, TokenizerComparison)
- `util/adapters.py` - Gaggle coercion and normalization helpers
- `dlc/*` - All DLC integrations (PyTorch, HuggingFace, LangChain, NeMo, etc.)

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

1. **Pure modules** (`zoo/validation.py`, `zoo/transforms.py`, `zoo/rng.py`, `zoo/core_planning.py`, `zoo/corrupt_dispatch.py`, `compat/types.py`, `conf/types.py`, `constants.py`, `protocols.py`, `attack/compose.py`, `attack/encode.py`, `attack/metrics_dispatch.py`, `attack/core_planning.py`): trust inputs, no side effects
2. **Boundary modules** (`main.py`, `__init__` methods, `zoo/core.py`, `attack/core.py`): validate thoroughly once
3. **Impure modules** (`internal/rust.py`, `compat/loaders.py`, `conf/loaders.py`, `attack/tokenization.py`, `attack/metrics.py`, `attack/core_execution.py`, `attack/analysis.py`, `zoo/core_execution.py`, `util/adapters.py`, `dlc/*`): side effects allowed

The test suite in `tests/core/test_purity_architecture.py` enforces import conventions automatically.

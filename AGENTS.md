# Glitchlings - Agent Handbook

Welcome! This repository corrals a roster of deterministic text-corruption "glitchlings" plus a CLI for orchestrating them. Treat this handbook as the default guidance for any work in the repo.

## Repository Tour
- **`src/glitchlings/`** - Installable Python package.
  - `__init__.py` exposes the public API (glitchlings, `Gaggle`, `summon`, `SAMPLE_TEXT`).
  - `__main__.py` wires `python -m glitchlings` to the CLI entry point in `main.py`.
  - `main.py` implements the CLI: parser construction, text sourcing, glitchling summoning, and optional diff output.
- **`src/glitchlings/zoo/`** - Core glitchling implementations.
  - `core.py` defines the `Glitchling` base class, `AttackWave`/`AttackOrder` enums, deterministic seed derivation, and the Rust pipeline bridge.
  - `typogre.py`, `mim1c.py`, `reduple.py`, `rushmore.py`, `redactyl.py`, `jargoyle.py`, `scannequin.py`, and `zeedub.py` provide concrete glitchlings. Word-level agents use `_rate.resolve_rate` to support legacy parameter names and expose the new `unweighted` toggle.
- **`src/glitchlings/util/`** - Shared helpers including `SAMPLE_TEXT`, keyboard-neighbour layouts, diff utilities, and rate parsing helpers.
- **`src/glitchlings/dlc/prime/`** - Optional DLC integration with the `verifiers` environments (install via `pip install -e .[prime]`).
- **`benchmarks/`** - Performance harnesses (`pipeline_benchmark.py`, etc.) that exercise both the Python and Rust execution paths.
- **`docs/`** - Field guide, development notes, release process, and per-glitchling reference pages. Changes to behaviour should update the relevant doc alongside code.
- **`rust/`** - PyO3 crates backing the optional Rust extensions.
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
- When mutating token sequences, preserve whitespace and punctuation via separator-preserving regex splits (see `reduple.py`, `rushmore.py`, `redactyl.py`).
- CLI work should continue the existing UX: validate inputs with `ArgumentParser.error`, keep deterministic output ordering, and gate optional behaviours behind explicit flags.
- Rust fast paths must remain optional: guard imports with `try`/`except ImportError`, surface identical signatures, and fall back to the Python implementation when the extension is absent.

## Testing & Tooling
- Run the full suite with `pytest` from the repository root.
- Some tests rely on the NLTK WordNet corpus; if it is missing they skip automatically. Install it via `python -c "import nltk; nltk.download('wordnet')"` to exercise Jargoyle thoroughly.
- Touching Rust-backed modules? Rerun `pytest tests/test_rust_backed_glitchlings.py` with and without the compiled extensions to keep both code paths healthy.
- Pipeline or CLI changes should also cover `tests/test_glitchling_core.py`, `tests/test_benchmarks.py`, and `tests/test_cli.py`.
- Optional extras (e.g., DLC) depend on `verifiers`. Install the `prime` extra (`pip install -e .[prime]`) when working in `src/glitchlings/dlc/` and run `tests/test_prime_echo_chamber.py` locally.

## Determinism Checklist
- Expose configurable parameters via `set_param` so fixtures in `tests/test_glitchlings_determinism.py` can reset seeds predictably.
- Derive RNGs from the enclosing context (`Gaggle.derive_seed`) instead of using global state.
- When sampling subsets (e.g., replacements or deletions), stabilise candidate ordering before selecting to keep results reproducible.
- Preserve signature parity between Python and Rust implementations so switching paths does not alter behaviour.

## Workflow Tips
- Use `summon([...], seed=...)` for programmatic orchestration when reproducing tests or crafting examples.
- The CLI lists built-in glitchlings (`glitchlings --list`) and can show diffs; update `BUILTIN_GLITCHLINGS` and help text when introducing new creatures.
- Keep documentation synchronised: update `README.md`, `docs/index.md`, per-glitchling reference pages, and `MONSTER_MANUAL.md` when behaviours or defaults change.
- When editing keyboard layouts or homoglyph mappings, ensure downstream consumers continue to work with lowercase keys (`util.KEYNEIGHBORS`).
- Rust builds are optional--keep the project functional when extensions are absent (e.g., in CI or user installs without `maturin`).

# Repository Cleanup & Organization Checklist

## 1. Documentation Architecture & "Single Source of Truth"

Currently, similar information is maintained in `MONSTER_MANUAL.md`, `README.md`, and `docs/glitchlings/*.md` (e.g.,). This invites drift where parameter descriptions update in code but lag in documentation.

- [ ] **Automate `MONSTER_MANUAL.md` Generation**
  - *Context*: `docs/build_glitchling_gallery.py` already introspects glitchlings to generate markdown.
  - *Task*: Create `docs/build_monster_manual.py`. Use flavor text defined in classes (e.g., `PedantBase.flavor`) or docstrings to generate the "Stat Block" markdown programmatically.
  - *Goal*: Ensure "flavor" documentation automatically reflects current defaults and available parameters.

- [ ] **Consolidate "Getting Started" Guides**
  - *Context*: `README.md`, `docs/index.md`, and `AGENTS.md` all contain workflow instructions.
  - *Task*: Reduce `README.md` to a project elevator pitch and a link to `docs/index.md`. Move developer-specific instructions exclusively to `docs/development.md`.
  - *Goal*: Reduce maintenance surface area; users go to one place for instructions.

## 2. Configuration Consolidation

There are three config-related files in the top-level package: `config.py`, `attack_config.py`, and `runtime_config.py`.

- [x] **Create `glitchlings.conf` Submodule**
  - *Context*: `src/glitchlings/config.py` currently just re-exports the other two.
  - *Task*: Move `attack_config.py` and `runtime_config.py` into a new directory `src/glitchlings/conf/`. Rename `config.py` to `src/glitchlings/conf/__init__.py`.
  - *Goal*: Namespace separation. `from glitchlings.conf import load_attack_config` is cleaner.
  - *Status*: Added `glitchlings.conf` with compatibility shims for legacy imports.

- [x] **Unify Config Schemas**
  - *Context*: `AttackConfig` (YAML) and `RuntimeConfig` (TOML) use different loaders.
  - *Task*: Abstract loader logic into a shared helper in the new submodule that handles file I/O and validation consistently.
  - *Status*: Shared loader utilities now provide consistent file I/O and mapping validation for YAML and TOML configs.

## 3. Asset Management Centralization

Asset logic is split between `glitchlings.zoo.assets`, `glitchlings.dev.sync_assets`, and Rust's `resources.rs`.

- [ ] **Promote Assets Module**
  - *Context*: `src/glitchlings/zoo/assets/` exists, but assets are general.
  - *Task*: Move `src/glitchlings/zoo/assets/` to `src/glitchlings/assets/`. Update `MANIFEST.in` and setup configuration.
  - *Goal*: Decouple assets from the `zoo` subdirectory.

- [ ] **Strict Asset Manifest**
  - *Context*: `sync_assets.py` hardcodes `PIPELINE_ASSETS`.
  - *Task*: Move the `PIPELINE_ASSETS` constant into `src/glitchlings/assets/__init__.py`. Ensure both Python loaders and `build.rs` reference this single list.
  - *Goal*: Prevent build and packaging from drifting apart on required assets.

## 4. Internal Module Hygiene

Cleanup technical debt from the Rust migration.

- [ ] **Consolidate Rust Loading**
  - *Context*: `src/glitchlings/_zoo_rust/__init__.py` locates the extension, while `src/glitchlings/zoo/_rust_extensions.py` imports it.
  - *Task*: Merge `_rust_extensions.py` logic into a single internal module (e.g., `src/glitchlings/internal/rust.py`).
  - *Goal*: Single entry point for "Get Rust function or raise error."

- [ ] **Standardize "Behavioral" Constants**
  - *Context*: Constants like `DEFAULT_ATTACK_SEED` live in `attack_config.py`. Default rates are hardcoded in `__init__` methods.
  - *Task*: Create `src/glitchlings/constants.py`. Move seeds, default rates, and standard file paths there.
  - *Goal*: Allow global tuning of defaults and centralized reference in docs/tests.

## 5. Test Suite Organization

- [ ] **Isolate "Pure Python" vs "Rust Required" Tests**
  - *Context*: Tests currently rely on markers like `requires_rust`.
  - *Task*: Move all tests that *strictly* require the compiled extension into `tests/rust/`. Keep `tests/core/` for Python-side API logic.
  - *Goal*: Easier CI debugging (compilation vs logic errors).

- [ ] **Benchmark Hygiene**
  - *Context*: `benchmarks/pipeline_benchmark.py` exists.
  - *Task*: Integrate benchmarks into CI (as a non-failing step) to monitor performance regressions.

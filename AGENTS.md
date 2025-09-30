# Glitchlings – Agent Handbook

This repository packages a menagerie of deterministic text-corruption "glitchlings" plus a CLI for orchestrating them.
Use this handbook as the default guidance for any work in the repo.

## Repository Tour
- **`src/glitchlings/zoo/`** – Core glitchling implementations.
  - `core.py` defines the `Glitchling` base class, attack-wave ordering, and the `Gaggle` orchestrator.
  - The remaining modules (e.g., `typogre.py`, `mim1c.py`, `reduple.py`, `rushmore.py`, `redactyl.py`, `jargoyle.py`, `scannequin.py`) supply concrete glitchlings with deterministic RNG usage.
- **`src/glitchlings/main.py`** – Entry point for the `glitchlings` CLI (parser construction, text routing, diff display).
- **`src/glitchlings/util/`** – Shared utilities including `SAMPLE_TEXT`, keyboard-neighbour maps, and string diff helpers.
- **`src/glitchlings/dlc/prime.py`** – Optional “Prime” DLC integrating with the `verifiers` environments.
- **`tests/`** – Pytest suite covering determinism, parameter effects, and `Gaggle` behaviour.
- **Top-level docs** – `README.md` (project intro, usage) and `MONSTER_MANUAL.md` (bestiary-style descriptions).

## Coding Conventions
- Target **Python 3.12+** (see `pyproject.toml`).
- Follow the existing import order: standard library, third-party, then local modules.
- Every new glitchling should:
  - Subclass `Glitchling` and set `scope`/`order` using `AttackWave` and `AttackOrder` (`core.py`).
  - Accept keyword-only parameters in `__init__`, forwarding them through `super().__init__` to populate `set_param`-backed attributes.
  - Use the provided `rng` from the glitchling instead of creating global randomness, to preserve determinism inside `Gaggle` executions.
- Prefer explicit, well-scoped helper functions (see the existing zoo modules) and include docstrings describing behaviour and determinism notes when randomness is involved.
- Utilities that mutate strings should keep whitespace and punctuation intact by splitting with separator-preserving regexes (see `reduple.py`, `rushmore.py`, and `redactyl.py`).
- When touching CLI code, keep the UX conventions already present: informative parser errors via `ArgumentParser.error`, optional `--diff` output, and deterministic ordering when listing glitchlings.

## Testing & Tooling
- Run the test suite with `pytest` from the repository root.
- Some tests rely on the NLTK WordNet corpus; if it is unavailable they skip automatically, but fetching it via `python -c "import nltk; nltk.download('wordnet')"` keeps the suite green.
- Optional extras (e.g., DLC) depend on `verifiers`. Install the `prime` extra (`pip install -e .[prime]`) if you need to work in that area.

## Determinism Checklist
- Expose configurable parameters via `set_param` so tests can reset seeds (`tests/test_glitchlings_determinism.py`).
- Always reset or derive RNGs from the parent context (`Gaggle.derive_seed`) instead of relying on global state.
- When sampling subsets (e.g., replacements/deletions), sort or otherwise stabilise candidate ordering before choosing, so results are reproducible across runs.

## Workflow Tips
- Use `summon([...], seed=...)` for programmatic orchestration and to reproduce test fixtures.
- The CLI lists built-in glitchlings (`glitchlings --list`) and can diff outputs; when extending it, update `BUILTIN_GLITCHLINGS` and related help text accordingly.
- Keep documentation in sync: update `MONSTER_MANUAL.md` and `README.md` if new glitchlings or behaviours are introduced.
- When modifying keyboard layouts or homoglyph mappings, ensure downstream functions continue to operate on lowercase keys (see `util.KEYNEIGHBORS`).


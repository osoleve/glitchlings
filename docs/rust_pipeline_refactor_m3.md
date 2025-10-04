# Glitchlings Rust Pipeline Refactor — Milestone 3

Milestone 3 introduces a deterministic RNG in Rust that mirrors Python's `random.Random` so the future pipeline can derive seeds once and execute multiple glitchlings without crossing the Python boundary.

## Python-Compatible RNG
- Implemented a `PyRng` wrapper around a Mersenne Twister state machine, reproducing CPython's seeding routine, 53-bit float generation, and tempering logic.
- Added parity helpers for `random()`, `getrandbits()`, `randrange()`, and `sample()` so existing glitchlings can migrate without behavioural drift.
- Surface clear error variants (`PyRngError`) for empty ranges, zero steps, and oversized requests to keep pipeline callers honest.

## Determinism & Validation
- Seed material uses the same little-endian 32-bit word expansion as CPython, ensuring that `Gaggle.derive_seed` values drive identical sequences across languages.
- Rust unit tests lock in parity for the master seed (`151`) and a derived seed from `Gaggle.derive_seed`, covering floating point draws, range selection, bit extraction, and sampling across both small and large populations.

## Next Steps
- Thread `PyRng` through the shared `TextBuffer` mutations so each glitchling can consume identical sequences without Python mediation.
- Begin adapting glitchling operations to the new in-place pipeline execution model once RNG state flows through the executor.

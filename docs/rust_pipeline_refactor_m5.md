# Glitchlings Rust Pipeline Refactor — Milestone 5

Milestone 5 introduces a deterministic `Pipeline` executor that mirrors Gaggle's ordering and seed derivation so multiple
glitchlings can run in Rust without returning control to Python between mutations.

## Deterministic Pipeline Executor
- Added a `Pipeline` struct that stores ordered `GlitchDescriptor`s, derives per-operation seeds via a Rust `derive_seed`
  function matching `Gaggle.derive_seed`, and applies each `GlitchOp` sequentially to a shared `TextBuffer`.
- Encapsulated failure cases in a `PipelineError` that reports the failing glitchling and forwards underlying `GlitchOpError`
  context for Python interop.
- Re-exported the pipeline pieces from the crate root so the forthcoming PyO3 entry point can batch work directly through the
  executor.

## Seed Parity & Tests
- Ported the `_int_to_bytes` logic from Python to ensure seed material hashed through BLAKE2s yields identical 64-bit values.
- Added unit tests to lock in known derived seeds and to verify the pipeline applies operations in order and remains
  deterministic across repeated runs.
- These tests provide confidence that the executor respects the orchestration contract ahead of Python integration.

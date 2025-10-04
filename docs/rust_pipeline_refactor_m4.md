# Glitchlings Rust Pipeline Refactor — Milestone 4

Milestone 4 refactors the Rust glitchlings to operate on the shared `TextBuffer` via a common `GlitchOp` trait so multiple
corruptions can be staged without bouncing through Python.

## GlitchOp Trait & RNG Abstraction
- Introduced a `GlitchOp` trait with an `apply(&mut TextBuffer, &mut dyn GlitchRng)` signature and a `GlitchRng` bridge that is
  implemented by both the new Rust `PyRng` and Python's `random.Random` objects.
- Added a `GlitchOpError` type that unifies buffer issues, RNG failures, and redaction precondition errors while translating
  cleanly to Python exceptions for the legacy string-based adapters.
- Re-exported the operations and error types from the crate root so upcoming pipeline work can compose them ergonomically.

## In-Place Glitchling Updates
- Reimplemented the reduplication, deletion, redaction, and OCR artifact glitchlings as structs mutating the shared `TextBuffer`
  in place, reusing the consolidated tokenisation and regex helpers from earlier milestones.
- Ensured logic parity with the existing Python fallbacks, including whitespace cleanup for deletions and merge semantics for
  redactions.
- Let each operation validate its own preconditions instead of short-circuiting on
  empty buffers so the redaction path surfaces the same "no redactable words"
  error that Python emits.
- Added unit tests covering representative mutations, error conditions, and OCR span selection to guard against regressions as
  the pipeline evolves.

## Python Compatibility Adapters
- Kept thin PyO3 functions that wrap each `GlitchOp` with a `PythonRngAdapter`, preserving the existing extension API surface
  while steering the heavy lifting through the new abstractions.
- These adapters provide a safe bridge during the transition and ensure we can continue to run the Python determinism tests
  before the pipeline wiring lands.

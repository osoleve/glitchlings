# Glitchlings Rust Pipeline Refactor — Milestone 6

Milestone 6 focuses on Python integration so the existing `Gaggle` orchestrator can batch
work through the Rust pipeline without sacrificing determinism or backwards compatibility.

## PyO3 Pipeline Entry Point
- Exposed a `compose_glitchlings` pyfunction that converts Python descriptors into
  `GlitchDescriptor`s, instantiates the Rust `Pipeline`, and returns the mutated text.
- Accepted dictionaries tagged with operation `type` values (`reduplicate`, `delete`,
  `redact`, and `ocr`) so Python can describe the batch without constructing Rust-side
  objects manually.

## Gaggle Fast-Path Integration
- Added lightweight builders that translate `Gaggle`'s ordered glitchling clones into
  descriptor dictionaries compatible with the new PyO3 entry point.
- Updated `Gaggle.corrupt` to prefer the Rust pipeline when the extension is available
  and all glitchlings in the wave have pipeline support, falling back transparently to
  the existing Python loop when necessary or when the extension raises.

## Tests & Guardrails
- Extended the Rust-backed test suite with parity checks for `compose_glitchlings` and
  a regression test that confirms `Gaggle` uses the Rust pipeline when all operations
  support it, while still matching the Python sequence's output.
- Retained optional behaviour by skipping the new tests if the extension is not
  installed, keeping environments without the Rust build fully functional.

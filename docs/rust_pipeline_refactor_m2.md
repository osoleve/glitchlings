# Glitchlings Rust Pipeline Refactor — Milestone 2

Milestone 2 centralises shared resources so future pipeline stages can reuse tokenisation, regexes, and confusion data without repeated work.

## Shared Resource Catalogue
- **Tokenisation helpers** now live in `resources.rs`, providing the same separator-aware splitting logic for both the legacy Rust bindings and the new `TextBuffer` abstraction.
- **Regexes** for whitespace normalisation are compiled once with `once_cell::sync::Lazy`, enabling fast reuse across deletions, redactions, and other word-level glitchlings.
- **OCR confusion tables** are pre-sorted once and reused by OCR-related glitchlings without reallocation.

## Determinism & Parity
- Shared helpers keep the whitespace handling behaviour identical to the previous implementations, maintaining compatibility with Python fallbacks.
- Resource initialisation relies solely on deterministic constants and does not introduce new RNG usage.

## Next Steps
- With resources consolidated, upcoming milestones can focus on adapting each glitchling to operate against the shared `TextBuffer` while drawing on these central utilities.

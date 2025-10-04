# Rust Pipeline Refactor — Milestone 1 Notes

## Shared Intermediate Representation

- Introduced a `TextBuffer` abstraction (`rust/zoo/src/text_buffer.rs`) that tokenises an input string once into alternating word and separator segments.
- Each segment tracks:
  - `SegmentKind` (`Word` or `Separator`).
  - Backed text payload (`TextSegment`).
  - Derived `TextSpan` metadata capturing byte and character ranges for fast lookup.
- `TextBuffer` maintains total byte/character counts and exposes helpers to surface the word list while keeping separator runs intact for deterministic rebuilds.

## Mutation Helpers

- Word-level APIs: `replace_word`, `delete_word`, and `insert_word_after` target logical word indices (ignoring separator runs) and automatically refresh metadata.
- Character-level API: `replace_char_range` performs a single string rebuild and re-tokenises once, allowing downstream glitchlings to slice arbitrary spans while preserving consistent token metadata.
- All helpers return rich `TextBufferError` variants so future pipeline code can bubble context-specific failures back to Python.

## Testing

- Added unit tests covering tokenisation, word edits, char-range edits, insertion, and failure cases to guarantee determinism and metadata accuracy before integrating glitchlings with the buffer.

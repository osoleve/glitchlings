# Reduple

Reduple repeats words to mimic stuttering transcripts while preserving whitespace and punctuation.

- **Scope**: word level.
- **Signature**: `Reduple(rate=0.05, seed=None)`.
- **Behaviour**: randomly repeats words ("reduplication") to mimic stuttering transcripts or speech disfluencies while preserving whitespace and punctuation.
- **Usage tips**:
  - Use `rate=0.01` to emulate occasional hesitations; bump to ≥0.08 for heavy repetition stress tests.
  - Because edits preserve separators, downstream whitespace-sensitive parsers remain stable.
  - Combine with Jargoyle to mix synonym swaps and repeated words for lexical drift.

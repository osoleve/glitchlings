# Adjax

Adjax swaps the cores of neighbouring words while leaving punctuation, casing, and spacing untouched, creating sentences that still parse syntactically even as the meaning slides sideways.

- **Scope**: word level.
- **Signature**: `Adjax(rate=0.5, seed=None, swap_rate=None)`.
- **Behaviour**: samples adjacent word pairs and, with probability `rate`, trades their core tokens while preserving any leading/trailing punctuation or whitespace.
- **Usage tips**:
  - Dial `rate` down to ~0.2 for subtle paraphrase drift, or push it toward 1.0 to fully reshuffle local context.
  - Stacking Adjax before Rushmore yields scrambled-but-sparse passages that stress summarisation and retrieval models.
  - Because punctuation and separators remain in place, downstream tokenisers that depend on spacing continue to behave predictably.

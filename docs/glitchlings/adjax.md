# Adjax

Adjax is now implemented via `Rushmore(modes='swap')`, keeping the familiar adjacent-word swap while sharing configuration with the broader Rushmore toolkit.

- **Scope**: word level.
- **Signature**: `Adjax(rate=0.5, seed=None)` → delegates to Rushmore with only the swap mode enabled.
- **Behaviour**: samples adjacent word pairs and, with probability `rate`, trades their core tokens while preserving any leading/trailing punctuation or whitespace. Use Rushmore directly when you want to mix swaps with deletions or reduplications.
- **Usage tips**:
  - Dial `rate` down to ~0.2 for subtle paraphrase drift, or push it toward 1.0 to fully reshuffle local context.
  - Compose swaps with deletions via `Rushmore(modes=('delete', 'swap'), ...)` to simulate garbled transcripts that still look well formatted.
  - Because punctuation and separators remain in place, downstream tokenisers that depend on spacing continue to behave predictably.

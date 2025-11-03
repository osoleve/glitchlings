# Reduple

Reduple now serves as a compatibility wrapper for `Rushmore(modes='duplicate')`. It still repeats words to mimic stuttering transcripts, but the implementation (and new features such as multi-mode chaining) live in Rushmore.

- **Scope**: word level.
- **Signature**: `Reduple(rate=0.01, seed=None, unweighted=False)` → delegates to `Rushmore` with the duplication mode selected.
- **Behaviour**: randomly repeats words while preserving whitespace and punctuation. For advanced control (e.g., combining deletions and reduplications or altering per-mode weights), switch to Rushmore directly.
- **Usage tips**:
  - Existing code continues to work, but new projects should prefer `Rushmore(modes='duplicate', ...)` for clarity.
  - Increase `rate` to intensify repetitions, or set `duplicate_unweighted=True` on Rushmore to sample words uniformly.
  - Combine with Jargoyle or Rushmore's deletion mode to mix redundancy with missing context.

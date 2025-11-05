# Rushmore

Rushmore now bundles three word-level attacks—deletions, reduplications, and adjacent swaps—under a single configurable interface. By default it continues to delete words, but you can opt into any combination of the historical Reduple and Adjax behaviours with the `modes` parameter.

- **Scope**: word level.
- **Signature**: `Rushmore(modes='delete', rate=None, delete_rate=None, duplicate_rate=None, swap_rate=None, unweighted=False, delete_unweighted=None, duplicate_unweighted=None, seed=None)`.
- **Behaviour**: executes the enabled modes in order (delete → duplicate → swap) using the same RNG so chained operations remain deterministic. When a per-mode rate is omitted, Rushmore falls back to sensible defaults (0.01 for deletions/reduplications, 0.5 for swaps). Each mode continues to tidy whitespace and punctuation exactly as before.
- **Usage tips**:
  - Use `modes='delete'`, `modes='duplicate'`, or `modes='swap'` to reproduce the legacy Rushmore, Reduple, and Adjax behaviours respectively; `modes='all'` (or any iterable of mode names) composes them.
  - `rate` applies to every active mode unless you provide a per-mode override such as `duplicate_rate=0.02` or `swap_rate=0.4`.
  - Toggle `unweighted=True` to sample uniformly; override individual modes with `delete_unweighted` / `duplicate_unweighted` when you only want to change part of the attack.
  - The first word is still preserved during deletions—prepend a short throwaway sentence if you need removals deeper in the passage.
  - Standalone `Reduple` and `Adjax` glitchlings have been retired; use `Rushmore(modes='duplicate')` and `Rushmore(modes='swap')` to recreate their behaviour with the modern interface.

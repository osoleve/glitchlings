# Rushmore

Rushmore orchestrates word-level duplication, deletion, and swap attacks depending on the configured `attack_mode`.

- **Scope**: word level.
- **Signature**: `Rushmore(rate=0.01, seed=None, unweighted=False, attack_mode="all")`.
- **Behaviour**: duplicates (`attack_mode="duplicate"`), deletes (`"delete"`), swaps adjacent cores (`"swap"`), or chains the full trio (`"all"`). Deletion mode skips the opening word to preserve a foothold and tidies whitespace/punctuation. Duplication mode reintroduces stuttering repetition, and swap mode mirrors Adjax's adjacent swaps with the same probability semantics.
- **Usage tips**:
  - Keep deletion rates conservative (<0.03) to avoid stripping sentences bare; duplication and swap modes tolerate higher values.
  - Toggle `unweighted=True` to sample uniformly instead of favouring shorter tokens for duplication and deletion modes.
  - Use multiple Rushmore instances with different `attack_mode` values when you want deterministic ordering (e.g., duplicate before delete) without reaching for separate glitchlings.

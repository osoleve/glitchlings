# Zeedub

Zeedub plants zero-width characters between neighbouring non-space glyphs so that text looks unchanged to the naked eye while hiding invisible obstacles for downstream tokenisers.

- **Scope**: character level (last in the wave so it runs after other character glitchlings).
- **Signature**: `Zeedub(rate=0.02, characters=None, seed=None)`.
- **Behaviour**: calculates the pool of eligible bigrams formed by adjacent non-space codepoints, samples a deterministic subset proportional to `rate`, and injects zero-width characters such as U+200B (ZERO WIDTH SPACE) or U+2060 (WORD JOINER).
- **Usage tips**:
  - Keep `rate` low (0.005–0.02) for subtle tampering; higher values quickly saturate text with invisible joins.
  - Pass a custom `characters` sequence to restrict the insertion set to specific control codes or research artifacts.
  - When debugging, wrap outputs with `repr(...)` or replace `"\u200b"` etc. to make the hidden glyphs visible.


# Redactyl

Redactyl censors words by replacing their core characters with a configurable glyph.

- **Scope**: word level.
- **Signature**: `Redactyl(replacement_char="FULL_BLOCK", rate=0.025, merge_adjacent=False, seed=151, unweighted=False)`.
- **Behaviour**: replaces the core characters of selected words with a replacement glyph (the `FULL_BLOCK` constant (U+2588 FULL BLOCK) by default) to simulate document redaction. Optionally merges adjacent redaction blocks across punctuation.
- **Usage tips**:
  - Switch `replacement_char` to `_` or `*` when terminals struggle with block glyphs.
  - Enable `merge_adjacent=True` to form continuous bars when redacting phrases.
  - Toggle `unweighted=True` to sample words uniformly instead of biasing toward longer tokens.
  - When no redactable words exist, the underlying implementation raises a `ValueError`--wrap calls with try/except in automated pipelines.

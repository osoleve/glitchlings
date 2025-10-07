# Redactyl

Redactyl censors words by replacing their core characters with a configurable glyph.

- **Scope**: word level.
- **Signature**: `Redactyl(replacement_char="█", rate=0.05, merge_adjacent=False, seed=151)`.
- **Behaviour**: replaces the core characters of selected words with a replacement glyph (default FULL BLOCK) to simulate document redaction. Optionally merges adjacent redaction blocks across punctuation.
- **Usage tips**:
  - Switch `replacement_char` to `_` or `*` when terminals struggle with block glyphs.
  - Enable `merge_adjacent=True` to form continuous bars when redacting phrases.
  - When no redactable words exist, the underlying implementation raises a `ValueError`—wrap calls with try/except in automated pipelines.

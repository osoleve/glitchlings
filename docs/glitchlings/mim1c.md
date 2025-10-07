# Mim1c

Mim1c replaces characters with visually confusable Unicode homoglyphs to test robustness against adversarial typography.

- **Scope**: character level (late attack order so it acts after insertions/deletions).
- **Signature**: `Mim1c(rate=0.02, classes=None, banned_characters=None, seed=None)`.
- **Behaviour**: replaces alphanumeric characters with visually confusable Unicode homoglyphs via `confusable_homoglyphs` (e.g., `A → Α`, `e → е`). When `classes` is omitted it targets Latin, Greek, and Cyrillic scripts; pass `classes="all"` to consider every alias.
- **Usage tips**:
  - Restrict `classes` (e.g., `classes=["LATIN"]`) when evaluation pipelines reject non-Latin scripts.
  - Use `banned_characters` to exclude confusables that would break downstream filters (e.g., ban full-width ASCII when testing strict lexers).
  - Keep `rate` below 0.03 for legible perturbations; higher values can break tokenisers that expect ASCII.
  - Pairs well with Typogre for keyboard + homoglyph chaos.

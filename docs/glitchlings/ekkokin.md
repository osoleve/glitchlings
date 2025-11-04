# Ekkokin

Ekkokin swaps words for curated homophones (courtesy of Wikipedia) so the end result still sounds natural even as the spelling drifts away.

- **Scope**: word level.
- **Signature**: `Ekkokin(rate=0.02, seed=None)`.
- **Behaviour**: normalises homophone sets sourced from `assets/ekkokin_homophones.json`, then samples replacements deterministically from each group. The Rust-backed `ekkokin_homophones` pipeline mirrors the documented behaviour and now underpins production runs, so keep the compiled extension available.
- **Usage tips**:
  - Dial `rate` up cautiously—homophones accumulate quickly because each replacement still reads plausibly.
  - Pair with `typogre` for blended lexical/visual noise, or run alone to focus on phonetic ambiguity in evaluation prompts.

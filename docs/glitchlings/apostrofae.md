# Apostrofae

Apostrofae swaps balanced straight quotes, apostrophes, and backticks for smart-quote pairs sourced from the shared lookup table.

- **Scope**: character level (normal ordering).
- **Signature**: `Apostrofae(seed=None)`.
- **Behaviour**: walks the input once to find matching straight-quote pairs before replacing each boundary with a randomly sampled fancy counterpart. Unpaired glyphs (like contractions) remain untouched so the output stays readable while still revealing formatting mistakes.
- **Usage tips**:
  - Chain Apostrofae after word-level glitchlings to preserve their token boundaries before the decorative swaps run.
  - Provide a stable `seed` (or rely on a `Gaggle` seed) when you need reproducible smart-quote layouts in regression tests or documentation.

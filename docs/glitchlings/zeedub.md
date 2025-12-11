# Zeedub

Zeedub plants zero-width characters between neighbouring non-space glyphs so that text looks unchanged to the naked eye while hiding invisible obstacles for downstream tokenisers.

- **Scope**: character level (last in the wave so it runs after other character glitchlings).
- **Signature**: `Zeedub(rate=0.02, visibility="glyphless", placement="random", max_consecutive=4, characters=None, seed=None)`.
- **Behaviour**: calculates the pool of eligible positions based on the placement mode, samples a deterministic subset proportional to `rate`, and injects zero-width characters from the visibility mode's palette.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rate` | float | 0.02 | Probability of insertion at each eligible position |
| `visibility` | str | `"glyphless"` | Controls which zero-width characters are used |
| `placement` | str | `"random"` | Controls where insertions can occur |
| `max_consecutive` | int | 4 | Maximum consecutive insertions (0 for unlimited) |
| `characters` | list | None | Custom palette (overrides visibility mode) |
| `seed` | int | None | Deterministic seed for reproducibility |

## Placement Modes

- **`random`** (default): Insert between any adjacent non-whitespace characters. This is the most aggressive mode.

- **`grapheme_boundary`**: Only insert at grapheme cluster boundaries. This is safer for rendering because it never splits user-perceived characters (e.g., won't insert between a base character and its combining accent). Uses Unicode Standard Annex #29 segmentation rules.

- **`script_aware`**: Context-sensitive insertion. ZWJ (Zero Width Joiner) and ZWNJ (Zero Width Non-Joiner) are only inserted where they're linguistically meaningful:
  - Adjacent to Arabic script characters
  - Adjacent to Indic script characters (Devanagari, Bengali, Tamil, etc.)
  - Adjacent to emoji (for ZWJ sequences)

  Other zero-width characters (ZWSP, Word Joiner, etc.) are inserted anywhere.

## Visibility Modes

- **`glyphless`** (default): True invisibles only. These characters have no visual representation:
  - U+200B Zero Width Space (ZWSP)
  - U+200C Zero Width Non-Joiner (ZWNJ)
  - U+200D Zero Width Joiner (ZWJ)
  - U+FEFF Byte Order Mark (BOM)
  - U+2060 Word Joiner (WJ)
  - U+034F Combining Grapheme Joiner (CGJ)

- **`with_joiners`**: Adds variation selectors VS1–VS16 (U+FE00–U+FE0F). These are used to select alternate glyphs for emoji and CJK characters. Zeedub only inserts these after valid base characters (emoji, CJK ideographs, mathematical symbols).

- **`semi_visible`**: Adds characters that are technically visible but extremely narrow:
  - U+200A Hair Space
  - U+2009 Thin Space
  - U+202F Narrow No-Break Space

## Safety Constraints

By default, Zeedub caps consecutive insertions at 4 (`max_consecutive=4`) to prevent pathological sequences that can:
- Crash or hang text renderers
- Create selection/cursor navigation issues
- Overwhelm tokenizers with excessive invisible tokens

Set `max_consecutive=0` to disable this limit for research purposes.

## Examples

```python
from glitchlings import Zeedub

# Default behavior
z = Zeedub(rate=0.02, seed=42)
result = z("Hello world")

# Safer insertion at grapheme boundaries only
z = Zeedub(rate=0.05, placement="grapheme_boundary", seed=42)
result = z("café résumé")  # Won't split combining accents

# Script-aware for multilingual text
z = Zeedub(rate=0.1, placement="script_aware", seed=42)
result = z("Hello مرحبا नमस्ते")  # ZWJ/ZWNJ only in Arabic/Devanagari

# Include variation selectors for emoji research
z = Zeedub(rate=0.1, visibility="with_joiners", seed=42)
result = z("Hello 👋 world")

# Unlimited consecutive insertions (research mode)
z = Zeedub(rate=0.5, max_consecutive=0, seed=42)
result = z("test")
```

## Usage Tips

- Keep `rate` low (0.005–0.02) for subtle tampering; higher values quickly saturate text with invisible joins.
- Use `placement="grapheme_boundary"` when working with combining characters or emoji to avoid creating malformed sequences.
- Use `placement="script_aware"` for multilingual corpora to ensure joiners are contextually appropriate.
- Pass a custom `characters` sequence to restrict the insertion set to specific control codes.
- When debugging, wrap outputs with `repr(...)` or replace `"\u200b"` etc. to make the hidden glyphs visible.

## References

- [Unicode Standard Annex #29: Unicode Text Segmentation](https://www.unicode.org/reports/tr29/) — Grapheme cluster boundary rules for `grapheme_boundary` mode
- [Unicode Technical Report #36: Unicode Security Considerations](https://www.unicode.org/reports/tr36/) — Default_Ignorable handling and visibility classification

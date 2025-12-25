# Redactyl

*"Oops, that was my black highlighter. Some things are better left ████████."*

Redactyl is a censorious glitchling that blacks out words with solid block characters. It simulates classified documents, FOIA releases, and the general paranoia of information control. The text is still technically there—you just can't read it anymore.

## Stats

| Attribute | Value |
|-----------|-------|
| **Scope** | Word |
| **Attack Order** | Normal |
| **Signature** | Block character redaction |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `replacement_char` | str | `"█"` | The character used to black out words |
| `rate` | float | 0.025 | Probability of redacting each word |
| `merge_adjacent` | bool | False | Connect adjacent redactions into continuous bars |
| `seed` | int | 151 | Deterministic seed for reproducibility |
| `unweighted` | bool | False | Sample words uniformly instead of biasing toward longer ones |

## Behaviour

Redactyl selects words probabilistically and replaces their characters with the `replacement_char`. By default it uses U+2588 FULL BLOCK (█), which renders as a solid black rectangle in most fonts.

**Weighting** — By default, longer words are more likely to be redacted than shorter ones. This mimics how real redaction often targets names, places, and technical terms (which tend to be longer). Set `unweighted=True` for uniform sampling.

**Merging** — When `merge_adjacent=True`, consecutive redacted words (even across punctuation) merge into a single continuous bar. This produces the distinctive look of heavily censored documents.

## Examples

```python
from glitchlings import Redactyl

# Default behavior
redact = Redactyl(rate=0.2, seed=42)
redact("The secret meeting occurred at midnight in the warehouse")
# "The ██████ meeting occurred at ████████ in the █████████"

# Continuous bars for that FOIA aesthetic
foia = Redactyl(rate=0.3, merge_adjacent=True, seed=42)
foia("Agent Smith met Agent Jones at the classified location")
# "Agent █████ met █████ █████ at the ██████████ ████████"

# ASCII-safe redaction for terminals that struggle with Unicode
safe = Redactyl(replacement_char="X", rate=0.2, seed=42)
safe("Redacted content here")
# "XXXXXXXX content XXXX"

# Asterisk style (like password masking)
stars = Redactyl(replacement_char="*", rate=0.2, seed=42)
stars("Sensitive information follows")
# "********* *********** follows"
```

## When to Use Redactyl

**Incomplete information testing** — Can your model reason with missing pieces? Redactyl lets you test comprehension when key terms are hidden.

**OCR pipeline robustness** — Scanned documents with redactions are common in legal and historical archives. Test how your model handles them.

**Anonymization simulation** — When you need training data that looks like it's been through a privacy filter.

**Document classification** — Does your model rely on specific words, or does it understand context? Redact the obvious keywords and find out.

!!! tip "Usage Tips"
    - The default `rate=0.025` produces light redaction. For that "heavily classified" look, try 0.1–0.2.
    - Some terminals render `█` poorly. Switch to `replacement_char="_"` or `"*"` for ASCII-safe output.
    - The `unweighted=True` option is useful when you want to test short-word comprehension, not just long-word comprehension.
    - Combine with [Scannequin](scannequin.md) to simulate poorly scanned, heavily redacted archives.

!!! warning "Empty Input Edge Case"
    If the text contains no redactable words (e.g., a single character), Redactyl raises a `ValueError`. Wrap calls in try/except for automated pipelines.

## Complementary Glitchlings

- **[Scannequin](scannequin.md)** — OCR errors on top of redactions for that "archive from the basement" feel
- **[Rushmore](rushmore.md)** — Delete words entirely instead of redacting them
- **[Zeedub](zeedub.md)** — Hide information invisibly instead of visibly

## See Also

- [Monster Manual](../monster-manual.md) — Full bestiary with all glitchlings
- [Visual Gallery](../glitchling-gallery.md) — See Redactyl output at multiple rates

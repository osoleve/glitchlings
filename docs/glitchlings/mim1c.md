# Mim1c

*"Wait, was that an 'a' or an 'а'? Looks the same to me..."*

Mim1c is a master of visual deception. It replaces characters with Unicode homoglyphs—characters from different scripts that look nearly identical. The text appears unchanged to human readers but breaks string comparisons, parsers, and security filters that expect ASCII.

- **Scope**: character level (late attack order so it acts after insertions/deletions).
- **Signature**: `Mim1c(rate=0.02, classes=None, banned_characters=None, mode="mixed_script", max_consecutive=3, seed=None)`.
- **Behaviour**: replaces alphanumeric characters with visually confusable Unicode homoglyphs (e.g., `A → Α`, `e → е`). When `classes` is omitted it targets Latin, Greek, and Cyrillic scripts; pass `classes="all"` to consider every alias.

## Substitution Modes

The `mode` parameter controls which types of confusables are allowed:

| Mode | Description | Example |
|------|-------------|---------|
| `single_script` | Only same-script confusables (Latin→Latin variants). Safest for most pipelines. | `l → ɭ` (Latin Extended) |
| `mixed_script` | Cross-script substitutions (Latin↔Cyrillic↔Greek). Default mode with maximum visual similarity. | `H → Η` (Greek), `o → о` (Cyrillic) |
| `compatibility` | Unicode compatibility variants (fullwidth, math alphanumerics, enclosed forms). | `H → Ｈ` (Fullwidth) |
| `aggressive` | All confusable types combined. Most disruptive. | Any of the above |

## Locality Control

The `max_consecutive` parameter limits how many adjacent characters can be substituted, preventing the "ransom note" effect where every character comes from a different script. Default is 3; set to 0 for unlimited.

## Script Affinity

In `mixed_script` mode, substitutions are weighted by visual plausibility:

- Latin↔Cyrillic: 0.9 weight (very similar appearance)
- Latin↔Greek: 0.8 weight
- Cyrillic↔Greek: 0.7 weight

This produces more natural-looking spoofed text.

## Usage Tips

- Restrict `classes` (e.g., `classes=["LATIN"]`) when evaluation pipelines reject non-Latin scripts.
- Use `banned_characters` to exclude confusables that would break downstream filters (e.g., ban full-width ASCII when testing strict lexers).
- Keep `rate` below 0.03 for legible perturbations; higher values can break tokenisers that expect ASCII.
- Use `mode="single_script"` when you need substitutions that won't trigger mixed-script detection.
- Use `mode="compatibility"` to test fullwidth/mathematical character handling.
- Pairs well with Typogre for keyboard + homoglyph chaos.

## Examples

```python
from glitchlings import Mim1c

# Default: mixed-script substitutions with locality control
mim1c = Mim1c(rate=0.05, seed=42)
print(mim1c("Hello World"))  # Ηello Wοrld (H→Η Greek, o→ο Cyrillic)

# Safe mode: only same-script substitutions
safe_mim1c = Mim1c(rate=0.1, mode="single_script", seed=42)
print(safe_mim1c("Hello World"))  # Heɭɭo Worɭd (l→ɭ Latin Extended)

# Compatibility mode: fullwidth and math characters
compat_mim1c = Mim1c(rate=0.1, mode="compatibility", seed=42)
print(compat_mim1c("Hello World"))  # Ｈello Ｗorld (fullwidth)

# Aggressive with no locality limit
chaos_mim1c = Mim1c(rate=0.2, mode="aggressive", max_consecutive=0, seed=42)
```

## When to Use Mim1c

**Unicode normalization testing** — Does your system normalize confusables before comparison? Mim1c finds out.

**Security filter bypass testing** — Homoglyph attacks are used to evade keyword filters. Test your defenses.

**Tokenizer robustness** — Many tokenizers split unexpectedly on non-ASCII characters. See what breaks.

**Adversarial example generation** — Create visually identical but technically different text for ML testing.

## Complementary Glitchlings

- **[Typogre](typogre.md)** — Keyboard typos for a different class of character-level corruption
- **[Zeedub](zeedub.md)** — Invisible characters instead of visible lookalikes
- **[Scannequin](scannequin.md)** — OCR-style errors based on visual confusion

## See Also

- [Monster Manual](../monster-manual.md) — Full bestiary with all glitchlings
- [Visual Gallery](../glitchling-gallery.md) — See Mim1c output at multiple rates

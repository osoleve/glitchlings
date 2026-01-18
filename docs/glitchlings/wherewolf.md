# Wherewolf

*"Did you hear what I heard? Or did you here what I herd?"*

Wherewolf is a cunning creature that swaps words for their homophones—words that sound identical but mean entirely different things. The text still reads naturally aloud, but the spelling drifts in ways that trip up models relying on surface patterns.

## Stats

| Attribute | Value |
|-----------|-------|
| **Scope** | Word |
| **Attack Order** | Early |
| **Signature** | Phonetic word substitution |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rate` | float | 0.02 | Probability of swapping each eligible word |
| `seed` | int | None | Deterministic seed for reproducibility |

## Behaviour

Wherewolf maintains a curated homophone dictionary (sourced from Wikipedia and stored in `assets/ekkokin_homophones.json`). When it encounters a word with known homophones, it may swap it for one of its sound-alikes.

The replacements preserve casing—"Their" becomes "There", not "there"—so the text maintains its visual rhythm even as meaning shifts.

## Examples

```python
from glitchlings import Wherewolf

wolf = Wherewolf(rate=0.5, seed=42)

# Homophones sound right but look wrong
wolf("The knight rode through the night")
# "The night road through the knight"

wolf("I knew the new gnu")
# "Eye new the knew gnu"

wolf("They're going to their house over there")
# "There going to they're house over their"
```

## When to Use Wherewolf

**Spell-checker testing** — Homophones are grammatically valid words, so naive spell-checkers miss them entirely. Wherewolf helps you test whether your correction system catches contextual errors.

**Audio transcription robustness** — If your model processes text that might have originated from speech-to-text, homophone confusion is a realistic error pattern.

**ESL mistake simulation** — Non-native speakers often confuse homophones. Wherewolf can generate training data that reflects this common error type.

**Phonetic ambiguity research** — When you need text that's correct-when-spoken but wrong-when-written.

!!! tip "Usage Tips"
    - Keep `rate` low (0.02–0.05) for realistic perturbations. Higher rates produce text that's obviously corrupted.
    - Pair with [Typogre](typogre.md) for blended lexical and visual noise.
    - Run alone when you want to focus on phonetic ambiguity without character-level corruption.
    - The homophone dictionary focuses on common English homophones. Rare or archaic forms aren't included.

## Complementary Glitchlings

- **[Typogre](typogre.md)** — Add keyboard typos on top of homophone swaps for compound corruption
- **[Jargoyle](jargoyle.md)** — Swap words for synonyms (semantic drift) alongside homophones (phonetic drift)
- **[Scannequin](scannequin.md)** — OCR errors create a different class of word-level mistakes

## See Also

- [Monster Manual](../monster-manual.md) — Full bestiary with all glitchlings
- [Visual Gallery](../glitchling-gallery.md) — See Wherewolf output at multiple rates

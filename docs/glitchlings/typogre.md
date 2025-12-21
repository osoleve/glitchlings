# Typogre

*"What a nice word. Would be a shame if something happened to it..."*

Typogre is the classic keyboard gremlin—it simulates fat-finger typing errors by swapping characters with their keyboard neighbors, dropping spaces, doubling letters, and occasionally holding Shift too long. The result is text that looks like it was typed in a hurry by someone who never learned to touch-type.

## Stats

| Attribute | Value |
|-----------|-------|
| **Scope** | Character |
| **Attack Order** | Early |
| **Signature** | Keyboard-adjacent typos |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rate` | float | 0.02 | Probability of error at each character position |
| `keyboard` | str | `"CURATOR_QWERTY"` | Keyboard layout for adjacency lookups |
| `shift_slip_rate` | float | 0.0 | Probability of Shift modifier slippage |
| `shift_slip_exit_rate` | float | None | How quickly Shift slippage ends |
| `motor_weighting` | str | `"uniform"` | Biomechanical error weighting (see below) |
| `seed` | int | None | Deterministic seed for reproducibility |

## Behaviour

Typogre uses keyboard adjacency maps to determine which keys are "nearby" on a physical keyboard. When it corrupts a character, it picks a neighbor based on the layout. This produces realistic typos—the kind where your finger slipped one key over.

**Modifier slippage** adds another dimension: when `shift_slip_rate` is non-zero, Typogre simulates holding Shift too long, producing bursts like "HELlo" instead of "Hello". This happens *before* the standard fat-finger errors.

## Usage Tips

- Use `rate=0.005–0.01` for gentle, realistic noise. Higher rates produce obviously corrupted text.
- Set `keyboard="DVORAK"` or `keyboard="AZERTY"` to match your target population's hardware.
- Enable `shift_slip_rate` for bursty modifier errors.
- Combine with [Rushmore](rushmore.md) deletions to simulate hurried note-taking.

## Motor Coordination Weighting

Typogre supports biomechanically-informed error weights derived from the [Aalto 136M Keystrokes dataset](https://userinterfaces.aalto.fi/136Mkeystrokes/). Typos aren't just distributed geometrically by keyboard layout, they're also distributed by whether they occur when using the same finger twice, the same hand twice, or switching hands between keys.

### Weighting Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `uniform` | All keyboard neighbors equally likely (default) | Original behavior, maximum chaos |
| `wet_ink` | Cross-hand errors slip through; same-finger errors are caught | Simulates errors participants didn't catch |
| `hastily_edited` | Same-finger errors occur most often | Simulates errors participants fixed mid-stream |

### How It Works

- **Same-finger transitions** (e.g., 'e' → 'd', both left middle finger): Errors feel "wrong" and are often caught
- **Same-hand transitions** (e.g., 'e' → 'f', same hand, different fingers): Lower error detection
- **Cross-hand transitions** (e.g., 'e' → 'j', alternating hands): Errors feel "normal" and slip through

### Example

```python
from glitchlings import Typogre

# Default uniform weighting (original behavior)
typo = Typogre(rate=0.1)

# Wet ink: uncorrected errors that survive to final output
typo_wet = Typogre(rate=0.1, motor_weighting="wet_ink")

# Hastily edited: raw typing patterns before correction
typo_hasty = Typogre(rate=0.1, motor_weighting="hastily_edited")
```

### Citation

> Dhakal, V., Feit, A. M., Kristensson, P. O., & Oulasvirta, A. (2018). Observations on Typing from 136 Million Keystrokes. *CHI '18*. https://doi.org/10.1145/3173574.3174220

## Complementary Glitchlings

- **[Mim1c](mim1c.md)** — Unicode confusables for visual deception alongside keyboard typos
- **[Scannequin](scannequin.md)** — OCR-style errors for document scanning scenarios
- **[Rushmore](rushmore.md)** — Word-level deletions for hasty-writing simulation

## See Also

- [Keyboard Layouts](../keyboard-layouts.md) — Available adjacency maps (QWERTY, DVORAK, AZERTY, etc.)
- [Monster Manual](../monster-manual.md) — Full bestiary with all glitchlings
- [Visual Gallery](../glitchling-gallery.md) — See Typogre output at multiple rates

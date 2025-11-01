Spectroll remaps colour-centric vocabulary to keep descriptions surprising while staying readable. It can operate deterministically with a fixed palette swap or dip into a seeded "spectral drift" that samples nearby hues for more varied storytelling.

- **Scope**: word level.
- **Signature**: `Spectroll(mode='literal', seed=None)`.
- **Behaviour**: matches standalone colour tokens (including compounds like "reddish" or "greenery") and replaces the colour stem either via a bidirectional literal map or by sampling neighbouring hues in drift mode.
- **Usage tips**:
  - Literal mode is ideal for regression tests or deterministic golden files.
  - Drift mode pairs well with dialogue or descriptive prose where you want repeatable but non-static palettes—set the seed per scene to keep revisions stable.
  - Stack Spectroll after structural glitchlings (Adjax, Rushmore) so that sentence boundaries stay legible before the colours start drifting.

| Source phrase | Literal mode | Drift mode (seed=7) |
| --- | --- | --- |
| `red balloon` | `blue balloon` | `orange balloon` |
| `Green light` | `Lime light` | `Teal light` |
| `a reddish hue` | `a blueish hue` | `a magentaish hue` |
| `Do you prefer Black or White?` | `Do you prefer White or Black?` | `Do you prefer Purple or Cyan?` |

Use `from glitchlings.spectroll import swap_colors` when you need the core transformation as a utility function, or summon the glitchling itself with `summon(["Spectroll"], seed=...)` to integrate with the broader Gaggle orchestrator.

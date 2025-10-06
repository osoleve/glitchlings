# Keyboard Layout Reference

Glitchlings includes several keyboard adjacency maps that fuel Typogre and any
behaviour that depends on "nearby" keys. Layouts live in
`glitchlings.util.KEYNEIGHBORS` and each entry exposes a mapping from a key to
the characters that surround it on the corresponding physical keyboard.

The following layouts are currently bundled:

| Layout name | Region / focus | Notes |
| --- | --- | --- |
| `CURATOR_QWERTY` | Project-specific curation | Includes numeric neighbours for symbol-heavy glitches. |
| `QWERTY` | US English | Standard ANSI layout. |
| `DVORAK` | US English (Dvorak) | Optimised vowel/consonant arrangement. |
| `COLEMAK` | US English (Colemak) | Ergonomic compromise between QWERTY and Dvorak. |
| `AZERTY` | France / Belgium | ISO layout featuring accented characters such as `é` and `à`. |
| `QWERTZ` | Germany / Central Europe | Adds umlauts (`ä`, `ö`, `ü`) and `ß`. |
| `SPANISH_QWERTY` | Spain | Provides dedicated keys for `ñ`, acute accents, and inverted punctuation. |
| `SWEDISH_QWERTY` | Sweden / Nordic | Includes `å`, `ä`, and `ö` alongside the `<` dead-key column. |

To use a layout, import `KEYNEIGHBORS` and select the desired mapping:

```python
from glitchlings.util import KEYNEIGHBORS
neighbors = getattr(KEYNEIGHBORS, "QWERTZ")
print(neighbors["z"])  # -> list of adjacent characters
```

Each mapping only contains lowercase keys; call `.lower()` on user input before
looking up neighbours.

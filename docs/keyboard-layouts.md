# Keyboard Layouts

[Typogre](glitchlings/typogre.md) simulates fat-finger typos by swapping characters with their keyboard neighbors. The quality of those typos depends entirely on having accurate adjacency maps—you can't slip from 'f' to 'g' if the layout doesn't know they're next to each other.

Glitchlings bundles several keyboard layouts for different regions and ergonomic preferences.

## Bundled Layouts

| Layout | Region | Notes |
|--------|--------|-------|
| `CURATOR_QWERTY` | Project default | Curated QWERTY with numeric neighbors for symbol-heavy typos |
| `QWERTY` | US English | Standard ANSI layout |
| `DVORAK` | US English | Vowels on home row, consonants opposite |
| `COLEMAK` | US English | Ergonomic compromise between QWERTY and Dvorak |
| `AZERTY` | France / Belgium | ISO layout with `é`, `à`, and other accented characters |
| `QWERTZ` | Germany / Central Europe | Umlauts (`ä`, `ö`, `ü`) and `ß` |
| `SPANISH_QWERTY` | Spain | `ñ`, acute accents, and inverted punctuation |
| `SWEDISH_QWERTY` | Sweden / Nordic | `å`, `ä`, `ö` and the `<` dead-key column |

## Using Layouts with Typogre

Pass the layout name to Typogre's `keyboard` parameter:

```python
from glitchlings import Typogre

# German keyboard layout
typo = Typogre(rate=0.1, keyboard="QWERTZ", seed=42)
typo("Größe und Gemütlichkeit")

# French layout
typo_fr = Typogre(rate=0.1, keyboard="AZERTY", seed=42)
typo_fr("Café résumé")

# Dvorak for ergonomic typo simulation
typo_dv = Typogre(rate=0.1, keyboard="DVORAK", seed=42)
typo_dv("The quick brown fox")
```

## Accessing Layout Data Directly

For custom glitchlings or analysis, access the adjacency maps directly:

```python
from glitchlings.util import KEYNEIGHBORS

# Get the QWERTZ layout
qwertz = getattr(KEYNEIGHBORS, "QWERTZ")

# What's adjacent to 'z' on a German keyboard?
print(qwertz["z"])  # ['a', 's', 'x'] or similar

# All keys in the layout
print(list(qwertz.keys()))
```

!!! note "Lowercase Only"
    Adjacency maps only contain lowercase keys. Call `.lower()` on input before lookups.

## Shift Slippage

Typogre's `shift_slip_rate` parameter simulates holding Shift too long (or releasing it too early), producing bursts like "HEllo" instead of "Hello".

This requires a separate shift map that knows which characters produce which when Shift is held:

```python
from glitchlings import Typogre

# Simulate modifier slippage
typo = Typogre(rate=0.0, shift_slip_rate=0.3, seed=42)
typo("hello world")  # "HELlo world" or similar
```

All bundled layouts have matching shift maps. If you create a custom layout, provide a shift map too.

## Custom Layouts

To add a custom keyboard layout, create a dict mapping each key to its neighbors:

```python
custom_layout = {
    "a": ["q", "w", "s", "z"],
    "b": ["v", "g", "h", "n"],
    # ... all other keys
}
```

Then pass it directly or register it in `KEYNEIGHBORS` for reuse.

## Why Layout Matters

Different keyboards produce different typo patterns:

- **QWERTY** users commonly swap `e/r`, `t/y`, `u/i` (horizontal neighbors)
- **AZERTY** users might hit `q` when reaching for `a` (they're swapped)
- **Dvorak** users have vowels clustered, so vowel-vowel swaps are common

Matching your typo simulation to your target population's keyboard makes corruption more realistic.

## See Also

- [Typogre](glitchlings/typogre.md) — Full Typogre documentation with motor weighting options
- [Monster Manual](monster-manual.md) — Complete glitchling bestiary

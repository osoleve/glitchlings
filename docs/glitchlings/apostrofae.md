# Apostrofae (Pedant – Curlite)

Apostrofae is no longer a standalone glitchling. Instead, it is the
Pedant evolution unlocked by the **Curlite** stone. The form keeps its
signature behaviour—replacing balanced straight quotes, apostrophes, and
backticks with curated smart-quote pairs from the shared lookup
table—while inheriting Pedant's deterministic seeding and pipeline
integration.

- **Scope**: character level (normal ordering via the Pedant pipeline).
- **Summoning**: `Pedant(stone=PedantStone.CURLITE, seed=None)` or
  `Pedant(stone="Curlite", seed=None)`.
- **Behaviour**: scans the input once to find matching straight-quote
  pairs before swapping each boundary with a deterministically sampled
  fancy counterpart. Unpaired glyphs (like contractions) remain
  untouched, preserving readability while exposing formatting mistakes.
- **Usage tips**:
  - Chain Apostrofae after word-level glitchlings so their token
    boundaries stay intact before the decorative swaps run.
  - Reuse the same `seed` (or rely on a `Gaggle` seed) when you need
    reproducible smart-quote layouts for documentation or regression
    tests.

```python
from glitchlings import Pedant
from glitchlings.zoo.pedant import PedantStone

apostrofae = Pedant(stone=PedantStone.CURLITE, seed=404)
apostrofae('"Mind the gap," she whispered.')
```

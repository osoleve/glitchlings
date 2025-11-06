# Pedant

Pedant is a grammar-zealot (or so it thinks) that evolves with new powers
whenever you supply one of the Pedant Stones. Each evolution performs a distinct,
deterministic "cleanup" pass over the input text.

- **Scope**: word level (late ordering).
- **Signature**: `Pedant(stone="Coeurite", seed=None)`.
- **Behaviour**: instantiates a base `Pedant` and evolves it with the chosen
  stone before applying that form's `move(...)`. The default `Coeurite` stone
  unlocks **Aetheria**, which reintroduces ligatures and diaereses such as
  `coöperate` and `Æther`. Other stones trigger alternate evolutions:
  - `Whom Stone` → **Whomst** forces `who` → `whom`.
  - `Fewerite` → **Fewerling** swaps `less` for `fewer` when the surrounding
    text references countable quantities.
  - `Curlite` → **Apostrofae** polishes straight quotes into
    typographic pairs.
  - `Subjunctite` → **Subjunic** corrects subjunctive phrases (`if I was` →
    `if I were`).
  - `Oxfordium` → **Commama** enforces serial commas in simple lists.
  - `Metricite` → **Kiloa** converts mile distances to rounded kilometres with
    matched casing.
  - `Orthogonite` → **Correctopus** unleashes an all-caps final edit.
- **Parameters**:
  - `stone` (default `"Coeurite"`): accepts a `PedantStone` enum member or the
    stone's display label (e.g. `"Whom Stone"` or `"Metricite"`). Parameter names
    `form` and `stone_name` map to the same value.
  - `seed` (optional): feeds deterministic RNG for evolutions that make
    probabilistic choices (Aetheria's diaeresis placement, for example). A
    gaggle-level seed also controls pedant behaviour.
- **Usage tips**:
  - Import `PedantStone` when you want static analysis or autocompletion of the
    available forms; otherwise pass the stone name as a string.
  - The Rust pipeline powers Pedant in production builds; keep the compiled
    extension available so performance stays high even in long pipelines.

```python
from glitchlings import Pedant
from glitchlings.zoo.pedant import PedantStone

whomst = Pedant(stone=PedantStone.WHOM, seed=404)
whomst("Who you gonna call?")  # "Whom you gonna call?"

apostrofae = Pedant(stone=PedantStone.CURLITE, seed=404)
apostrofae('"Mind the gap," she whispered.')

metric = Pedant(stone="Metricite", seed=404)
metric("The trail is 12 miles long.")  # "The trail is 19 kilometres long."
```

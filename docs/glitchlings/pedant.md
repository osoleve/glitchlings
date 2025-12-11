# Pedant

Pedant is a grammar-zealot (or so it thinks) that evolves with new powers
whenever you supply one of the Pedant Stones. Each evolution performs a distinct,
deterministic "cleanup" pass over the input text.

- **Scope**: word level (late ordering).
- **Signature**: `Pedant(stone="Hypercorrectite", seed=None)`.
- **Behaviour**: instantiates a base `Pedant` and evolves it with the chosen
  stone before applying that form's `move(...)`. The default `Hypercorrectite`
  stone unlocks **Andi**, which hypercorrects coordinate-structure pronouns
  ("between you and me" -> "between you and I"). Other stones trigger alternate
  evolutions:
  - `Hypercorrectite` -> **Andi** overcorrects "me" to "I" in coordinate
    structures after prepositions ("for Bob and me" -> "for Bob and I").
  - `Unsplittium` -> **Infinitoad** "corrects" split infinitives
    ("to boldly go" -> "boldly to go" or "to go boldly").
  - `Coeurite` -> **Aetheria** restores archaic ligatures and diaereses
    (`cooperate` -> `cooperate`, `aesthetic` -> `aesthetic`).
  - `Curlite` -> **Apostrofae** polishes straight quotes into
    typographic pairs.
  - `Oxfordium` -> **Commama** enforces serial commas in simple lists.
- **Parameters**:
  - `stone` (default `"Hypercorrectite"`): accepts a `PedantStone` enum member
    or the stone's display label (e.g. `"Coeurite"` or `"Oxfordium"`). Parameter
    names `form` and `stone_name` map to the same value.
  - `seed` (optional): feeds deterministic RNG for evolutions that make
    probabilistic choices (Aetheria's diaeresis placement, Infinitoad's adverb
    placement). A gaggle-level seed also controls pedant behaviour.
- **Usage tips**:
  - Import `PedantStone` when you want static analysis or autocompletion of the
    available forms; otherwise pass the stone name as a string.
  - The Rust pipeline powers Pedant in production builds; keep the compiled
    extension available so performance stays high even in long pipelines.

## Linguistic References

The hypercorrection patterns are grounded in sociolinguistics research:

- Collins, P. (2022). "Hypercorrection in English: an intervarietal corpus-based
  study." *English Language & Linguistics*, 26(2), 279-305.
- Labov, W. (1966). "Hypercorrection by the Lower Middle Class as a Factor in
  Linguistic Change." *Sociolinguistic Patterns*.
- Angermeyer, P.S. & Singler, J.V. (2003). "The case for politeness: Pronoun
  variation in co-ordinate NPs in object position in English." *Language
  Variation and Change*, 15, 171-209.

```python
from glitchlings import Pedant
from glitchlings.zoo.pedant import PedantStone

# Hypercorrect pronouns in coordinate structures
andi = Pedant(stone=PedantStone.HYPERCORRECTITE, seed=404)
andi("between you and me")  # "between you and I"

# "Correct" split infinitives
infinitoad = Pedant(stone=PedantStone.UNSPLITTIUM, seed=404)
infinitoad("to boldly go")  # "boldly to go" or "to go boldly"

# Curly quotes
apostrofae = Pedant(stone=PedantStone.CURLITE, seed=404)
apostrofae('"Mind the gap," she whispered.')
```

# Jargoyle

*"Uh oh. The worst person you know just bought a thesaurus."*

Jargoyle is a lexical shapeshifter that swaps words for their synonyms—or near-synonyms, or vaguely-related terms from themed dictionaries. The result is text that means approximately the same thing but reads like it was written by someone trying too hard.

## Stats

| Attribute | Value |
|-----------|-------|
| **Scope** | Word |
| **Attack Order** | Normal |
| **Signature** | Dictionary-based word swaps |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lexemes` | str | `"synonyms"` | Which dictionary to use for swaps |
| `mode` | str | `"drift"` | `"drift"` for random selection, `"literal"` for first match |
| `rate` | float | 0.01 | Probability of swapping each eligible word |
| `seed` | int | None | Deterministic seed for reproducibility |

## Bundled Dictionaries

Jargoyle ships with several themed lexeme collections:

| Dictionary | Description | Example Swaps |
|------------|-------------|---------------|
| `synonyms` | General synonym substitution | quick → swift, fast → rapid |
| `colors` | Color term variations | red → crimson, blue → azure |
| `corporate` | Business jargon alternatives | use → leverage, problem → challenge |
| `academic` | Scholarly vocabulary | show → demonstrate, think → hypothesize |
| `cyberpunk` | Neon-drenched slang | computer → deck, hacker → razorgirl |
| `lovecraftian` | Cosmic horror terminology | ancient → eldritch, strange → cyclopean |

### Custom Dictionaries

Drop any `*.json` file into `assets/lexemes/` to make it available as a lexeme source. Format:

```json
{
  "word": ["synonym1", "synonym2", "synonym3"],
  "another": ["replacement"]
}
```

List available dictionaries at runtime:

```python
from glitchlings.zoo.jargoyle import list_lexeme_dictionaries
print(list_lexeme_dictionaries())
```

## Modes

**`drift`** (default) — Randomly selects among available synonyms for each word. The `seed` parameter makes this deterministic.

**`literal`** — Always picks the first entry in the dictionary. Fully deterministic regardless of seed—useful when you need identical output across runs without managing seeds.

## Examples

```python
from glitchlings import Jargoyle

# Default: general synonyms with drift
jarg = Jargoyle(rate=0.3, seed=42)
jarg("The quick fox jumps fast over the lazy dog")
# "The swift fox leaps rapid over the indolent dog"

# Color palette shifts
colors = Jargoyle(lexemes="colors", rate=0.5, seed=42)
colors("The red car drove under the blue sky")
# "The crimson car drove under the azure sky"

# Corporate buzzword injection
corp = Jargoyle(lexemes="corporate", rate=0.3, seed=42)
corp("We need to use this tool to fix the problem")
# "We need to leverage this solution to address the challenge"

# Cosmic horror mode
eldritch = Jargoyle(lexemes="lovecraftian", rate=0.4, seed=42)
eldritch("The ancient temple stood in the dark forest")
# "The eldritch fane loomed in the tenebrous wood"
```

## When to Use Jargoyle

**Domain shift testing** — See how your model handles vocabulary it wasn't trained on. Academic ↔ casual, technical ↔ lay terminology.

**Paraphrase robustness** — Test whether your model understands meaning or just memorizes surface patterns.

**Style transfer evaluation** — When you need text that means the same thing but sounds different.

**Data augmentation** — Generate training variants that preserve semantics while varying vocabulary.

## Usage Tips

- Start with `rate=0.01` for subtle drift. Even low rates accumulate—synonym chains can produce surprisingly different text.
- Use `mode="literal"` when you need reproducibility without seed management.
- The `corporate` and `academic` dictionaries are intentionally absurd. They're for testing, not for actual business communications.
- Combine with [Wherewolf](wherewolf.md) to stack semantic drift (Jargoyle) on phonetic drift (Wherewolf).

## Complementary Glitchlings

- **[Wherewolf](wherewolf.md)** — Phonetic substitution vs. semantic substitution
- **[Pedant](pedant.md)** — Grammar-focused hypercorrection alongside vocabulary shifts
- **[Rushmore](rushmore.md)** — Word-level deletions and duplications

## See Also

- [Monster Manual](../monster-manual.md) — Full bestiary with all glitchlings
- [Visual Gallery](../glitchling-gallery.md) — See Jargoyle output at multiple rates

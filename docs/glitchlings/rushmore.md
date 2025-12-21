# Rushmore

*"I accidentally an entire word. You shouldn't have waited until the last minute to write that paper."*

Rushmore is a versatile chaos agent that attacks at the word level. It can delete words, duplicate them, or swap adjacent pairs—simulating the kind of mistakes people make when typing in a hurry, editing carelessly, or dealing with transmission errors.

## Stats

| Attribute | Value |
|-----------|-------|
| **Scope** | Word |
| **Attack Order** | Normal |
| **Signature** | Multi-mode word attacks |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `modes` | str or list | `"delete"` | Attack modes: `"delete"`, `"duplicate"`, `"swap"`, or `"all"` |
| `rate` | float | None | Base rate for all modes (overridden by per-mode rates) |
| `delete_rate` | float | 0.01 | Probability of deleting each word |
| `duplicate_rate` | float | 0.01 | Probability of duplicating each word |
| `swap_rate` | float | 0.5 | Probability of swapping adjacent pairs |
| `unweighted` | bool | False | Sample words uniformly instead of biasing by length |
| `seed` | int | None | Deterministic seed for reproducibility |

## Attack Modes

Rushmore bundles three distinct attacks. Enable any combination with the `modes` parameter.

### Delete Mode

Removes words entirely, leaving gaps in the text. Simulates hasty editing, transmission dropouts, or just not finishing your

```python
from glitchlings import Rushmore

delete = Rushmore(modes="delete", rate=0.1, seed=42)
delete("I found myself transformed in his bed")
# "I found transformed his bed"
```

!!! note "First Word Protection"
    The first word is never deleted—it anchors the sentence. Prepend a throwaway word if you need deletions at the start.

### Duplicate Mode

Repeats words in place, simulating the stutter of a nervous typist or a copy-paste mishap.

```python
dup = Rushmore(modes="duplicate", rate=0.1, seed=42)
dup("The quick brown fox jumps over")
# "The quick quick brown fox jumps over over"
```

### Swap Mode

Exchanges adjacent word pairs, scrambling local order while keeping words intact.

```python
swap = Rushmore(modes="swap", rate=0.3, seed=42)
swap("The quick brown fox jumps over the lazy dog")
# "quick The brown fox over jumps lazy the dog"
```

### Combined Modes

Chain multiple attacks for compound chaos:

```python
# All three modes
chaos = Rushmore(modes="all", rate=0.05, seed=42)

# Or pick specific combinations
chaos = Rushmore(modes=["delete", "duplicate"], rate=0.05, seed=42)
```

Modes execute in order: delete → duplicate → swap. Each operation uses the same RNG, so chained operations remain deterministic.

## Examples

```python
from glitchlings import Rushmore

# Classic deletion (the original Rushmore behavior)
rush = Rushmore(rate=0.1, seed=42)
rush("He found himself transformed in his bed into a horrible vermin")
# "He found himself in bed into a horrible"

# Per-mode rate control
fine = Rushmore(
    modes="all",
    delete_rate=0.02,
    duplicate_rate=0.01,
    swap_rate=0.1,
    seed=42
)

# High-chaos composition
wild = Rushmore(modes="all", rate=0.2, seed=42)
```

## When to Use Rushmore

**Grammar correction testing** — Missing or duplicated words are common writing errors. See if your model can detect and fix them.

**Transmission error simulation** — Dropped packets, incomplete messages, corrupted logs. Rushmore creates the gaps.

**Hasty writing simulation** — First drafts, text messages, notes-to-self. Real humans make these mistakes constantly.

**Sequence robustness** — Does your model understand word order? Swap mode finds out.

## Usage Tips

- Start with `rate=0.01` for subtle corruption. Word-level changes are highly visible even at low rates.
- Use `modes="all"` when you want maximum chaos, but remember that delete + duplicate + swap can make text nearly unreadable.
- Set `unweighted=True` when testing short-word comprehension—by default, longer words are more likely to be selected.
- The first word is protected from deletion to keep sentence structure anchored.

## Legacy Glitchlings

Rushmore consolidates the behavior of three older glitchlings:

| Legacy Name | Equivalent Rushmore Call |
|-------------|--------------------------|
| `Rushmore` (old) | `Rushmore(modes="delete")` |
| `Reduple` | `Rushmore(modes="duplicate")` |
| `Adjax` | `Rushmore(modes="swap")` |

The standalone `Reduple` and `Adjax` glitchlings have been retired. Use Rushmore with the appropriate mode.

## Complementary Glitchlings

- **[Redactyl](redactyl.md)** — Hide words with blocks instead of deleting them
- **[Typogre](typogre.md)** — Character-level corruption after word-level scrambling
- **[Jargoyle](jargoyle.md)** — Replace words with synonyms instead of removing them

## See Also

- [Monster Manual](../monster-manual.md) — Full bestiary with all glitchlings
- [Visual Gallery](../glitchling-gallery.md) — See Rushmore output at multiple rates

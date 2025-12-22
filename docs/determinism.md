# Determinism Guide

Glitchlings are deterministic by design. Same seed + same input = same output, every time, on every machine. This matters because reproducible experiments are the foundation of trustworthy research—and because debugging non-deterministic corruption is a special kind of hell.

## How Seeds Work

Every glitchling owns a private `random.Random` instance. It never touches Python's global RNG state, so glitchlings don't interfere with each other or with your other code.

### Individual Glitchlings

Pass `seed=` on construction:

```python
from glitchlings import Typogre

typo = Typogre(rate=0.1, seed=42)
typo("Hello world")  # Always the same output
typo("Hello world")  # Same again
```

Reset the RNG mid-run with `reset_rng()` if you need to replay:

```python
typo.reset_rng()
typo("Hello world")  # Back to the original output
```

### Gaggles

Pass `seed=` to the Gaggle, and it derives per-glitchling seeds automatically:

```python
from glitchlings import Gaggle, Typogre, Mim1c

gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)
```

The derived seeds depend on:

- The master seed you provide
- Each glitchling's class name
- The order of glitchlings in the roster

!!! warning "Roster Order Matters"
    Changing the order of glitchlings changes their derived seeds, even if the master seed stays the same. If you need identical output, keep the roster order stable.

### Attack Helper

The `Attack` class follows the same pattern:

```python
from glitchlings.attack import Attack
from glitchlings import Typogre

# Seed controls the internal Gaggle
attack = Attack([Typogre(rate=0.02)], seed=404)
result = attack.run("Hello world")  # Reproducible
```

If you pass an existing Gaggle or Glitchling, Attack clones it before applying the seed—so your original instance stays untouched.

### Dataset Corruption

Dataset wrappers inherit their Gaggle's seed:

```python
from glitchlings import Gaggle, Typogre
from glitchlings.dlc.huggingface import GlitchedDataset

gaggle = Gaggle([Typogre(rate=0.02)], seed=404)
corrupted = gaggle.corrupt_dataset(dataset, columns=["text"])
# Reproducible across runs
```

### Rust Pipeline

Seeds are forwarded to the compiled Rust pipeline. Keep your master seed stable across runs, and both Python and Rust will produce identical output.

## Common Pitfalls

### Unstable Ordering

When sampling from a set or dictionary, Python's iteration order can vary. Always sort before sampling:

```python
# BAD: order may vary
candidates = {word for word in text.split()}
selected = rng.sample(list(candidates), 3)

# GOOD: stable order
candidates = sorted(set(text.split()))
selected = rng.sample(candidates, 3)
```

### Global RNG State

Never use `random.choice()` or `random.shuffle()` directly. Always go through the glitchling's `self.rng`:

```python
# BAD: touches global state
import random
selected = random.choice(options)

# GOOD: uses instance RNG
selected = self.rng.choice(options)
```

### Floating-Point Comparisons

If you're making decisions based on `rate < threshold`, remember that floating-point arithmetic isn't always exact. Stick to `<=` or `<` consistently.

### External Data

If your glitchling loads data from a file (like a homophone dictionary), sort the data on load. File system order can vary between machines.

## Debugging Non-Determinism

If your glitchling produces different output for the same seed and input, check these in order:

1. **Set vs. dict iteration** — Sort before sampling
2. **Direct `random` calls** — Route through `self.rng`
3. **Candidate pool ordering** — Sort before shuffle/sample
4. **External file loading** — Sort on read
5. **Insufficient sort keys** — Add secondary keys if primary keys can tie

The test suite includes `tests/core/test_glitchlings_determinism.py` which runs each glitchling multiple times with the same seed and asserts identical output. Run it to verify your changes:

```bash
pytest tests/core/test_glitchlings_determinism.py -v
```

## Quick Checklist

Before shipping a new glitchling or modification:

- [ ] Pass `seed=` on construction
- [ ] Use `self.rng` for all random operations
- [ ] Sort any sets/dicts before sampling
- [ ] Sort external data on load
- [ ] Run the determinism test suite

## See Also

- [Development Guide](development.md) — Testing and contribution workflow
- [Attack Helper](attack.md) — How Attack handles seed propagation

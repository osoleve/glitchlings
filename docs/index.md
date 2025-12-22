# Glitchlings Field Guide

Welcome, brave soul. You've found the field manual for wrangling glitchlings—those mischievous text-corruption creatures that haunt language models and keep evaluations honest.

This guide covers everything from summoning your first glitchling to orchestrating full-scale chaos with the `Gaggle`. If your models have been getting a little too comfortable with clean data, you've come to the right place.

## Installation

Install from PyPI:

```bash
pip install -U glitchlings
```

That's it. You're ready to corrupt.

### Optional Extras

Some glitchlings come with DLC—optional integrations for popular libraries:

```bash
pip install 'glitchlings[hf]'        # Hugging Face datasets
pip install 'glitchlings[torch]'     # PyTorch DataLoader
pip install 'glitchlings[lightning]' # Lightning DataModule
pip install 'glitchlings[langchain]' # LangChain runnables
pip install 'glitchlings[nemo]'      # NVIDIA NeMo DataDesigner
pip install 'glitchlings[prime]'     # Prime Intellect RL environments
pip install 'glitchlings[gutenberg]' # Project Gutenberg
pip install 'glitchlings[all]'       # Everything
```

See [Integrations & DLC](integrations.md) for details on each.

### Development Install

Working from a local clone? Install in editable mode:

```bash
pip install -e .[dev]
```

The full development workflow (virtual environments, Rust tips, testing) lives in the [Development Guide](development.md).

## Quickstart

Glitchlings are callable objects. Summon one, call it on text, get corrupted text back:

```python
from glitchlings import Gaggle, SAMPLE_TEXT, Typogre, Mim1c, Rushmore

gaggle = Gaggle(
    [
        Rushmore(rate=0.01),              # word deletions
        Rushmore(modes="duplicate", duplicate_rate=0.005),
        Mim1c(rate=0.01),                 # unicode confusables
        Typogre(rate=0.02),               # keyboard typos
    ],
    seed=1234,
)

print(gaggle(SAMPLE_TEXT))
```

> Onee morninᶃ, when Gregor Samsa woke from troubleⅾ dreams, he found himself transformed in his bed into a horible ｖermin...

All glitchlings are **deterministic**—pass a `seed` during construction to make the chaos reproducible. Same seed, same input, same output. Every time.

## Meet Auggie

Don't want to memorize signatures? Let my assistant Auggie handle it. Auggie provides a fluent builder interface for composing gaggles:

```python
from glitchlings import Auggie, SAMPLE_TEXT

auggie = (
    Auggie(seed=404)
    .typo(rate=0.015)
    .confusable(rate=0.01)
    .homophone(rate=0.02)
)

print(auggie(SAMPLE_TEXT))
```

Auggie knows all the glitchlings and their quirks. See [Auggie's page](glitchlings/auggie.md) for the full helper list.

## Where to Go Next

**Just getting started?** Explore the [Bestiary](monster-manual.md) to meet each glitchling, or browse the [Visual Gallery](glitchling-gallery.md) to see them in action at different corruption rates.

**Building a pipeline?** Check out:

- [Attack Helper](attack.md) — single-call corruption with tokenization and metrics
- [Pipeline Workflows](pipeline-workflows.md) — integrate with HF datasets, PyTorch, LangChain, and more
- [Configuration Files](configuration.md) — version-controlled YAML attack configs

**Need reproducibility?** Read the [Determinism Guide](determinism.md) for seed hygiene and RNG best practices.

**Prefer the terminal?** The [CLI Reference](cli.md) documents the full `glitchlings` command interface.

## The Gaggle

The `Gaggle` class coordinates multiple glitchlings into a single pipeline:

```python
from glitchlings import Gaggle, Typogre, Mim1c

gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)
result = gaggle("Your text here")
```

**Seed derivation** — Pass `seed=` to the Gaggle and it derives per-glitchling seeds automatically. Same master seed = same corruption, every time.

**Attack ordering** — Glitchlings declare their scope (document, sentence, word, character) and attack order. The Gaggle sorts them automatically so word-level operations happen before character-level ones. Override with `attack_order=[...]` when you need custom choreography.

**Dynamic tuning** — Use `gaggle.set_param("Typogre", "rate", 0.05)` to adjust parameters without rebuilding.

**Summoning shorthand** — Build a gaggle from names or mixed objects:

```python
from glitchlings import summon
gaggle = summon(["typogre", Mim1c(rate=0.01)], seed=404)
```

## The Attack Helper

When you need corruption *plus* metrics, reach for `Attack`:

```python
from glitchlings import Typogre
from glitchlings.attack import Attack

attack = Attack([Typogre(rate=0.02)], seed=404)
result = attack.run("Your text here")

print(result.corrupted)
print(result.metrics["normalized_edit_distance"])
```

Attack tokenizes both clean and corrupted text, computes similarity metrics, and handles transcript-style chat batches. See the [Attack Helper](attack.md) reference for the full API.

## Command Line Interface

Prefer not to write Python? The `glitchlings` CLI exposes the same functionality:

```bash
# List available glitchlings
glitchlings --list

# Apply Typogre to text
glitchlings -g typogre "Your text here"

# Configure inline with kwargs
glitchlings -g "Typogre(rate=0.05)" "Your text here"

# Corrupt a file and show the diff
glitchlings -g typogre --input-file document.txt --diff

# Pipe text through corruption
echo "Some text" | glitchlings -g mim1c

# Get metrics in JSON
glitchlings --attack --sample
```

Full contract in the [CLI Reference](cli.md).

## Testing Before You Ship

Before documenting new glitchlings or publishing changes, run the test suite:

```bash
pytest
```

If the benchmark guard fails on slower hardware, raise the safety margin:

```bash
GLITCHLINGS_BENCHMARK_SAFETY_FACTOR=12 pytest
```

## Further Reading

- [Monster Manual](monster-manual.md) — complete bestiary with flavor text
- [Visual Gallery](glitchling-gallery.md) — side-by-side outputs at multiple rates
- [Analysis Tools](analysis-tools.md) — SeedSweep, GridSearch, and comparison utilities
- [Keyboard Layouts](keyboard-layouts.md) — adjacency maps for Typogre
- [Determinism Guide](determinism.md) — seeds and RNG guidance

# Glitchlings Field Guide

Welcome to the Glitchlings field manual! This guide explains how to install the toolkit, orchestrate chaos with the `Gaggle`, and wrangle the individual glitchlings.

## Table of contents

1. [Installation](#installation)
2. [Quickstart](#quickstart)
3. [Guide map](#guide-map)
4. [The Gaggle orchestrator](#the-gaggle-orchestrator)
5. [Attack helper](#attack-helper)
6. [Command line interface](#command-line-interface)
7. [Glitchling reference](#glitchling-reference)
   - [Auggie](glitchlings/auggie.md)
   - [Typogre](glitchlings/typogre.md)
   - [Hokey](glitchlings/hokey.md)
   - [Mim1c](glitchlings/mim1c.md)
   - [Rushmore](glitchlings/rushmore.md)
   - [Redactyl](glitchlings/redactyl.md)
   - [Jargoyle](glitchlings/jargoyle.md)
   - [Ekkokin](glitchlings/ekkokin.md)
   - [Pedant](glitchlings/pedant.md)
   - [Scannequin](glitchlings/scannequin.md)
   - [Zeedub](glitchlings/zeedub.md)
8. [Testing checklist](#testing-checklist)
9. [Additional resources](#additional-resources)
   - [Glitchling gallery](glitchling-gallery.md)
   - [Keyboard layout reference](keyboard-layouts.md)
   - [Attack helper reference](attack.md)
   - [Dataset workflows](datasets.md)
   - [Integrations and DLC](integrations.md)
   - [Determinism guide](determinism.md)

## Installation

Install the latest release directly from PyPI:

```bash
pip install -U glitchlings
```

### DLC

Install optional dependencies as needed

e.g. to install all optional deps:

```bash
pip install -U 'glitchlings[all]'
```

#### RL Environment DLC

- `prime` for Prime Intellect RL Hub utilities (see [Integrations and DLC](integrations.md))

#### Dataset/Loader Monkeypatching DLC

Wrap popular dataset loaders for seamless, reproducible corruption:

- `hf` for Hugging Face Datasets
- `torch` for PyTorch DataLoader
- `lightning` for Lightning DataModule
- `gutenberg` for Project Gutenberg (Gutendex) corruption helpers

See [Dataset workflows](datasets.md) for details.

### Source install

When working from a local clone, install in editable mode so your changes take effect immediately:

```bash
pip install -e .[dev]
```

Looking for a complete development workflow (virtual environments, test suite, and Rust tips)? Consult the [development setup guide](development.md).

## Quickstart

Glitchlings are callable objects that accept strings (and string-like iterables) and return corrupted copies. Summon a single glitchling or gather multiple into a `Gaggle` to orchestrate compound effects:

```python
from glitchlings import Gaggle, SAMPLE_TEXT, Typogre, Mim1c, Rushmore

gaggle = Gaggle(
    [
        Rushmore(rate=0.01),  # deletions
        Rushmore(modes="duplicate", duplicate_rate=0.005),
        Mim1c(rate=0.01),
        Typogre(rate=0.02),
    ],
    seed=1234,
)

print(gaggle(SAMPLE_TEXT))
```

> Onee morninᶃ, when Gregor Samsa woke from troubleⅾ dreams, he found himself transformed in his bed into a horible ｖermin. He lay onhis armour-like back, and if he lifted his head a little he could see his brown bely, slightlydomed and divided by arches intostiff sections. The bexddihng was hardly able to to cover it and seemed ready to slide off any moment. His many legs, pitifuly thin compared with the size of the rest of him, waved about helplessly as he looked.

All glitchlings are deterministic: pass a `seed` during construction (or on the enclosing `Gaggle`) to make the chaos reproducible.

Glitchlings slot neatly into existing pipelines:

- **Direct invocation** - Instantiate a glitchling (or `Gaggle`) and call it on strings, iterables, or datasets. Keep the seed stable to reproduce every run.
- **Dataset corruption** - Use ``glitchlings.dlc.huggingface.GlitchedDataset`` (or a `Gaggle`'s `.corrupt_dataset`) to perturb Hugging Face `datasets.Dataset` columns. Pass the target column names explicitly.
- **PyTorch data loaders** - Use ``glitchlings.dlc.pytorch.GlitchedDataLoader`` to wrap ``torch.utils.data.DataLoader`` batches. The wrapper infers textual fields automatically or honours explicit column names/indices while leaving other batch data untouched.

## Guide map

- [Attack helper](attack.md) – single-call corruption plus metrics, with transcript-aware batching and tokenizer selection.
- [Dataset workflows](datasets.md) - how to glitch Hugging Face datasets and PyTorch data loaders with the provided wrappers and column selection.
- [Integrations and DLC](integrations.md) - Hugging Face, PyTorch, Lightning, and Prime extras with install commands.
- [Determinism guide](determinism.md) - seed hygiene and RNG guardrails across glitchlings, gaggles, and attacks.

### Command line interface

Prefer not to touch Python? The `glitchlings` CLI exposes the same functionality. Consult the generated [CLI reference](cli.md) for the full contract and live help output:

```bash
# Discover all built-in glitchlings.
glitchlings --list

# Glitch an entire file with Typogre and inspect the unified diff.
glitchlings -g typogre --file documents/report.txt --diff

# Configure glitchlings inline with keyword arguments.
glitchlings -g "Typogre(rate=0.05)" "Ghouls just wanna have fun"

# Pipe text through Mim1c for on-the-fly homoglyph swaps.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c

# Emit an Attack report with metrics, token counts, and tokens (JSON by default).
glitchlings --report json --sample
```

Append `--diff` to render a unified diff comparing the original and corrupted outputs. Combine it with `--color=always` in terminals that support ANSI colours to highlight changes more clearly. Pass glitchling parameters with `-g "Name(arg=value, ...)"` to mirror the Python API without writing code.

## The Gaggle orchestrator

The `Gaggle` class coordinates multiple glitchlings with deterministic sequencing and shared seeding:

- **Seed derivation** - pass `seed=` to `Gaggle(...)` and it will derive per-glitchling seeds via `derive_seed`, ensuring cross-run stability without repeated outputs.
- **Attack scopes & order** – glitchlings declare a scope (`document`, `sentence`, `word`, `character`) and attack order (`early`, `late`, etc.). By default the gaggle sorts by scope, then by order so character-level edits (Typogre, Pedant with Curlite, Mim1c, Scannequin) happen after word-level operations (Rushmore and its duplicate/swap modes, Redactyl, Jargoyle). Override this via `Gaggle([...], attack_order=[...])` when you need bespoke choreography.
- **Dynamic configuration** – use `gaggle.set_param("Typogre", "rate", 0.05)` to tweak nested glitchling parameters without rebuilding the ensemble.
- **Dataset utilities** - wrap datasets with ``glitchlings.dlc.huggingface.GlitchedDataset`` or call `gaggle.corrupt_dataset(dataset, columns=[...])` to clone and perturb Hugging Face datasets while leaving the original untouched. Pass the columns explicitly.
- **Summoning from shorthand** - `glitchlings.summon` lets you build a gaggle from names or partially-configured objects (`summon(["typogre", Mim1c(rate=0.01)], seed=404)`).

Deep integration tests for the orchestration stack live in `tests/test_glitchling_core.py`, and the CLI argument matrix in `tests/test_parameter_effects.py`.

## Attack helper

Use `glitchlings.attack.Attack` when you want a single call that corrupts text, tokenises the before/after, and emits similarity metrics. It mirrors the determinism guarantees of the `Gaggle` and understands chat transcripts. It also accepts plain `list[str]` batches, renders fast `summary()` reports, and ships a `compare(...)` helper for tokenizer matrices. See the dedicated [Attack helper reference](attack.md) for parameters, tokenizer options, and examples.

## Glitchling reference

Each glitchling subclasses the shared `Glitchling` base class and exposes the same interface: call the instance with text, adjust parameters via `set_param`, and rely on deterministic seeds. Dive into the dedicated pages below for signatures, behaviours, and usage tips:

- [Auggie](glitchlings/auggie.md) - behaviour-driven assistant that assembles gaggles with helper methods.
- [Typogre](glitchlings/typogre.md) - keyboard-adjacent typos and doubled characters for fat-finger chaos.
- [Hokey](glitchlings/hokey.md) - expressive lengthening driven by linguistic cues.
- [Mim1c](glitchlings/mim1c.md) - homoglyph swaps that sneak confusable Unicode into your text.
- [Rushmore](glitchlings/rushmore.md) - targeted deletions, reduplications, and swaps with configurable attack modes.
- [Redactyl](glitchlings/redactyl.md) - block out sensitive words with configurable redaction glyphs.
- [Jargoyle](glitchlings/jargoyle.md) - dictionary-driven synonym substitutions for domain drift.
- [Ekkokin](glitchlings/ekkokin.md) - curated homophone swaps that preserve casing and cadence.
- [Pedant](glitchlings/pedant.md) - grammar evolutions driven by themed stones (Whomst, Fewerling, Commama, Kiloa, and more).
- [Scannequin](glitchlings/scannequin.md) - OCR-style misreads and confusable spans with deterministic sampling.
- [Zeedub](glitchlings/zeedub.md) - zero-width glyph injections that hide corruption inside seemingly clean text.

## Testing checklist

Before publishing changes or documenting new glitchlings, run the Pytest suite from the repository root:

```bash
pytest
```

If the Python pipeline regression guard fails on slower hardware, raise the safety margin with `GLITCHLINGS_BENCHMARK_SAFETY_FACTOR` (default: `12`) or set `GLITCHLINGS_BENCHMARK_STRICT=1` to re-enable the historical baseline thresholds.

## Additional resources

- [Monster Manual](monster-manual.md) - complete bestiary with flavour text.
- Repository README (`README.md` in the repository root) - project overview and ASCII ambience.
- [Development setup](development.md) - local environment, testing, and Rust acceleration guide.
- [Glitchling gallery](glitchling-gallery.md) - side-by-side outputs for each glitchling at multiple rates.
- [Keyboard layout reference](keyboard-layouts.md) - available adjacency maps for Typogre and related features.
- [Attack helper reference](attack.md) - single-call corruption + metrics.
- [Dataset workflows](datasets.md) - dataset and loader corruption patterns.
- [Integrations and DLC](integrations.md) - Hugging Face, PyTorch, Lightning, and Prime extras.
- [Determinism guide](determinism.md) - seeds and RNG guidance.

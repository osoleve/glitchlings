# Glitchlings Field Guide

Welcome to the Glitchlings field manual! This guide explains how to install the toolkit, orchestrate chaos with the `Gaggle`, and wrangle the individual glitchlings.

## Table of contents

1. [Installation](#installation)
2. [Quickstart](#quickstart)
3. [The Gaggle orchestrator](#the-gaggle-orchestrator)
4. [Attack helper](#attack-helper)
5. [Declarative attack configurations](#declarative-attack-configurations)
6. [Rust pipeline acceleration](#rust-pipeline-acceleration)
7. [Glitchling reference](#glitchling-reference)
   - [Auggie](glitchlings/auggie.md)
   - [Typogre](glitchlings/typogre.md)
   - [Pedant – Curlite (Apostrofae)](glitchlings/apostrofae.md)
   - [Mim1c](glitchlings/mim1c.md)
   - [Rushmore](glitchlings/rushmore.md)
   - [Redactyl](glitchlings/redactyl.md)
   - [Jargoyle](glitchlings/jargoyle.md)
   - [Ekkokin](glitchlings/ekkokin.md)
   - [Pedant](glitchlings/pedant.md)
   - [Spectroll](glitchlings/spectroll.md)
   - [Scannequin](glitchlings/scannequin.md)
   - [Zeedub](glitchlings/zeedub.md)
8. [Dataset workflows](#dataset-workflows)
9. [Integrations and DLC](#integrations-and-dlc)
10. [Ensuring determinism](#ensuring-determinism)
11. [Testing checklist](#testing-checklist)
12. [Additional resources](#additional-resources)
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

- `prime` for Prime Intellect RL Hub utilities (see [Prime Intellect integration](#prime-intellect-integration))

#### Dataset/Loader Monkeypatching DLC

Add a `.glitch(...)` method to popular dataset loaders for seamless, reproducible corruption:

- `hf` for Hugging Face Datasets
- `torch` for PyTorch DataLoader
- `lightning` for Lightning DataModule

See [Dataset workflows](#dataset-workflows) for details.

#### Lexicon Backend DLC

- `vectors` for spaCy/gensim lexicon building
- `st` for SentenceTransformer lexicon caches

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

- **Direct invocation** – Instantiate a glitchling (or `Gaggle`) and call it on strings, iterables, or datasets. Keep the seed stable to reproduce every run.
- **Dataset corruption** – After ``import glitchlings.dlc.huggingface`` registers the extension, call ``Dataset.glitch(...)`` (or a `Gaggle`'s `.corrupt_dataset`) to perturb a Hugging Face `datasets.Dataset` and return a corrupted copy for training or evaluation.
- **PyTorch data loaders** – Import ``glitchlings.dlc.pytorch`` to patch ``torch.utils.data.DataLoader.glitch(...)``. The wrapper infers textual fields automatically or honours explicit column names/indices while leaving other batch data untouched.

### Command line interface

Prefer not to touch Python? The `glitchlings` CLI exposes the same functionality:

```bash
# Discover all built-in glitchlings.
glitchlings --list

# Glitch an entire file with Typogre and inspect the unified diff.
glitchlings -g typogre --file documents/report.txt --diff

# Configure glitchlings inline with keyword arguments.
glitchlings -g "Typogre(rate=0.05)" "Ghouls just wanna have fun"

# Pipe text through Mim1c for on-the-fly homoglyph swaps.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c
```

Append `--diff` to render a unified diff comparing the original and corrupted outputs. Combine it with `--color=always` in terminals that support ANSI colours to highlight changes more clearly. Pass glitchling parameters with `-g "Name(arg=value, ...)"` to mirror the Python API without writing code.

## The Gaggle orchestrator

The `Gaggle` class coordinates multiple glitchlings with deterministic sequencing and shared seeding:

- **Seed derivation** - pass `seed=` to `Gaggle(...)` and it will derive per-glitchling seeds via `derive_seed`, ensuring cross-run stability without repeated outputs.
- **Attack scopes & order** – glitchlings declare a scope (`document`, `sentence`, `word`, `character`) and attack order (`early`, `late`, etc.). By default the gaggle sorts by scope, then by order so character-level edits (Typogre, Pedant with Curlite, Mim1c, Scannequin) happen after word-level operations (Rushmore and its duplicate/swap modes, Redactyl, Jargoyle). Override this via `Gaggle([...], attack_order=[...])` when you need bespoke choreography.
- **Dynamic configuration** – use `gaggle.set_param("Typogre", "rate", 0.05)` to tweak nested glitchling parameters without rebuilding the ensemble.
- **Dataset utilities** - after importing ``glitchlings.dlc.huggingface``, call ``dataset.glitch(...)`` (or `gaggle.corrupt_dataset(dataset, columns=[...])`) to clone and perturb Hugging Face datasets while leaving the original untouched. Column inference automatically targets `text`, `prompt`, or similar string columns when none are provided.
- **Summoning from shorthand** - `glitchlings.summon` lets you build a gaggle from names or partially-configured objects (`summon(["typogre", Mim1c(rate=0.01)], seed=404)`).

Deep integration tests for the orchestration stack live in `tests/test_glitchling_core.py`, and the CLI argument matrix in `tests/test_parameter_effects.py`.

## Attack helper

Use `glitchlings.attack.Attack` when you want a single call that corrupts text, tokenises the before/after, and emits similarity metrics. It wraps your glitchlings (or a `Gaggle`) and exposes:

- **Deterministic seeding** – pass `seed=` to stabilise the gaggle Attack builds; existing gaggles/glitchlings have their RNGs reset when seeded.
- **Transcript-aware batching** – chat transcripts are treated as batches and metrics return one value per turn.
- **Modern default tokenization** – defaults to a `tiktoken` encoder (`o200k_base`, falling back to `cl100k_base`, then whitespace).

See the dedicated [Attack helper reference](attack.md) for full details and examples.

## Declarative attack configurations

Keep repeatable experiments outside your codebase by describing rosters in YAML. Each entry can either reference a built-in glitchling by name (with optional keyword arguments) or provide a mapping with `name` plus parameters:

```yaml
seed: 2024
glitchlings:
  - "Typogre(rate=0.03)"
  - name: Rushmore
    parameters:
      rate: 0.08
      unweighted: true
  - name: Zeedub
    rate: 0.01          # top-level keys become parameters when `parameters` is omitted
```

Feed the file to the CLI with:

```bash
glitchlings --config experiments/story-mode.yaml --diff "Here be dragons."
```

Omit `--seed` to honour the configuration's `seed`; supply `--seed` to override it on the fly while keeping the same roster. In Python, load the same file with `glitchlings.load_attack_config(path)` and convert it into a callable `Gaggle` via `glitchlings.build_gaggle(...)`.

Configuration files are now validated against a JSON Schema before any glitchlings are instantiated. Unknown top-level keys raise an error, and each mapping entry must define a `name`. The schema is exposed as `glitchlings.config.ATTACK_CONFIG_SCHEMA` if you want to reuse it in external tooling.

## Rust pipeline acceleration

The refactored Rust pipeline batches compatible glitchlings in a single PyO3 call so large datasets spend less time bouncing between Python and Rust. The orchestrator now requires this compiled extension, so build the PyO3 crate before running Glitchlings.

`tests/test_rust_backed_glitchlings.py` exercises the Rust-backed glitchlings to ensure the accelerated implementations remain stable.

## Glitchling reference

Each glitchling subclasses the shared `Glitchling` base class and exposes the same interface: call the instance with text, adjust parameters via `set_param`, and rely on deterministic seeds. Dive into the dedicated pages below for signatures, behaviours, and usage tips:

- [Auggie](glitchlings/auggie.md) - behaviour-driven assistant that assembles gaggles with helper methods.
- [Typogre](glitchlings/typogre.md) - keyboard-adjacent typos and doubled characters for fat-finger chaos.
- [Pedant – Curlite (Apostrofae)](glitchlings/apostrofae.md) - deterministic smart-quote swaps pulled from a shared fancy-quote lookup.
- [Mim1c](glitchlings/mim1c.md) - homoglyph swaps that sneak confusable Unicode into your text.
- [Rushmore](glitchlings/rushmore.md) - targeted deletions, reduplications, and swaps with configurable attack modes.
- [Redactyl](glitchlings/redactyl.md) - block out sensitive words with configurable redaction glyphs.
- [Jargoyle](glitchlings/jargoyle.md) - lexicon-driven synonym substitutions tuned by part of speech.
- [Ekkokin](glitchlings/ekkokin.md) - curated homophone swaps that preserve casing and cadence.
- [Pedant](glitchlings/pedant.md) - grammar evolutions driven by themed stones (Whomst, Fewerling, Commama, Kiloa, and more).
- [Scannequin](glitchlings/scannequin.md) - OCR-style misreads and confusable spans with deterministic sampling.
- [Zeedub](glitchlings/zeedub.md) - zero-width glyph injections that hide corruption inside seemingly clean text.

## Dataset workflows

Leverage the Hugging Face and PyTorch integrations to perturb large corpora reproducibly. See the dedicated [dataset workflows guide](datasets.md) for examples and tips, including column inference, saving corrupted copies, and seed hygiene.

## Integrations and DLC

Optional extras patch popular libraries to make corruption frictionless. See [Integrations and DLC](integrations.md) for Hugging Face, PyTorch, Lightning, and Prime details plus install commands.

## Ensuring determinism

- Derive seeds from the surrounding context (`Gaggle.derive_seed`) when spawning new RNGs.
- Stabilise candidate order before sampling subsets to keep runs reproducible.
- Use `set_param` to expose tunable values so they can be reset between tests.
- When writing new glitchlings, route randomness through the instance RNG rather than module-level state.

These determinism checks are enforced in `tests/test_glitchlings_determinism.py`. For a deeper checklist (including Attack seeds and dataset corruption), see the [Determinism guide](determinism.md).

## Testing checklist

Before publishing changes or documenting new glitchlings, run the Pytest suite from the repository root:

```bash
pytest
```

If the Python pipeline regression guard fails on slower hardware, raise the safety margin with `GLITCHLINGS_BENCHMARK_SAFETY_FACTOR` (default: `12`) or set `GLITCHLINGS_BENCHMARK_STRICT=1` to re-enable the historical baseline thresholds.

Lexicon-specific regressions live in `tests/test_lexicon_metrics.py`; they verify that new backends stay within striking distance of the recorded synonym diversity, coverage, and cosine-similarity baselines. Pair them with `tests/test_jargoyle.py::test_jargoyle_custom_lexicon_deterministic` when validating alternative backends in the Jargoyle pipeline.

Want to compare against the legacy WordNet lexicon? Install `nltk` and download the corpus manually (`python -m nltk.downloader wordnet`), then add `"wordnet"` to the `lexicon.priority` list in `config.toml`.

## Additional resources

- Monster Manual (`MONSTER_MANUAL.md` in the repository root) - complete bestiary with flavour text.
- Repository README (`README.md` in the repository root) - project overview and ASCII ambience.
- [Development setup](development.md) - local environment, testing, and Rust acceleration guide.
- [Glitchling gallery](glitchling-gallery.md) - side-by-side outputs for each glitchling at multiple rates.
- [Keyboard layout reference](keyboard-layouts.md) - available adjacency maps for Typogre and related features.
- [Attack helper reference](attack.md) - single-call corruption + metrics.
- [Dataset workflows](datasets.md) - dataset and loader corruption patterns.
- [Integrations and DLC](integrations.md) - Hugging Face, PyTorch, Lightning, and Prime extras.
- [Determinism guide](determinism.md) - seeds and RNG guidance.

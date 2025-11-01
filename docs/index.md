# Glitchlings Field Guide

Welcome to the Glitchlings field manual! This guide explains how to install the toolkit, orchestrate chaos with the `Gaggle`, and wrangle the individual glitchlings.

## Table of contents

1. [Installation](#installation)
2. [Quickstart](#quickstart)
3. [Rust pipeline acceleration](#rust-pipeline-acceleration)
4. [The Gaggle orchestrator](#the-gaggle-orchestrator)
5. [Declarative attack configurations](#declarative-attack-configurations)
6. [Glitchling reference](#glitchling-reference)
   - [Typogre](glitchlings/typogre.md)
   - [Apostrofae](glitchlings/apostrofae.md)
   - [Mim1c](glitchlings/mim1c.md)
   - [Reduple](glitchlings/reduple.md)
   - [Adjax](glitchlings/adjax.md)
   - [Rushmore](glitchlings/rushmore.md)
   - [Redactyl](glitchlings/redactyl.md)
   - [Jargoyle](glitchlings/jargoyle.md)
   - [Ekkokin](glitchlings/ekkokin.md)
   - [Scannequin](glitchlings/scannequin.md)
   - [Zeedub](glitchlings/zeedub.md)
7. [Dataset workflows](#dataset-workflows)
8. [Prime Intellect integration](#prime-intellect-integration)
9. [Ensuring determinism](#ensuring-determinism)
10. [Testing checklist](#testing-checklist)
11. [Additional resources](#additional-resources)
    - [Glitchling gallery](glitchling-gallery.md)
    - [Keyboard layout reference](keyboard-layouts.md)

## Installation

Install the latest release directly from PyPI:

```bash
pip install -U glitchlings
```

Need the optional Prime Intellect loader or extra lexicon tooling?

```bash
# Prime Intellect DLC + verifiers dependency
pip install -U 'glitchlings[prime]'

# Embedding-based lexicon helpers (spaCy/gensim + NumPy)
pip install -U 'glitchlings[vectors]'

# SentenceTransformer-backed cache builder
pip install -U 'glitchlings[st]'

# Optional: NLTK WordNet corpora if you want the legacy synonym backend
python -m nltk.downloader wordnet
```

### Precomputing vector lexicon caches

The vector backend prefers cached nearest neighbours for fast, deterministic lookups. Build a cache from a spaCy pipeline or a gensim `KeyedVectors` file:

```bash
glitchlings build-lexicon \
    --source spacy:en_core_web_md \
    --output data/vector_lexicon.json \
    --overwrite
```

Provide a newline-delimited vocabulary with `--tokens words.txt` when you only care about a subset of words, or point `--source` at a KeyedVectors/word2vec file to work from pre-trained embeddings stored on disk. SentenceTransformer checkpoints are supported via `--source sentence-transformers:<model>` (pair them with `--tokens` to define the vocabulary). The repo ships a compact default cache (`lexicon/data/default_vector_cache.json`) derived from the `sentence-transformers/all-mpnet-base-v2` model so the CLI and tests work out of the box; regenerate it when you have richer embeddings or bespoke vocabularies.

### Lexicon evaluation metrics

Compare alternative synonym sources or refreshed caches with `glitchlings.lexicon.metrics`. The `compare_lexicons(...)` helper reports average synonym diversity, the share of tokens with three or more substitutes, and mean cosine similarity using any embedding table you pass in. These utilities underpin the lexicon regression tests so new backends stay deterministic without sacrificing coverage or semantic cohesion.

### Source install

When working from a local clone, install in editable mode so your changes take effect immediately:

```bash
pip install -e .
```

Looking for a complete development workflow (virtual environments, test suite, and Rust tips)? Consult the [development setup guide](development.md).

## Quickstart

Glitchlings are callable objects that accept strings (and string-like iterables) and return corrupted copies. Summon a single glitchling or gather multiple into a `Gaggle` to orchestrate compound effects:

```python
from glitchlings import Gaggle, SAMPLE_TEXT, Typogre, Mim1c, Reduple, Rushmore

gaggle = Gaggle([
    Typogre(rate=0.02),
    Mim1c(rate=0.01),
    Reduple(rate=0.005),
    Rushmore(rate=0.005),
], seed=1234)

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

## Rust pipeline acceleration

The refactored Rust pipeline batches compatible glitchlings in a single PyO3 call so large datasets spend less time bouncing between Python and Rust. When the compiled extension is present, `Gaggle` automatically prefers this fast path.

Parity with the pure-Python pipeline is asserted in `tests/test_rust_backed_glitchlings.py`.

1. Compile the Rust crate once per environment:

   ```bash
   maturin develop -m rust/zoo/Cargo.toml
   ```

   Re-run the command after switching Python versions or pulling changes that touch the Rust sources.

2. Opt out temporarily (for debugging or profiling) by exporting `GLITCHLINGS_RUST_PIPELINE=0` (accepted values: `0`, `false`, `no`, `off`). Any truthy value re-enables the accelerator, while the default is enabled when the extension imports successfully.

Supported operations and their Rust counterparts:

- `Reduple` (`type: "reduplicate"`) – deterministic word reduplication with optional length weighting.
- `Rushmore` (`type: "delete"`) – word deletions that retain punctuation spacing.
- `Redactyl` (`type: "redact"`) – block-character redactions with merge and weighting controls.
- `Adjax` (`type: "swap_adjacent"`) – adjacent word-core swaps that respect affixes.
- `Scannequin` (`type: "ocr"`) – OCR-style confusions sourced from the shared lookup table.
- `Typogre` (`type: "typo"`) – character-level fat-finger edits preserving the configured keyboard layout.
- `Zeedub` (`type: "zwj"`) – zero-width glyph injections with per-glitchling palettes.

Glitchlings that do not expose a pipeline descriptor (including custom subclasses) continue to run on the Python orchestrator automatically, and mixed rosters downgrade gracefully when any member lacks Rust support.


## The Gaggle orchestrator

The `Gaggle` class coordinates multiple glitchlings with deterministic sequencing and shared seeding:

- **Seed derivation** - pass `seed=` to `Gaggle(...)` and it will derive per-glitchling seeds via `derive_seed`, ensuring cross-run stability without repeated outputs.
- **Attack scopes & order** – glitchlings declare a scope (`document`, `sentence`, `word`, `character`) and attack order (`early`, `late`, etc.). By default the gaggle sorts by scope, then by order so character-level edits (Typogre, Apostrofae, Mim1c, Scannequin) happen after word-level operations (Reduple, Adjax, Rushmore, Redactyl, Jargoyle). Override this via `Gaggle([...], attack_order=[...])` when you need bespoke choreography.
- **Dynamic configuration** – use `gaggle.set_param("Typogre", "rate", 0.05)` to tweak nested glitchling parameters without rebuilding the ensemble.
- **Dataset utilities** - after importing ``glitchlings.dlc.huggingface``, call ``dataset.glitch(...)`` (or `gaggle.corrupt_dataset(dataset, columns=[...])`) to clone and perturb Hugging Face datasets while leaving the original untouched. Column inference automatically targets `text`, `prompt`, or similar string columns when none are provided.
- **Summoning from shorthand** - `glitchlings.summon` lets you build a gaggle from names or partially-configured objects (`summon(["typogre", Mim1c(rate=0.01)], seed=404)`).

Deep integration tests for the orchestration stack live in `tests/test_glitchling_core.py`, and the CLI argument matrix in `tests/test_parameter_effects.py`.

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

## Glitchling reference

Each glitchling subclasses the shared `Glitchling` base class and exposes the same interface: call the instance with text, adjust parameters via `set_param`, and rely on deterministic seeds. Dive into the dedicated pages below for signatures, behaviours, and usage tips:

- [Typogre](glitchlings/typogre.md) - keyboard-adjacent typos and doubled characters for fat-finger chaos.
- [Apostrofae](glitchlings/apostrofae.md) - deterministic smart-quote swaps pulled from a shared fancy-quote lookup.
- [Mim1c](glitchlings/mim1c.md) - homoglyph swaps that sneak confusable Unicode into your text.
- [Reduple](glitchlings/reduple.md) - word-level reduplication for hesitant transcripts.
- [Rushmore](glitchlings/rushmore.md) - targeted deletions that erode context without shredding structure.
- [Redactyl](glitchlings/redactyl.md) - block out sensitive words with configurable redaction glyphs.
- [Jargoyle](glitchlings/jargoyle.md) - lexicon-driven synonym substitutions tuned by part of speech.
- [Ekkokin](glitchlings/ekkokin.md) - curated homophone swaps that preserve casing and cadence.
- [Scannequin](glitchlings/scannequin.md) - OCR-style misreads and confusable spans with deterministic sampling.
- [Zeedub](glitchlings/zeedub.md) - zero-width glyph injections that hide corruption inside seemingly clean text.
## Dataset workflows

Leverage the Hugging Face integration to perturb large corpora reproducibly:

```python
from datasets import load_dataset
from glitchlings import Gaggle, Typogre, Mim1c

dataset = load_dataset("ag_news")
gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)

corrupted = gaggle.corrupt_dataset(
    dataset,
    columns=["text"],
    description="ag_news with typographic noise",
)
```

Key points:

- When `columns` is omitted, Glitchlings infers targets (`prompt`, `question`, or all string columns) using `_resolve_columns` semantics from the Prime loader.
- The returned dataset is a shallow copy containing both clean and corrupted columns-persist it with `corrupted.push_to_hub(...)` or `corrupted.save_to_disk(...)`.
- Use dataset-level seeds (`seed=` on the gaggle) so repeated corruptions are stable across machines.

Integration coverage for Hugging Face datasets lives in `tests/test_dataset_corruption.py`, while the DLC-specific loaders are exercised in `tests/test_huggingface_dlc.py`.

## Prime Intellect integration

Installing the `prime` extra exposes `glitchlings.dlc.prime.load_environment`, a convenience wrapper around `verifiers.load_environment` that lets you pre-inject glitchlings into benchmark datasets.

```python
from glitchlings import Mim1c, Typogre
from glitchlings.dlc.prime import (
    Difficulty,
    echo_chamber,
    load_environment,
    tutorial_level,
)

# Load an existing environment and apply custom corruption
custom_env = load_environment(
    "osoleve/syllabify-en",
    glitchlings=[Mim1c(rate=0.01), Typogre(rate=0.02)],
    seed=404,
    columns=["prompt"],  # optional; inferred when omitted
)

# Or convert a Hugging Face dataset column into an Echo Chamber
restoration_env = echo_chamber(
    "osoleve/clean-room",
    column="text",
    glitchlings=["Typogre", "Mim1c"],
    reward_function=lambda prompt, completion, answer: float(completion == answer),
)
```

Capabilities at a glance:

- **Flexible inputs** – pass a string environment slug, an instantiated `verifiers.Environment`, a single glitchling, a list of glitchlings or names, or a pre-built `Gaggle`.
- **Column inference** – when `columns` is `None`, the loader searches for `prompt`/`question` columns, otherwise falls back to all string-valued columns. Explicitly list columns to target subsets (e.g., prompts but not references).
- **Deterministic summoning** – non-`Gaggle` inputs are normalised via `summon(...)` with the provided `seed`, so repeated calls produce matching corruption ensembles.
- **Tutorial difficulty scaling** – `tutorial_level` wires in tuned Mim1c/Typogre parameters multiplied by the selected `Difficulty` enum. Use `Difficulty.Easy` for gentle practice or `Difficulty.Extreme` to hammer robustness.
- **Dataset mutation** – environments are returned with their dataset replaced by the corrupted clone. Skip the `glitchlings` argument to leave the dataset untouched.
- **Echo Chambers** – bootstrap text-cleaning challenges straight from Hugging Face datasets; the environment instructs models to restore glitch-corrupted text, scores responses with a symmetric Damerau–Levenshtein rubric by default, and lets you swap in bespoke reward functions when needed.

## Ensuring determinism

- Derive seeds from the surrounding context (`Gaggle.derive_seed`) when spawning new RNGs.
- Stabilise candidate order before sampling subsets to keep runs reproducible.
- Use `set_param` to expose tunable values so they can be reset between tests.
- When writing new glitchlings, route randomness through the instance RNG rather than module-level state.

These determinism checks are enforced in `tests/test_glitchlings_determinism.py`.

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

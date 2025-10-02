# Glitchlings Usage Guide

Welcome to the Glitchlings field manual! This GitHub Pages-ready guide explains how to install the toolkit, orchestrate chaos with the `Gaggle`, and wield every individual glitchling (Typogre, Mim1c, Reduple, Rushmore, Redactyl, Jargoyle, and Scannequin). It closes with deep coverage of the optional Prime Intellect integration so you can perturb verifier datasets with confidence.

## Table of contents

1. [Installation](#installation)
2. [Quickstart](#quickstart)
3. [The Gaggle orchestrator](#the-gaggle-orchestrator)
4. [Glitchling reference](#glitchling-reference)
   - [Typogre](#typogre)
   - [Mim1c](#mim1c)
   - [Reduple](#reduple)
   - [Rushmore](#rushmore)
   - [Redactyl](#redactyl)
   - [Jargoyle](#jargoyle)
   - [Scannequin](#scannequin)
5. [Dataset workflows](#dataset-workflows)
6. [Prime Intellect integration](#prime-intellect-integration)
7. [Ensuring determinism](#ensuring-determinism)
8. [Testing checklist](#testing-checklist)
9. [Additional resources](#additional-resources)

## Installation

Install the latest release directly from PyPI:

```bash
pip install -U glitchlings
```

Need the optional Prime Intellect loader or the NLTK-powered Jargoyle ready to go? Pull in the documented extras:

```bash
# Prime Intellect DLC + verifiers dependency
pip install -U 'glitchlings[prime]'

# NLTK WordNet corpora for Jargoyle synonym swaps
python -m nltk.downloader wordnet
```

### Source install

When working from a local clone, install in editable mode so your changes take effect immediately:

```bash
pip install -e .
```

If you plan to experiment with the PyO3 acceleration crates, install `maturin` and run `maturin develop` from each crate directory inside the `rust/` folder to compile the optional Rust fast paths.

## Quickstart

Glitchlings are callable objects that accept strings (and string-like iterables) and return corrupted copies. Summon a single glitchling or gather multiple into a `Gaggle` to orchestrate compound effects:

```python
from glitchlings import Gaggle, SAMPLE_TEXT, Typogre, Mim1c, Reduple, Rushmore

gaggle = Gaggle([
    Typogre(max_change_rate=0.03),
    Mim1c(replacement_rate=0.02),
    Reduple(seed=404),
    Rushmore(max_deletion_rate=0.02),
], seed=1234)

print(gaggle(SAMPLE_TEXT))
```

All glitchlings are deterministic: pass a `seed` during construction (or on the enclosing `Gaggle`) to make the chaos reproducible.

### Command line interface

Prefer not to touch Python? The `glitchlings` CLI exposes the same functionality:

```bash
# Discover all built-in glitchlings.
glitchlings --list

# Glitch an entire file with Typogre and inspect the unified diff.
glitchlings -g typogre --file documents/report.txt --diff

# Pipe text through Mim1c for on-the-fly homoglyph swaps.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c
```

Append `--diff` to render a unified diff comparing the original and corrupted outputs. Combine it with `--color=always` in terminals that support ANSI colours to highlight changes more clearly.

## The Gaggle orchestrator

The `Gaggle` class coordinates multiple glitchlings with deterministic sequencing and shared seeding:

- **Seed derivation** – pass `seed=` to `Gaggle(...)` and it will derive per-glitchling seeds via `derive_seed`, ensuring cross-run stability without repeated outputs.
- **Attack scopes & order** – glitchlings declare a scope (`document`, `sentence`, `word`, `character`) and attack order (`early`, `late`, etc.). By default the gaggle sorts by scope, then by order so character-level edits (Typogre, Mim1c, Scannequin) happen after word-level operations (Reduple, Rushmore, Redactyl, Jargoyle). Override this via `Gaggle([...], attack_order=[...])` when you need bespoke choreography.
- **Dynamic configuration** – use `gaggle.set_param("Typogre", "max_change_rate", 0.05)` to tweak nested glitchling parameters without rebuilding the ensemble.
- **Dataset utilities** – call `gaggle.corrupt_dataset(dataset, columns=[...])` to clone and perturb Hugging Face datasets while leaving the original untouched. Column inference automatically targets `text`, `prompt`, or similar string columns when none are provided.
- **Summoning from shorthand** – `glitchlings.summon` lets you build a gaggle from names or partially-configured objects (`summon(["typogre", Mim1c(replacement_rate=0.01)], seed=404)`).

## Glitchling reference

Each glitchling subclasses the shared `Glitchling` base class and exposes the same interface: call the instance with text, adjust parameters via `set_param`, and rely on deterministic seeds. This section summarises every built-in creature, its defaults, and practical usage notes.

### Typogre

- **Scope**: character level (early in the pipeline).
- **Signature**: `Typogre(max_change_rate=0.02, keyboard="CURATOR_QWERTY", seed=None)`.
- **Behaviour**: simulates fat-finger typing by swapping neighbouring keys, dropping spaces, inserting doubles, or choosing layout-adjacent characters. Keyboard layouts map through `glitchlings.util.KEYNEIGHBORS` and include curated QWERTY, DVORAK, and custom research boards.
- **Usage tips**:
  - Lower `max_change_rate` (0.005–0.01) for gentle noise; raise it for more chaotic misspellings.
  - Swap to `keyboard="DVORAK"` or supply a custom adjacency dict to model alternative hardware.
  - Combine with Rushmore deletions to simulate hurried note-taking.

### Mim1c

- **Scope**: character level (late attack order so it acts after insertions/deletions).
- **Signature**: `Mim1c(replacement_rate=0.02, classes=None, seed=None)`.
- **Behaviour**: replaces alphanumeric characters with visually confusable Unicode homoglyphs via `confusable_homoglyphs` (e.g., `A → Α`, `e → е`). When `classes` is omitted it targets Latin, Greek, and Cyrillic scripts; pass `classes="all"` to consider every alias.
- **Usage tips**:
  - Restrict `classes` (e.g., `classes=["LATIN"]`) when evaluation pipelines reject non-Latin scripts.
  - Keep `replacement_rate` below 0.03 for legible perturbations; higher values can break tokenisers that expect ASCII.
  - Pairs well with Typogre for keyboard + homoglyph chaos.

### Reduple

- **Scope**: word level.
- **Signature**: `Reduple(reduplication_rate=0.05, seed=None)`.
- **Behaviour**: randomly repeats words (“reduplication”) to mimic stuttering transcripts or speech disfluencies while preserving whitespace and punctuation.
- **Usage tips**:
  - Use `reduplication_rate=0.01` to emulate occasional hesitations; bump to ≥0.08 for heavy repetition stress tests.
  - Because edits preserve separators, downstream whitespace-sensitive parsers remain stable.
  - Combine with Jargoyle to mix synonym swaps and repeated words for lexical drift.

### Rushmore

- **Scope**: word level.
- **Signature**: `Rushmore(max_deletion_rate=0.01, seed=None)`.
- **Behaviour**: deletes randomly selected words (skipping the first to preserve context) and tidies double spaces/punctuation afterwards.
- **Usage tips**:
  - Keep `max_deletion_rate` conservative (<0.03) to avoid stripping sentences bare.
  - Because the first word is preserved, prepend short context sentences when you need deletions deeper in the passage.
  - Sandwich between Reduple and Redactyl to test summarisation robustness under missing context.

### Redactyl

- **Scope**: word level.
- **Signature**: `Redactyl(replacement_char="█", redaction_rate=0.05, merge_adjacent=False, seed=151)`.
- **Behaviour**: replaces the core characters of selected words with a replacement glyph (default FULL BLOCK) to simulate document redaction. Optionally merges adjacent redaction blocks across punctuation.
- **Usage tips**:
  - Switch `replacement_char` to `_` or `*` when terminals struggle with block glyphs.
  - Enable `merge_adjacent=True` to form continuous bars when redacting phrases.
  - When no redactable words exist, the underlying implementation raises a `ValueError`—wrap calls with try/except in automated pipelines.

### Jargoyle

- **Scope**: word level.
- **Signature**: `Jargoyle(replacement_rate=0.1, part_of_speech="n", seed=None)`.
- **Behaviour**: swaps nouns/verbs/adjectives/adverbs with WordNet synonyms. Downloads the WordNet corpus on demand when missing and maintains deterministic sampling by sorting candidate lemmas.
- **Usage tips**:
  - Target specific POS tags (e.g., `part_of_speech=("n", "v")`) to limit changes to content words.
  - Lower `replacement_rate` (0.02–0.05) for subtle lexical variety; higher rates explore paraphrasing extremes.
  - Ensure your environment has the WordNet data pre-cached to avoid first-run download delays.

### Scannequin

- **Scope**: character level (late order).
- **Signature**: `Scannequin(error_rate=0.02, seed=None)`.
- **Behaviour**: introduces OCR-style confusion pairs (rn↔m, cl↔d, O↔0, curly quotes to ASCII, etc.) using deterministic span selection. Supports a Rust acceleration path when compiled.
- **Usage tips**:
  - Bump `error_rate` for scanned-document stress tests or reduce it for light OCR noise.
  - Because replacements can change token length, run Scannequin after word-level glitchlings to avoid offset drift.
  - Combine with Redactyl to mimic heavily redacted, poorly scanned archives.

## Dataset workflows

Leverage the Hugging Face integration to perturb large corpora reproducibly:

```python
from datasets import load_dataset
from glitchlings import Gaggle, Typogre, Mim1c

dataset = load_dataset("ag_news")
gaggle = Gaggle([Typogre(max_change_rate=0.02), Mim1c(replacement_rate=0.01)], seed=404)

corrupted = gaggle.corrupt_dataset(
    dataset,
    columns=["text"],
    description="ag_news with typographic noise",
)
```

Key points:

- When `columns` is omitted, Glitchlings infers targets (`prompt`, `question`, or all string columns) using `_resolve_columns` semantics from the Prime loader.
- The returned dataset is a shallow copy containing both clean and corrupted columns—persist it with `corrupted.push_to_hub(...)` or `corrupted.save_to_disk(...)`.
- Use dataset-level seeds (`seed=` on the gaggle) so repeated corruptions are stable across machines.

## Prime Intellect integration

Installing the `prime` extra exposes `glitchlings.dlc.prime.load_environment`, a convenience wrapper around `verifiers.load_environment` that lets you pre-inject glitchlings into benchmark datasets.

```python
from glitchlings import Mim1c, Typogre
from glitchlings.dlc.prime import load_environment, tutorial_level, Difficulty

# Load an existing environment and apply custom corruption
custom_env = load_environment(
    "osoleve/syllabify-en",
    glitchlings=[Mim1c(replacement_rate=0.01), Typogre(max_change_rate=0.02)],
    seed=404,
    columns=["prompt"],  # optional; inferred when omitted
)

# Or bootstrap a difficulty-scaled tutorial environment
practice_env = tutorial_level(
    "osoleve/syllabify-en",
    difficulty=Difficulty.Hard,
)
```

Capabilities at a glance:

- **Flexible inputs** – pass a string environment slug, an instantiated `verifiers.Environment`, a single glitchling, a list of glitchlings or names, or a pre-built `Gaggle`.
- **Column inference** – when `columns` is `None`, the loader searches for `prompt`/`question` columns, otherwise falls back to all string-valued columns. Explicitly list columns to target subsets (e.g., prompts but not references).
- **Deterministic summoning** – non-`Gaggle` inputs are normalised via `summon(...)` with the provided `seed`, so repeated calls produce matching corruption ensembles.
- **Tutorial difficulty scaling** – `tutorial_level` wires in tuned Mim1c/Typogre parameters multiplied by the selected `Difficulty` enum. Use `Difficulty.Easy` for gentle practice or `Difficulty.Extreme` to hammer robustness.
- **Dataset mutation** – environments are returned with their dataset replaced by the corrupted clone. Skip the `glitchlings` argument to leave the dataset untouched.

## Ensuring determinism

- Derive seeds from the surrounding context (`Gaggle.derive_seed`) when spawning new RNGs.
- Stabilise candidate order before sampling subsets to keep runs reproducible.
- Use `set_param` to expose tunable values so they can be reset between tests.
- When writing new glitchlings, route randomness through the instance RNG rather than module-level state.

## Testing checklist

Before publishing changes or documenting new glitchlings, run the Pytest suite from the repository root:

```bash
pytest
```

Some tests require the NLTK WordNet corpus. If you see skips mentioning WordNet, install it with:

```bash
python -c "import nltk; nltk.download('wordnet')"
```

## Additional resources

- [Monster Manual](../MONSTER_MANUAL.md) – complete bestiary with flavour text.
- [Repository README](../README.md) – project overview and ASCII ambience.

Once the `/docs` folder is published through GitHub Pages, this guide becomes the landing site for your glitchling adventures.

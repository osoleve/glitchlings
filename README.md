#

```plaintext
     .─') _                                       .─') _                  
    (  OO) )                                     ( OO ) )            
  ░██████  ░██ ░██   ░██               ░██       ░██ ░██                                 
 ░██   ░██ ░██       ░██               ░██       ░██                                     
░██        ░██ ░██░████████  ░███████ ░████████  ░██ ░██░████████   ░████████ ░███████  
░██  █████ ░██ ░██   ░██    ░██('─.░██ ░██    ░██ ░██ ░██░██    ░██ ░██.─')░██ ░██        
░██     ██ ░██ ░██   ░██    ░██( OO ) ╱░██    ░██ ░██ ░██░██    ░██ ░██(OO)░██ ░███████  
  ░██  ░███ ░██ ░██   ░██   ░██    ░██ ░██    ░██ ░██ ░██░██    ░██ ░██  o░███      ░██ 
  ░█████░█ ░██ ░██   ░████   ░███████  ░██    ░██ ░██ ░██░██    ░██  ░█████░██ ░███████  
                                                                    ░██            
                                                                ░███████             

                        Every language game breeds monsters.
```

![Python Versions](https://img.shields.io/pypi/pyversions/glitchlings.svg)
[![PyPI version](https://img.shields.io/pypi/v/glitchlings.svg)](https://pypi.org/project/glitchlings/)
![Wheel](https://img.shields.io/pypi/wheel/glitchlings.svg)
![Linting and Typing](https://github.com/osoleve/glitchlings/actions/workflows/ci.yml/badge.svg)  
![Entropy Budget](https://img.shields.io/badge/entropy-lifegiving-magenta.svg)
![Chaos](https://img.shields.io/badge/chaos-friend--shaped-chartreuse.svg)
![Charm](https://img.shields.io/badge/jouissance-indefatigable-cyan.svg)  
![Lore Compliance](https://img.shields.io/badge/ISO--474--▓▓-Z--Compliant-blue.svg)

`Glitchlings` are **utilities for corrupting the text inputs to your language models in deterministic, _linguistically principled_** ways.  
Each embodies a different way that documents can be compromised in the wild.

If reinforcement learning environments are games, then `Glitchling`s are enemies to breathe new life into old challenges.

They do this by breaking surface patterns in the input while keeping the target output intact.

Some `Glitchling`s are petty nuisances. Some `Glitchling`s are eldritch horrors.  
Together, they create truly nightmarish scenarios for your language models.

After all, what good is general intelligence if it can't handle a little chaos?

-_The Curator_

## Quickstart

```python
pip install -U glitchlings
```

> Glitchlings requires Python 3.10 or newer.

```python
from glitchlings import Gaggle, SAMPLE_TEXT, Typogre, Mim1c, Rushmore

gaggle = Gaggle(
    [
        Rushmore(rate=0.02),
        Rushmore(modes="duplicate", seed=404),
        Mim1c(rate=0.02),
        Typogre(rate=0.03),
    ]
)

print(gaggle(SAMPLE_TEXT))
```

> Onҽ m‎ھ‎rning, wһen Gregor Samƽa woke from trouble𝐝 𝑑reams, he found himself transformed in his bed into a horrible vermin‎٠‎ He l   lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightlh domed and divided by arches ino stiff sections. The bedding was adly able to cover it and and seemed ready to slide off any  moment. His many legxs, pitifully thin compared with the size of the the rest of him, waved about helplessly ashe looked looked.

Consult the [Glitchlings Usage Guide](docs/index.md)
for end-to-end instructions spanning the Python API, CLI, HuggingFace, PyTorch, and Prime Intellect
integrations, and the autodetected Rust pipeline (enabled whenever the extension is present).

## Motivation

If your model performs well on a particular task, but not when `Glitchling`s are present, it's a sign that it hasn't actually generalized to the problem.

Conversely, training a model to perform well in the presence of the types of perturbations introduced by `Glitchling`s should help it generalize better.

## Your First Battle

Summon your chosen `Glitchling` (_or a few, if ya nasty_) and call it on your text or slot it into `Dataset.map(...)`, supplying a seed if desired.
Glitchlings are standard Python classes, so you can instantiate them with whatever parameters fit your scenario:

```python
from glitchlings import Gaggle, Typogre, Mim1c

custom_typogre = Typogre(rate=0.1)
selective_mimic = Mim1c(rate=0.05, classes=["LATIN", "GREEK"])

gaggle = Gaggle([custom_typogre, selective_mimic], seed=99)
print(gaggle("Summoned heroes do not fear the glitch."))
```

Calling a `Glitchling` on a `str` transparently calls `.corrupt(str, ...) -> str`.
This means that as long as your glitchlings get along logically, they play nicely with one another.

When summoned as or gathered into a `Gaggle`, the `Glitchling`s will automatically order themselves into attack waves, based on the scope of the change they make:

1. Document
2. Paragraph
3. Sentence
4. Word
5. Character

They're horrible little gremlins, but they're not _unreasonable_.

## Command-Line Interface (CLI)

Keyboard warriors can challenge them directly via the `glitchlings` command:

<!-- BEGIN: CLI_USAGE -->
```bash
# Discover which glitchlings are currently on the loose.
glitchlings --list
```

```text
   Typogre — scope: Character, order: early
     Hokey — scope: Character, order: first
     Mim1c — scope: Character, order: last
   Ekkokin — scope: Word, order: early
    Pedant — scope: Word, order: late
  Jargoyle — scope: Word, order: normal
  Rushmore — scope: Word, order: normal
  Redactyl — scope: Word, order: normal
 Spectroll — scope: Word, order: normal
Scannequin — scope: Character, order: late
    Zeedub — scope: Character, order: last
```

```bash
# Review the full CLI contract.
glitchlings --help
```

```text
usage: glitchlings [-h] [-g SPEC] [-s SEED] [-f FILE] [--sample] [--diff]
                   [--list] [-c CONFIG]
                   [text]

Summon glitchlings to corrupt text. Provide input text as an argument, via
--file, or pipe it on stdin.

positional arguments:
  text                  Text to corrupt. If omitted, stdin is used or --sample
                        provides fallback text.

options:
  -h, --help            show this help message and exit
  -g SPEC, --glitchling SPEC
                        Glitchling to apply, optionally with parameters like
                        Typogre(rate=0.05). Repeat for multiples; defaults to
                        all built-ins.
  -s SEED, --seed SEED  Seed controlling deterministic corruption order
                        (default: 151).
  -f FILE, --file FILE  Read input text from a file instead of the command
                        line argument.
  --sample              Use the included SAMPLE_TEXT when no other input is
                        provided.
  --diff                Show a unified diff between the original and corrupted
                        text.
  --list                List available glitchlings and exit.
  -c CONFIG, --config CONFIG
                        Load glitchlings from a YAML configuration file.
```
<!-- END: CLI_USAGE -->

```bash
# Run Typogre against the contents of a file and inspect the diff.
glitchlings -g typogre --file documents/report.txt --diff

# Configure glitchlings inline by passing keyword arguments.
glitchlings -g "Typogre(rate=0.05)" "Ghouls just wanna have fun"

# Pipe text straight into the CLI for an on-the-fly corruption.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c

# Load a roster from a YAML attack configuration.
glitchlings --config experiments/chaos.yaml "Let slips the glitchlings of war"
```

Attack configurations live in plain YAML files so you can version-control experiments without touching code:

```yaml
# experiments/chaos.yaml
seed: 31337
glitchlings:
  - name: Typogre
    rate: 0.04
  - "Rushmore(rate=0.12, unweighted=True)"
  - name: Zeedub
    parameters:
      rate: 0.02
      characters: ["\u200b", "\u2060"]
```

Pass the file to `glitchlings --config` or load it from Python with `glitchlings.load_attack_config` and `glitchlings.build_gaggle`.

## Development

Follow the [development setup guide](docs/development.md) for editable installs, automated tests, and tips on enabling the Rust pipeline while you hack on new glitchlings.

## Starter 'lings

For maintainability reasons, all `Glitchling` have consented to be given nicknames once they're in your care. See the [Monster Manual](MONSTER_MANUAL.md) for a complete bestiary.

### Typogre

_What a nice word, would be a shame if something happened to it._

> _**Fatfinger.**_ Typogre introduces character-level errors (duplicating, dropping, adding, or swapping) based on the layout of a keyboard (QWERTY by default, with Dvorak and Colemak variants built-in).
>
> Args
>
> - `rate (float)`: The maximum number of edits to make as a percentage of the length (default: 0.02, 2%).
> - `keyboard (str)`: Keyboard layout key-neighbor map to use (default: "CURATOR_QWERTY"; also accepts "QWERTY", "DVORAK", "COLEMAK", and "AZERTY").
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Apostrofae

_It looks like you're trying to paste some text. Can I help?_

> _**Paperclip Manager.**_ Apostrofae scans for balanced runs of straight quotes, apostrophes, and backticks before replacing them with randomly sampled smart-quote pairs from a curated lookup table. The swap happens in-place so contractions and unpaired glyphs remain untouched.
>
> Args
>
> - `seed (int)`: Optional seed controlling the deterministic smart-quote sampling (default: 151).

### Mim1c

_Wait, was that...?_

> _**Confusion.**_ Mim1c replaces non-space characters with Unicode Confusables, characters that are distinct but would not usually confuse a human reader.
>
> Args
>
> - `rate (float)`: The maximum proportion of characters to replace (default: 0.02, 2%).
> - `classes (list[str] | "all")`: Restrict replacements to these Unicode script classes (default: ["LATIN", "GREEK", "CYRILLIC"]).
> - `banned_characters (Collection[str])`: Characters that must never appear as replacements (default: none).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Hokey

_She's soooooo coooool!_

> _**Passionista.**_ Hokey sometimes gets a little excited and elongates words for emphasis.
>
> Args
>
> - `rate (float)`: Share of high-scoring tokens to stretch (default: 0.3).
> - `extension_min` / `extension_max (int)`: Bounds for extra repetitions (defaults: 2 / 5).
> - `word_length_threshold (int)`: Preferred maximum alphabetic length; longer words are damped instead of excluded (default: 6).
> - `base_p (float)`: Base probability for the heavy-tailed sampler (default: 0.45).
> - `seed (int)`: The random seed for reproducibility (default: 151).

_Apocryphal Glitchling contributed by Chloé Nunes_

### Scannequin

_How can a computer need reading glasses?_

> _**OCR Artifacts.**_ Scannequin mimics optical character recognition errors by swapping visually similar character sequences (like rn↔m, cl↔d, O↔0, l/I/1).
>
> Args
>
> - `rate (float)`: The maximum proportion of eligible confusion spans to replace (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Zeedub

_Watch your step around here._

> _**Invisible Ink.**_ Zeedub slips zero-width codepoints between non-space character pairs, forcing models to reason about text whose visible form masks hidden glyphs.
>
> Args
>
> - `rate (float)`: Expected number of zero-width insertions as a proportion of eligible bigrams (default: 0.02, 2%).
> - `characters (Sequence[str])`: Optional override for the pool of zero-width strings to inject (default: curated invisibles such as U+200B, U+200C, U+200D, U+FEFF, U+2060).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Ekkokin

_Did you hear what I heard?_

> _**Echo Chamber.**_ Ekkokin swaps words with curated homophones so the text still sounds right while the spelling drifts. Groups are normalised to prevent duplicates and casing is preserved when substitutions fire.
>
> Args
>
> - `rate (float)`: Maximum proportion of eligible words to replace with homophones (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Jargoyle

_Uh oh. The worst person you know just bought a thesaurus._

> _**Sesquipedalianism.**_ Jargoyle, the insufferable `Glitchling`, replaces words from selected parts of speech with synonyms at random, without regard for connotational or denotational differences.
>
> Args
>
> - `rate (float)`: The maximum proportion of words to replace (default: 0.01, 1%).
>
- `part_of_speech`: The WordNet-style part(s) of speech to target (default: nouns). Accepts `wn.NOUN`, `wn.VERB`, `wn.ADJ`, `wn.ADV`, any iterable of those tags, or the string `"any"` to include them all. Vector/graph backends ignore this filter while still honouring deterministic sampling.
>
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Rushmore

_I accidentally an entire word._

> _**Tactical Scrambler.**_ Rushmore now orchestrates the full word-level triad—deletions, duplications, and adjacent swaps—that previously lived in separate glitchlings. Select the behaviours you need with the `modes` parameter (or pass `"all"`) and Rushmore executes them in a deterministic order while sharing one RNG.
>
> Args
>
> - `modes`: Choose which word-level attacks to enable. Accepts `"delete"`, `"duplicate"`, `"swap"`, any iterable of those tokens, a corresponding `RushmoreMode`, or the string `"all"`.
> - `rate (float)`: Global rate applied when per-mode rates are unspecified (default: 0.01, 1%).
> - `delete_rate`, `duplicate_rate`, `swap_rate (float)`: Optional per-mode overrides.
> - `unweighted (bool)`: Apply uniform sampling to all modes (default: False).
> - `delete_unweighted`, `duplicate_unweighted (bool | None)`: Per-mode overrides for weighting strategy.
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Redactyl

_Oops, that was my black highlighter._

> _**FOIA Reply.**_ Redactyl obscures random words in your document like an NSA analyst with a bad sense of humor.
>
> ### Args
>
> - `replacement_char (str)`: The character to use for redaction (default: FULL_BLOCK).
> - `rate (float)`: The maximum proportion of words to redact (default: 0.025, 2.5%).
> - `merge_adjacent (bool)`: Whether to redact the space between adjacent redacted words (default: False).
> - `unweighted (bool)`: Sample words uniformly instead of biasing toward longer tokens (default: False).
> - `seed (int)`: The random seed for reproducibility (default: 151).

## Field Report: Uncontained Specimens

### _Containment procedures pending_

- `nylingual` backtranslates portions of text.
- `glothopper` introduces code-switching effects, blending languages or dialects.
- `palimpsest` rewrites, but leaves accidental traces of the past.
- `vesuvius` is an apocryphal `Glitchling` with ties to _[Nosy, aren't we? -The Curator]_

## Apocrypha

Cave paintings and oral tradition contain many depictions of strange, otherworldly `Glitchling`s.  
These _Apocryphal `Glitchling`_ are said to possess unique abilities or behaviors.  
If you encounter one of these elusive beings, please document your findings and share them with _The Curator_.

### Ensuring Reproducible Corruption

Every `Glitchling` should own its own independent `random.Random` instance. That means:

- No `random.seed(...)` calls touch Python's global RNG.
- Supplying a `seed` when you construct a `Glitchling` (or when you `summon(...)`) makes its behavior reproducible.
- Re-running a `Gaggle` with the same master seed and the same input text (_and same external data!_) yields identical corruption output.
- Corruption functions are written to accept an `rng` parameter internally so that all randomness is centralized and testable.

#### At Wits' End?

If you're trying to add a new glitchling and can't seem to make it deterministic, here are some places to look for determinism-breaking code:

1. Search for any direct calls to `random.choice`, `random.shuffle`, or `set(...)` ordering without going through the provided `rng`.
2. Ensure you sort collections before shuffling or sampling.
3. Make sure indices are chosen from a stable reference (e.g., original text) when applying length‑changing edits.
4. Make sure there are enough sort keys to maintain stability.


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

```python
from glitchlings import Gaggle, SAMPLE_TEXT, Typogre, Mim1c, Reduple, Rushmore

gaggle = Gaggle([
    Typogre(max_change_rate=0.03),
    Mim1c(replacement_rate=0.02),
    Reduple(seed=404),
    Rushmore(max_deletion_rate=0.02),
])

print(gaggle(SAMPLE_TEXT))
```

> Onҽ m‎ھ‎rning, wһen Gregor Samƽa woke from trouble𝐝 𝑑reams, he found himself transformed in his bed into a horrible vermin‎٠‎ He l   lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightlh domed and divided by arches ino stiff sections. The bedding was adly able to cover it and and seemed ready to slide off any  moment. His many legxs, pitifully thin compared with the size of the the rest of him, waved about helplessly ashe looked looked.

## Motivation

If your model performs well on a particular task, but not when `Glitchling`s are present, it's a sign that it hasn't actually generalized to the problem.

Conversely, training a model to perform well in the presence of the types of perturbations introduced by `Glitchling`s should help it generalize better.

## Your First Battle

Summon your chosen `Glitchling` (_or a few, if ya nasty_) and call it on your text or slot it into `Dataset.map(...)`, supplying a seed if desired.
Glitchlings are standard Python classes, so you can instantiate them with whatever parameters fit your scenario:

```python
from glitchlings import Gaggle, Typogre, Mim1c

custom_typogre = Typogre(max_change_rate=0.1)
selective_mimic = Mim1c(replacement_rate=0.05, classes=["LATIN", "GREEK"])

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

```bash
# Discover which glitchlings are currently on the loose.
glitchlings --list

# Run Typogre against the contents of a file and inspect the diff.
glitchlings -g typogre --file documents/report.txt --diff

# Pipe text straight into the CLI for an on-the-fly corruption.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c
```

Use `--help` for a complete breakdown of available options.

## Starter 'lings

For maintainability reasons, all `Glitchling` have consented to be given nicknames once they're in your care. See the [Monster Manual](MONSTER_MANUAL.md) for a complete bestiary.

### Typogre

_What a nice word, would be a shame if something happened to it._

> _**Fatfinger.**_ Typogre introduces character-level errors (duplicating, dropping, adding, or swapping) based on the layout of a keyboard (QWERTY by default, with Dvorak and Colemak variants built-in).
>
> Args
>
> - `max_change_rate (float)`: The maximum number of edits to make as a percentage of the length (default: 0.02, 2%).
> - `keyboard (str)`: Keyboard layout key-neighbor map to use (default: "CURATOR_QWERTY"; also accepts "QWERTY", "DVORAK", "COLEMAK", and "AZERTY").
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Mim1c

_Wait, was that...?_

> _**Confusion.**_ Mim1c replaces non-space characters with Unicode Confusables, characters that are distinct but would not usually confuse a human reader.
>
> Args
>
> - `replacement_rate (float)`: The maximum proportion of characters to replace (default: 0.02, 2%).
> - `classes (list[str] | "all")`: Restrict replacements to these Unicode script classes (default: ["LATIN", "GREEK", "CYRILLIC"]).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Scannequin

_How can a computer need reading glasses?_

> _**OCR Artifacts.**_ Scannequin mimics optical character recognition errors by swapping visually similar character sequences (like rn↔m, cl↔d, O↔0, l/I/1).
>
> Args
>
> - `error_rate (float)`: The maximum proportion of eligible confusion spans to replace (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Jargoyle

_Uh oh. The worst person you know just bought a thesaurus._

> _**Sesquipedalianism.**_ Jargoyle, the insufferable `Glitchling`, replaces words from selected parts of speech with synonyms at random, without regard for connotational or denotational differences.
>
> Args
>
> - `replacement_rate (float)`: The maximum proportion of words to replace (default: 0.1, 10%).
> - `part_of_speech`: The WordNet part(s) of speech to target (default: nouns). Accepts `wn.NOUN`, `wn.VERB`, `wn.ADJ`, `wn.ADV`, any iterable of those tags, or the string `"any"` to include them all.
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Reduple

_Did you say that or did I?_

> _**Broken Record.**_ Reduple stutters through text by randomly reduplicating words. Like a nervous speaker, it creates natural repetitions that test a model's ability to handle redundancy without losing the thread.
>
> Args
>
> - `reduplication_rate (float)`: The maximum proportion of words to reduplicate (default: 0.05, 5%).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Rushmore

_I accidentally an entire word._

> _**Hasty Omission.**_ The evil (?) twin of `reduple`, Rushmore moves with such frantic speed that it causes words to simply vanish from existence as it passes.
>
> Args
>
> - `max_deletion_rate (float)`: The maximum proportion of words to delete (default: 0.01, 1%).
> - `seed (int)`: The random seed for reproducibility (default: 151).

### Redactyl

_Oops, that was my black highlighter._

> _**FOIA Reply.**_ Redactyl obscures random words in your document like an NSA analyst with a bad sense of humor.
>
> ### Args
>
> - `replacement_char (str)`: The character to use for redaction (default: █).
> - `redaction_rate (float)`: The maximum proportion of words to redact (default: 0.05, 5%).
> - `merge_adjacent (bool)`: Whether to redact the space between adjacent redacted words (default: False).
> - `seed (int)`: The random seed for reproducibility (default: 151).

## Field Report: Uncontained Specimens

### _Containment procedures pending_

- `ekkokin` substitutes words with homophones (phonetic equivalents).
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

#

```plaintext
     .─') _                                       .─') _                  
    (  OO) )                                     ( OO ) )            
  ░██████  ░██ ░██   ░██               ░██        ░██ ░██                                 
 ░██   ░██ ░██       ░██               ░██        ░██                                     
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
from glitchlings import summon, SAMPLE_TEXT

gaggle = summon(["reduple", "mim1c", "typogre", "rushmore"])
gaggle(SAMPLE_TEXT)
```

> Onҽ m‎ھ‎rning, wһen Gregor Samƽa woke from trouble𝐝 𝑑reams, he found himself transformed in his bed into a horrible vermin‎٠‎ He l   lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightlh domed and divided by arches ino stiff sections. The bedding was adly able to cover it and and seemed ready to slide off any  moment. His many legxs, pitifully thin compared with the size of the the rest of him, waved about helplessly ashe looked looked.

## Motivation

If your model performs well on a particular task, but not when `Glitchling`s are present, it's a sign that it hasn't actually generalized to the problem.

Conversely, training a model to perform well in the presence of the types of perturbations introduced by `Glitchling`s should help it generalize better.

## Your First Battle

Summon your chosen `Glitchling` (_or a few, if ya nasty_) and call it on your text or slot it into `Dataset.map(...)`, supplying a seed if desired.  
Some `Glitchling`s may have additional keyword arguments but they will always be optional with what I decide are "reasonable defaults".  
Seed defaults to 151, obviously.

Calling a `Glitchling` on a `str` transparently calls `.corrupt(str, ...) -> str`.  
This means that as long as your glitchlings get along logically, they play nicely with one another.

Each `Glitchling` maintains its own history of inputs and outputs, and a `Gaggle` of `Glitchling`s can be used to manage multiple `Glitchling`s at once while maintaining their individual histories.

When summoned as a `Gaggle`, the `Glitchling`s will automatically order themselves into attack waves, based on the scope of the change they make:

1. Document
2. Paragraph
3. Sentence
4. Word Level
5. Character

They're horrible little gremlins, but they're not _unreasonable_.

### Reproducible Corruption

Every `Glitchling` owns its own independent `random.Random` instance. That means:

- No `random.seed(...)` calls touch Python's global RNG.
- Supplying a `seed` when you construct a `Glitchling` (or when you `summon(...)`) makes its behavior reproducible.
- Re-running a `Gaggle` with the same master seed and the same input text (_and same external data!_) yields identical corruption output.

#### Quick Example

```python
from glitchlings import summon, SAMPLE_TEXT

g1 = summon(["reduple", "mim1c", "typogre", "rushmore", "redactyl"], seed=42)
o1 = g1(SAMPLE_TEXT)

g2 = summon(["reduple", "mim1c", "typogre", "rushmore", "redactyl"], seed=42)
o2 = g2(SAMPLE_TEXT)

assert o1 == o2  # Deterministic!
```

#### Notes & Caveats

- Corruption functions are written to accept an `rng` parameter internally so that all randomness is centralized and testable.
- If you mutate a glitchling's parameters after you've used it (e.g. `typogre.set_param(...)`) the outputs may not be the same as before the change. So don't do that.

### At Wits' End?

If you're trying to add a new glitchling and can't seem to make it deterministic, here are some places to look for determinism-breaking code:

1. Search for any direct calls to `random.choice`, `random.shuffle`, or `set(...)` ordering without going through the provided `rng`.
2. Ensure you sort collections before shuffling or sampling.
3. Make sure indices are chosen from a stable reference (e.g., original text) when applying length‑changing edits.
4. Make sure there are enough sort keys to maintain stability.

## Starter 'lings

For maintainability reasons, all `Glitchling` have consented to be given nicknames once they're in your care. See the [Monster Manual](MONSTER_MANUAL.md) for a complete bestiary.

### Typogre

_What a nice word, would be a shame if something happened to it._

> _**Fatfinger.**_ Typogre introduces character-level errors (duplicating, dropping, adding, or swapping) based on the layout of a (currently QWERTY) keyboard.
>
> ### Args
>
> - `max_change_rate (float)`: The maximum number of edits to make as a percentage of the length (default: 0.02, 2%)
> - `preserve_first (bool)`: Whether to preserve the first character of words when applicable (default: True).
> - `preserve_last (bool)`: Whether to preserve the last character of words when applicable (default: True).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import typogre
> >>> typogre(sample_text)
> ```

### Mim1c

_Wait, was that...?_

> _**Confusion.**_ Mim1c replaces non-space characters with Unicode Confusables, characters that are distinct but would not usually confuse a human reader.
>
> ### Args
>
> - `replacement_rate (float)`: The maximum proportion of characters to replace (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import mim1c
> >>> print(mim1c(sample_text))
> ```

### Jargoyle

_Uh oh. The worst person you know just bought a thesaurus._

> _**Sesquipedalianism.**_ Jargoyle, the insufferable `Glitchling`, replaces nouns with synonyms at random, without regard for connotational or denotational differences.
>
> ### Args
>
> - `replacement_rate (float)`: The maximum proportion of words to replace (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import jargoyle
> >>> print(jargoyle(sample_text))
> ```

### Reduple

_Did you say that or did I?_

> _**Broken Record.**_ Reduple stutters through text by randomly reduplicating words. Like a nervous speaker, it creates natural repetitions that test a model's ability to handle redundancy without losing the thread.
>
> ### Args
>
> - `reduplication_rate (float)`: The maximum proportion of words to reduplicate (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import reduple
> >>> print(reduple(sample_text))
> ```

### Rushmore

_I accidentally an entire word._

> _**Hasty Omission.**_ The evil (?) twin of `reduple`, Rushmore moves with such frantic speed that it causes words to simply vanish from existence as it passes.
>
> ### Args
>
> - `deletion_rate (float)`: The maximum proportion of words to delete (default: 0.01, 1%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import rushmore
> >>> print(rushmore(sample_text))
> ```

#### Redactyl

_Oops, that was my black highlighter._

> _**FOIA Reply.**_ Redactyl obscures random words in your document like an NSA analyst with a bad sense of humor
>
> ### Args
>
> - `replacement_char (str)`: The character to use for redaction (default: █).
> - `redaction_rate (float)`: The maximum proportion of words to redact (default: 0.05, 5%).
> - `merge_adjacent (bool)`: Whether to redact the space between adjacent redacted words (default: False).
>
> ```python
> >>> from glitchlings import redactyl
> >>> print(redactyl(sample_text))
> ```

## Field Report: Uncontained Specimens

### _Containment procedures pending_

- `ekkokin` substitutes words with homophones (phonetic equivalents).
- `nylingual` backtranslates portions of text.
- `glothopper` introduces code-switching effects, blending languages or dialects.
- `scannequin` introduces OCR-like artifacts.
- `palimpsest` rewrites, but leaves accidental traces of the past.

## Apocrypha

Cave paintings and oral tradition contain many depictions of strange, otherworldly `Glitchling`s.  
These _Apocryphal `Glitchling`_ are said to possess unique abilities or behaviors.  
If you encounter one of these elusive beings, please document your findings and share them with _The Curator_.

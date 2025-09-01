#

```plaintext
     .─') _                                       .─') _                  
    (  OO) )                                     ( OO ) )            
  ░██████  ░██ ░██   ░██               ░██        ░██ ░██                                 
 ░██   ░██ ░██       ░██               ░██        ░██                                     
░██        ░██ ░██░████████  ░███████  ░████████  ░██ ░██░████████   ░████████  ░███████  
░██  █████ ░██ ░██   ░██    ░██('─.░██ ░██    ░██ ░██ ░██░██    ░██ ░██.─')░██ ░██        
░██     ██ ░██ ░██   ░██    ░██( OO ) ╱░██    ░██ ░██ ░██░██    ░██ ░██(OO)░██  ░███████  
 ░██  ░███ ░██ ░██   ░██    ░██    ░██ ░██    ░██ ░██ ░██░██    ░██ ░██ o ░███        ░██ 
  ░█████░█ ░██ ░██    ░████  ░███████  ░██    ░██ ░██ ░██░██    ░██  ░█████░██  ░███████  
                                                                           ░██            
                                                                     ░███████             

                        Every language game breeds monsters.
```

`glitchlings` is a library of functions for corrupting the text inputs to your language models in deterministic, linguistically principled ways.  
Each embodies a different way that documents can be compromised in the wild.

Some glitchlings are petty nuisances.  
Some glitchlings are eldritch horrors.  
Each alone will put your LLM to the test.  
Together, they create truly nightmarish scenarios.

After all, what good is general intelligence if it can't handle a little chaos?

~= *The Curator* =~

## Purpose

Glitchlings are intended to increase the difficulty of your benchmark, RL environment, or dataset in general.  
They do this by breaking surface patterns in the input while keeping the target output intact.

If your model performs well on a particular task, but not when a glitchling is present, it's a sign that it hasn't actually generalized to the problem.  
Conversely, training a model to perform well in the presence of perturbations should help it generalize better.

## Use

Summon your chosen Glitchling (or a few, if ya nasty) and call it on your text or slot it into `Dataset.map(...)`, supplying a seed if desired.  
Some glitchlings may have additional keyword arguments but they will always be optional with what I decide are "reasonable defaults".  
Seed defaults to 151, obviously.

Calling a glitchling on a `str` transparently calls `.corrupt(str, ...) -> str`.  
This means that as long as the glitchlings you summon got along logically, the glitchlings play nicely with one another. But mind their order!

## Starter 'lings

For maintainability reasons, all glitchlings have consented to be given nicknames once they're in your care.

### Mim1c

*Wait, was that...?*

Mim1c is a *capgras glitchling*, replacing characters in your text with near-identical ones that are... *wrong*.  
That is, it introduces unicode confusables, variants on characters that would not usually trip up a human reader.

```python
from glitchlings import mim1c

print(mim1c("Hello, world!", max_replacement_rate=0.5))

> He‎𞣇‎lჿ, w‎ﮪ‎𝓇lꓒ!
```

Args:

- `max_replacement_rate (float)`: The maximum proportion of characters to replace (default: 0.02, 2%).
- `seed (int)`: The random seed for reproducibility (default: 151).

### Typogre

*What a nice word, it would be a shame if something happened to it...*

Typogre, the dyskinetic glitchling, simulates a "fat finger" typing error by randomly duplicating, dropping, adding, or swapping characters.  
Characters added in are based on the layout of a QWERTY keyboard, more layouts can be added.

```python
from glitchlings import typogre

print(typogre("Hello, world!", max_change_rate=0.5))

> Helo, wo r!
```

Args:

- `max_change_rate (float)`: The maximum number of edits to make as a percentage of the length (default: 0.02, 2%)
- `preserve_first (bool)`: Whether to preserve the first character (default: True).
- `preserve_last (bool)`: Whether to preserve the last character (default: True).
- `seed (int)`: The random seed for reproducibility (default: 151).

### Jargoyle

*Uh oh. The worst person you know just bought a thesaurus.*

Jargoyle, the insufferable-type glitchling, replaces nouns with synonyms at random, without regard for connotational/denotational differences.

```python
from glitchlings import jargoyle

print(jargoyle("Hello, world!", max_replacement_rate=1.0))

> hullo, macrocosm!
```

Args:

- `max_replacement_rate (float)`: The maximum proportion of words to replace (default: 0.02, 2%).
- `seed (int)`: The random seed for reproducibility (default: 151).

## Field Report: Uncontained Specimens

*Containment procedures pending*.

- Reduple repeats words or phrases.
- Redactyl obscures or ███████ parts of the text.
- Ekkokin substitutes words with homophones (phonetic equivalents).
- Rushmore will accidentally entire words, or worse.
- Nylingual backtranslates portions of text.
- Glothopper introduces code-switching effects, blending languages or dialects.
- Scannequin introduces OCR-like artifacts.
- Palimpsest rewrites, but leaves accidental traces of the past.

### Apocrypha

Cave paintings and oral tradition contain many depictions of strange, otherworldly glitchlings.  
These *Apocryphal Glitchlings* are said to possess unique abilities or behaviors.  
If you encounter one of these elusive beings, please document your findings and share them with *The Curator*.

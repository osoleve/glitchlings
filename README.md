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

`glitchlings` are **utilities for corrupting the text inputs to your language models in deterministic, _linguistically principled_** ways.  
Each embodies a different way that documents can be compromised in the wild.

If RL environments are games, then glitchlings are enemies to breathe new life into old challenges.

They do this by breaking surface patterns in the input while keeping the target output intact.

Some glitchlings are petty nuisances. Some glitchlings are eldritch horrors.  
Together, they create truly nightmarish scenarios for your language models.

After all, what good is general intelligence if it can't handle a little chaos?

-_The Curator_

## Motivation

If your model performs well on a particular task, but not when glitchlings are present, it's a sign that it hasn't actually generalized to the problem.

Conversely, training a model to perform well in the presence of the types of perturbations introduced by glitchlings should help it generalize better.

## Quickstart

```python
from glitchlings import summon, SAMPLE_TEXT

horde = summon(["reduple", "mim1c", "typogre", "rushmore"])
horde(SAMPLE_TEXT)
```

> Onҽ m‎ھ‎rning, wһen Gregor Samƽa woke from trouble𝐝 𝑑reams, he found himself transformed in his bed into a horrible vermin‎٠‎ He l   lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightlh domed and divided by arches ino stiff sections. The bedding was adly able to cover it and and seemed ready to slide off any  moment. His many legxs, pitifully thin compared with the size of the the rest of him, waved about helplessly ashe looked looked.

## Your First Battle

Summon your chosen Glitchling (_or a few, if ya nasty_) and call it on your text or slot it into `Dataset.map(...)`, supplying a seed if desired.  
Some glitchlings may have additional keyword arguments but they will always be optional with what I decide are "reasonable defaults".  
Seed defaults to 151, obviously.

Calling a glitchling on a `str` transparently calls `.corrupt(str, ...) -> str`.  
This means that as long as your glitchlings get along logically, they play nicely with one another.

Each glitchling maintains its own history of inputs and outputs, and a glitchling `Horde` can be used to manage multiple glitchlings at once while maintaining their individual histories.

When summoned as a `Horde`, the glitchlings will automatically order themselves into attack waves, based on the scope of the change they make:

1. Document
2. Paragraph
3. Sentence
4. Word Level
5. Character

They're horrible little gremlins, but they're not _unreasonable_.

## Starter 'lings

For maintainability reasons, all glitchlings have consented to be given nicknames once they're in your care.

### Mim1c

_Wait, was that...?_

Mim1c is a _capgras glitchling_, replacing characters in your text with near-identical ones that are... _wrong_.  
That is, it introduces unicode confusables, variants on characters that would not usually trip up a human reader.

```python
from glitchlings import mim1c

print(mim1c(sample_text))
```

> On𝗲 moꭈning‎؍‎ when Gregor S𝛼m𝑠𝚊 woke from troub‎𞸀‎ed dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it   t and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.

Args:

- `max_replacement_rate (float)`: The maximum proportion of characters to replace (default: 0.02, 2%).
- `seed (int)`: The random seed for reproducibility (default: 151).

### Typogre

_What a nice word, it would be a shame if something happened to it..._

Typogre, the dyskinetic glitchling, simulates a "fat finger" typing error by randomly duplicating, dropping, adding, or swapping characters.  
Characters added in are based on the layout of a QWERTY keyboard, more layouts can be added.

```python
from glitchlings import typogre

print(typogre(sample_text))
```

> One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on hisarmour-like back, and if he lifted his head a little he could see his brown belly, slightly romed and divided by arches int stiff sections. The bedding was hrly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplesly ass he looked.

Args:

- `max_change_rate (float)`: The maximum number of edits to make as a percentage of the length (default: 0.02, 2%)
- `preserve_first (bool)`: Whether to preserve the first character (default: True).
- `preserve_last (bool)`: Whether to preserve the last character (default: True).
- `seed (int)`: The random seed for reproducibility (default: 151).

### Jargoyle

_Uh oh. The worst person you know just bought a thesaurus._

Jargoyle, the insufferable-type glitchling, replaces nouns with synonyms at random, without regard for connotational/denotational differences.

```python
from glitchlings import jargoyle

print(jargoyle(sample_text))
```

> One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible varmint. He lay on his armor-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arch into stiff sections. The bedding was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.

Args:

- `max_replacement_rate (float)`: The maximum proportion of words to replace (default: 0.02, 2%).
- `seed (int)`: The random seed for reproducibility (default: 151).

### Reduple

_Did I just... did I just hear an echo?_

Reduple, the echolalic glitchling, stutters through your text by randomly reduplicating words.
Like a broken record or a nervous speaker, it creates natural repetitions that test whether your model can handle redundancy without losing the thread.

Unlike simple duplication, Reduple maintains natural spacing and punctuation placement, creating the kinds of repetitions you might see in real transcripts, hasty edits, or stuttering speech.

```python
from glitchlings import reduple

print(reduple(sample_text))
```

> One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it and and seemed ready to to slide off any moment. His many legs, pitifully thin compared with the size of the the rest of him, waved waved about helplessly as he looked looked.

Args:

- `max_reduplication_rate (float)`: The maximum proportion of words to reduplicate (default: 0.02, 2%).
- `seed (int)`: The random seed for reproducibility (default: 151).

### Rushmore

_Well, why'd you wait til the night before to start?_

Rushmore, the frantic glitchling, is the evil (?) twin of Reduple. Where Reduple may double up on a word, Rushmore might forget one.

Or, as we'd say back in the day, it "accidentally entire words."

Args:

- `max_deletion_rate (float)`: The maximum proportion of words to delete (default: 0.01, 1%).
- `seed (int)`: The random seed for reproducibility (default: 151).

```python
from glitchlings import rushmore

print(rushmore(sample_text))
```

> One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.

## Field Report: Uncontained Specimens

_Containment procedures pending_

- Redactyl obscures or ███████ parts of the text.
- Ekkokin substitutes words with homophones (phonetic equivalents).
- Nylingual backtranslates portions of text.
- Glothopper introduces code-switching effects, blending languages or dialects.
- Scannequin introduces OCR-like artifacts.
- Palimpsest rewrites, but leaves accidental traces of the past.

## Apocrypha

Cave paintings and oral tradition contain many depictions of strange, otherworldly glitchlings.  
These _Apocryphal Glitchlings_ are said to possess unique abilities or behaviors.  
If you encounter one of these elusive beings, please document your findings and share them with ~_The Curator_~.

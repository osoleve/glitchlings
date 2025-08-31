# Glitchlings

*Language games were never meant to be easy.*

Glitchlings is a library of functions for corrupting the text inputs to your language models.
After all, what good is general intelligence if it can't handle a little real world chaos?

## Use

Import your selected Glitchling (or a few, if ya nasty) and call it on your text/map it over your text column, supplying a seed if desired.
Some glitchlings may have additional keyword arguments but they will always be optional with what I decide are "reasonable defaults".
Seed defaults to 151, obviously.

For maintainability reasons, all glitchlings have consented to be renamed once they're in your care.
Calling one on arguments transparently calls `.corrupt(...)`, which ALWAYS returns a `str`.
This means that as long as they got along logically, the glitchlings play nicely with one another. But mind their order!

## Species (Starter 'lings)

### Doppeltexter

Doppeltexter replaces characters in your text with near-identical ones that are somehow... *wrong*.
That is, it introduces unicode confusables, variants on characters that would not usually trip up a human reader.

Args:
    - max_replacement_rate (float): The maximum proportion of characters to replace (default: 0.02).
    - seed (int): The random seed for reproducibility (default: 151).

```python
print(doppeltexter("Hello, world!", max_replacement_rate=0.5))

> He‎𞣇‎lჿ, w‎ﮪ‎𝓇lꓒ!
```

### Typogre

Typogre simulates a "fat finger" typing error by randomly duplicating, dropping, adding, or swapping characters.
Characters added in are based on the layout of a QWERTY keyboard, more layouts can be added.

Args:
    - max_change_rate (float): The maximum number of edits to make as a percentage of the length (default: 0.02, max: 1.0).
    - preserve_first (bool): Whether to preserve the first character (default: True).
    - preserve_last (bool): Whether to preserve the last character (default: True).
    - seed (int): The random seed for reproducibility (default: 151).

```python
print(typogre("Hello, world!", max_change_rate=0.5))

> Helo, wo r!
```

### Species we've documented but not yet captured

- Jargoyle uses the thesaurus, badly.
- Nilpotrix will accidentally entire words, or worse.
- Reduplicataur repeats words or phrases.
- Palimpsest rewrites, but leaves erroneous traces of the past.

### Contributing

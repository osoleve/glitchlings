# Glitchling Monster Manual

This manual contains the detailed stat blocks and descriptions of the various Glitchlings.

---

## Scannequin

_How can a computer need reading glasses?_

> Small Construct (squinting), Neutral
>
> ---
>
> _**OCR Artifacts.**_ Scannequin mimics optical character recognition errors by swapping visually similar character sequences (e.g., rn↔m, cl↔d, O↔0, l/I/1).
>
> ### Scannequin Args
>
> - `rate (float)`: The maximum proportion of eligible confusion spans to replace (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import scannequin
> >>> print(scannequin(sample_text))
> ```
>
> > One moming, when Gregor Samsa woke from troub1ed dreams, he found himse1f transf0rmed in his bed into a horribIe vermin. He lay on his armour-1ike back, and if he lifted his head a 1ittle he couId see his brown bel1y, sIightIy domed and divided by arches into stiff sections.
>
> ---
>
> - **Armor Class** 12 (paper)
> - **Hit Points** 9 (2d8)
> - **Speed** 15 ft., 40 ppm
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |4 |10 |8 |11 |9 |6 |
>
> ---
>
> - **Skills** Investigation +2
> - **Damage Vulnerabilities** coffee, humidity
> - **Languages** Cornmon
> - **Challenge** 0 (50 XP)
>
> ---

## Typogre

_What a nice word, would be a shame if something happened to it._

> Tiny Giant (Dyskinetic), Chaotic Neutral
>
> ---
>
> _**Fatfinger.**_ Typogre introduces character-level errors (duplicating, dropping, adding, or swapping)
> based on the layout of a keyboard (QWERTY by default, with Dvorak and Colemak variants built-in).
>
> ### Typogre Args
>
> - `rate (float)`: The maximum number of edits to make as a percentage of the length (default: 0.02, 2%).
> - `keyboard (str)`: Keyboard layout key-neighbor map to use (default: "CURATOR_QWERTY"; also accepts "QWERTY", "DVORAK", "COLEMAK", and "AZERTY").
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import typogre
> >>> typogre(sample_text)
> ```
>
> > One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on hisarmour-like back, and if he lifted his head a little he could see his brown belly, slightly romed and divided by arches int stiff sections. The bedding was hrly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplesly ass he looked.
>
> ---
>
> - **Armor Class** 7 (mittens)
> - **Hit Points** 17 (7d4)
> - **Speed** 60 wpm
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |15 |1 |11 |2 |2 |9 |
>
> ---
>
> - **Skills** Sleight of Hand -3
> - **Condition Immunities** blinded
> - **Languages** understands English but can't read
> - **Challenge** 1 (200 XP)
>
> ---

## Mim1c

_Wait, was that...?_

> Tiny Monstrosity (capgras), chaotic evil
>
> ---
>
> _**Confusion.**_ Mim1c replaces non-space characters with Unicode Confusables, characters that are distinct but would not usually confuse a human reader.
>
> ### Mim1c Args
>
> - `rate (float)`: The maximum proportion of characters to replace (default: 0.02, 2%).
> - `classes (list[str] | "all")`: Restrict replacements to these Unicode script classes (default: ["LATIN", "GREEK", "CYRILLIC"]).
> - `banned_characters (Collection[str])`: Characters that must never appear as replacements (default: none).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import mim1c
> >>> print(mim1c(sample_text))
> ```
>
> > On𝗲 moꭈning‎؍‎ when Gregor S𝛼m𝑠𝚊 woke from troub‎𞸀‎ed dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it   t and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.
>
> ---
>
> - **Armor Class** 14 (hide)
> - **Hit Points** 1 (9d4 - 36)
> - **Speed** 7O wpm
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |3 |15 |3 |13 |3 |7 |
>
> ---
>
> - **Skills** Deception +3, Stealth +6
> - **Damage Immunities** memorization
> - **Senses** truesight 30 ft.
> - **Languages** Abyssal Unicode
> - **Challenge** 2 (450 XP)
>
> ---

## Jargoyle

_Uh oh. The worst person you know just bought a thesaurus._

> Medium Monstrosity (academic), Lawful Evil
>
> ---
>
> _**Sesquipedalianism.**_ Jargoyle, the insufferable `Glitchling`, replaces words from selected parts of speech with synonyms at random, without regard for connotational or denotational differences.
>
> ### Jargoyle Args
>
> - `rate (float)`: The maximum proportion of words to replace (default: 0.1, 10%).
> - `part_of_speech`: The WordNet part(s) of speech to target (default: nouns). Accepts `wn.NOUN`, `wn.VERB`, `wn.ADJ`, `wn.ADV`, any iterable of those tags, or the string `"any"` to include them all.
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import jargoyle
> >>> print(jargoyle(sample_text))
> ```
>
> > One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible varmint. He lay on his armor-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arch into stiff sections. The bedding was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.
>
> ---
>
> - **Armor Class** 5 (thin skin)
> - **Hit Points** 52 (8d8 + 16)
> - **Speed** 30 ft. fly, 0 ft. socially
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |13 |5 |16 |19 |4 |17 |
>
> ---
>
> - **Skills** Deception +6, Persuasion +6
> - **Damage Immunities** plain language
> - **Condition Immunities** charmed
> - **Senses** darkvision 60 ft.
> - **Languages** understands all, but only speaks in overwrought synonyms
> - **Challenge** 3 (700 XP)
>
> ---

## Reduple

_Did you say that or did I?_

> Small Fey (echolalic), Chaotic Neutral
>
> ---
>
> _**Broken Record.**_ Reduple stutters through text by randomly reduplicating words. Like a nervous speaker, it creates natural repetitions that test a model's ability to handle redundancy without losing the thread.
>
> ### Reduple Args
>
> - `rate (float)`: The maximum proportion of words to reduplicate (default: 0.05, 5%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import reduple
> >>> print(reduple(sample_text))
> ```
>
> > One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it and and seemed ready to to slide off any moment. His many legs, pitifully thin compared with the size of the the rest of him, waved waved about helplessly as he looked looked.
>
> ---
>
> - **Armor Class** 14
> - **Hit Points** 13 (3d6 + 3)
> - **Speed** 40 ft.
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |6 |18 |10 |7 |11 |14 |
>
> ---
>
> - **Skills** Performance +4, Stealth +6
> - **Condition Immunities** silenced
> - **Languages** Sylvan, Common (with an endearing stutter)
> - **Challenge** 1/2 (100 XP)
>
> ---

## Rushmore

_I accidentally an entire word._

> Tiny Aberration (kinetic), Chaotic Neutral
>
> ---
>
> _**Hasty Omission.**_ The evil (?) twin of `reduple`, Rushmore moves with such frantic speed that it causes words to simply vanish from existence as it passes.
>
> ### Rushmore Args
>
> - `rate (float)`: The maximum proportion of words to delete (default: 0.01, 1%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import rushmore
> >>> print(rushmore(sample_text))
> ```
>
> > One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.
>
> ---
>
> - **Armor Class** 16
> - **Hit Points** 7 (2d4 + 2)
> - **Speed** 60 ft.
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |2 |22 |8 |5 |7 |6 |
>
> ---
>
> - **Skills** Acrobatics +8, Stealth +8
> - **Damage Vulnerabilities** effects that cause slowness
> - **Senses** blindsight 10 ft.
> - **Languages** --
> - **Challenge** 1 (200 XP)
>
> ---

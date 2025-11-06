# Glitchling Monster Manual

This manual contains the detailed stat blocks and descriptions of the various Glitchlings.

Any resemblance to real text, living or dead, is purely coincidental and probably your own fault for leaving the PDF open after midnight.

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

## Spectroll

_"The colors, Duke, the colors!"_

> Tiny Elemental (prismatic), Chaotic Neutral
>
> ---
>
> _**Chromatic Swap.**_ Spectroll rewrites colour words, trading each hue for its opposite in literal mode or sampling neighbour shades when it drifts across the spectrum.
>
> ### Spectroll Args
>
> - `mode (Literal['literal','drift'])`: Choose deterministic palette swaps or seeded spectral drift (default: `'literal'`).
> - `seed (int | None)`: Optional seed that anchors spectral drift so the same story beat keeps the same palette (default: 151).
>
> ```python
> >>> from glitchlings import spectroll
> >>> spectroll("The red balloon and green kite rose together.")
> 'The blue balloon and lime kite rose together.'
> >>> spectroll("The red balloon and green kite rose together.", mode="drift", seed=7)
> 'The orange balloon and teal kite rose together.'
> ```
>
> ---
>
> - **Armor Class** 12 (stained glass)
> - **Hit Points** 8 (2d6 + 1)
> - **Speed** 25 ft., 1.21 gigawatts
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |6 |14 |12 |11 |10 |15 |
>
> ---
>
> - **Skills** Performance +4, Deception +3
> - **Damage Resistances** radiant, psychic (when struck by bright ideas)
> - **Condition Immunities** blinded (rainbow vision)
> - **Languages** Common, Color Hex
> - **Challenge** 1/2 (100 XP)
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

## Hokey

_She's soooooo coooool!_

> Tiny Fey (fanatic), Chaotic Good
>
> ---
>
> _**Passionista.**_ Hokey sometimes gets a little excited and elongates words for emphasis.
>
> ### Hokey Args
>
> - `rate (float)`: Share of high-scoring tokens to stretch (default: 0.3).
> - `extension_min` / `extension_max (int)`: Bounds for extra repetitions (defaults: 2 / 5).
> - `word_length_threshold (int)`: Preferred maximum alphabetic length; longer words are damped instead of excluded (default: 6).
> - `base_p (float)`: Base probability for the heavy-tailed sampler (default: 0.45).
> - `seed (int | None)`: Optional random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import hokey
> >>> print(hokey("She's so cool and fun!"))
> ```
>
> > She's sooooo coooool and fuuun!
>
> ---
>
> - **Armor Class** 13 (denim jacket)
> - **Hit Points** 18 (4d6 + 2)
> - **Speed** 35 ft., 120 bpm (dance break)
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |8 |16 |12 |10 |11 |18 |
>
> ---
>
> - **Skills** Performance +6, Persuasion +8
> - **Damage Resistances** thunder (concert earplugs), psychic (relentless optimism)
> - **Condition Immunities** frightened (as long as the crowd is cheering)
> - **Languages** Common, Emoji
> - **Challenge** 1/2 (100 XP)
>
> ---

## Apostrofae

_It looks like you're trying to paste some text. Can I help?_

> Tiny Construct (overhelpful), Lawful Neutral
>
> ---
>
> _**Smart Quotes.**_ Apostrofae replaces balanced straight quotation marks, apostrophes, and backticks with curated Unicode pairs, nudging text toward typeset polish while revealing formatting inconsistencies.
>
> ### Apostrofae Args
>
> - `seed (int)`: Optional random seed for deterministic quote-pair sampling (default: 151).
>
> ```python
> >>> from glitchlings import apostrofae
> >>> print(apostrofae('"Mind the quotes," she said. `Okay,` he replied.'))
> ```
>
> > “Mind the quotes,” she said. “Okay,” he replied.
>
> ---
>
> - **Armor Class** 11 (stationery)
> - **Hit Points** 5 (2d4)
> - **Speed** 20 ft., 60 wpm
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |5 |12 |8 |13 |10 |9 |
>
> ---
>
> - **Skills** Persuasion +1, Insight +2
> - **Damage Resistances** paper cuts
> - **Condition Immunities** frightened (of WordArt)
> - **Languages** Common, ClipArt
> - **Challenge** 1/4 (50 XP)
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

## Zeedub

_A whispering glyph parasite that lives in the interstices of codepoints, marking territory with invisible traces._

> Diminutive Aberration (glyphic), Neutral
>
> ---
>
> _**Invisible Ink.**_ Zeedub threads zero-width codepoints between letters, leaving invisible tripwires that only the most paranoid normalisers will notice.
>
> ### Zeedub Args
>
> - `rate (float)`: Expected proportion of eligible bigrams to receive an insertion (default: 0.02, 2%).
> - `characters (Sequence[str])`: Optional override for the zero-width pool (default: curated set of U+200B, U+200C, U+200D, U+FEFF, U+2060).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import zeedub
> >>> print(zeedub(sample_text))
> ```
>
> > One morning, when Gregor Samsa woke from troubled drea<ZWSP>ms, he found himself transform<WJ>ed in his bed into a horrible vermin. He lay on his armour-like back, and i<ZWJ>f he lifted his head a little he could see his brown belly, slight<WJ>ly domed and divided by arches into stiff sections. Th<ZWNJ>e bedding was h<ZWJ>ardly able to cover it and seemed ready to slide off any moment. His many leg<BOM>s, pitifully thin co<ZWSP>mpared with the size of the rest of him, waved about helplessly as he l<BOM>ooked.
>
> > _(Markers such as `<ZWSP>` highlight otherwise invisible insertions.)_
>
> ---
>
> - **Armor Class** 13 (data veil)
> - **Hit Points** 11 (4d4 + 4)
> - **Speed** 0 ft., 40 wpm (ethereal drift)
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |1 |18 |8 |12 |14 |6 |
>
> ---
>
> - **Skills** Stealth +8, Perception +4
> - **Damage Resistances** radiant, force
> - **Condition Immunities** blinded, grappled
> - **Senses** blindsight 30 ft. (for glyphs only)
> - **Languages** understands Common, speaks only in silence
> - **Challenge** 1/4 (50 XP)
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
> - `rate (float)`: The maximum proportion of words to replace (default: 0.01, 1%).
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

## Ekkokin

_Did it come out wrong, or did you just hear what you expected?_

> Small Fey (echo), Neutral Mischief
>
> ---
>
> _**Echo Chamber.**_ Ekkokin replaces words with curated homophones drawn from a lovingly pruned lexicon. Every swap keeps the original casing and punctuation so the sentence still _sounds_ correct even while string comparisons drift.
>
> ### Ekkokin Args
>
> - `rate (float)`: Maximum proportion of eligible words to rewrite (default: 0.02, 2%).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import ekkokin
> >>> print(ekkokin(sample_text))
> ```
>
> > One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed inn his bed into a horrible vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of hymn, waved about helplessly as he looked.
>
> ---
>
> - **Armor Class** 12 (echoing shimmer)
> - **Hit Points** 22 (5d6 + 5)
> - **Speed** 30 ft., 40 bpm (metronomic sway)
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |8 |14 |12 |13 |11 |16 |
>
> ---
>
> - **Skills** Performance +5, Insight +3
> - **Damage Resistances** thunder (earplugs), psychic (skeptical audiences)
> - **Condition Immunities** deafened (selective hearing)
> - **Senses** passive Perception 13
> - **Languages** Common, Old Tongue homophones
> - **Challenge** 1 (200 XP)
>
> ---

## Rushmore

_I accidentally an entire word._

> Tiny Aberration (kinetic), Chaotic Neutral
>
> ---
>
> _**Hasty Omission.**_ Once known solely for erasing context, Rushmore now channels the full triad of word-level tricks: deletions, reduplications, and adjacent swaps. Pick which attack modes to unleash with `modes` and it will execute them in deterministic order using a shared RNG, mirroring the former Reduple and Adjax behaviours when those modes are selected.
>
> ### Rushmore Args
>
> - `modes (str | Sequence[str])`: Attack modes to enable ("delete", "duplicate", "swap", or any combination such as "all"). Order controls how effects chain.
> - `rate (float | None)`: Global rate applied to every enabled mode when a per-mode override is not supplied.
> - `delete_rate (float | None)`: Override for the deletion mode (default 0.01 when omitted).
> - `duplicate_rate (float | None)`: Override for the reduplication mode (default 0.01 when omitted).
> - `swap_rate (float | None)`: Override for the adjacent swap mode (default 0.5 when omitted).
> - `unweighted (bool)`: Toggle length-weighted sampling off for all modes that support it.
> - `delete_unweighted (bool | None)`: Per-mode override for deletion weighting.
> - `duplicate_unweighted (bool | None)`: Per-mode override for reduplication weighting.
> - `seed (int | None)`: Deterministic seed for this Rushmore instance.
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

## Redactyl

_Oops, that was my black highlighter._

> Medium Construct (bureaucratic), Lawful Neutral
>
> ---
>
> _**FOIA Reply.**_ Redactyl blankets selected words in block glyphs, hiding meaning while leaving punctuation and sentence structure intact.
>
> ### Redactyl Args
>
> - `replacement_char (str)`: The character to use for redaction (default: FULL_BLOCK).
> - `rate (float)`: The maximum proportion of words to redact (default: 0.025, 2.5%).
> - `merge_adjacent (bool)`: Whether neighbouring redactions collapse into a single bar (default: False).
> - `unweighted (bool)`: Sample words uniformly instead of biasing toward longer tokens (default: False).
> - `seed (int)`: The random seed for reproducibility (default: 151).
>
> ```python
> >>> from glitchlings import redactyl
> >>> print(redactyl(sample_text))
> ```
>
> > One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a ███████ vermin. He lay on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it and ████ seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.
>
> ---
>
> - **Armor Class** 15 (paper shield)
> - **Hit Points** 27 (5d8 + 5)
> - **Speed** 20 ft., 40 cpm (forms)
>
> ---
>
> |STR|DEX|CON|INT|WIS|CHA|
> |:---:|:---:|:---:|:---:|:---:|:---:|
> |10 |8 |14 |16 |9 |12 |
>
> ---
>
> - **Skills** Deception +5, Investigation +4
> - **Damage Resistances** psychic; immunity to transparency requests
> - **Languages** Common, Legalese
> - **Challenge** 2 (450 XP)
>
> ---

#

```plaintext
     .─') _                                       .─') _                  
    (  OO) )                                     ( OO ) )            
  ░██████  ░██ ░██   ░██               ░██        ░██ ░██                                 
 ░██   ░██ ░██       ░██                ░██        ░██                                     
░██        ░██ ░██░████████  ░███████   ░████████  ░██ ░██░████████   ░████████ ░███████  
░██  █████ ░██ ░██   ░██    ░██('─.░██ ░██    ░██ ░██ ░██░██    ░██ ░██.─')░██ ░██        
░██     ██ ░██ ░██   ░██    ░██( OO ) ╱░██    ░██ ░██ ░██░██    ░██ ░██(OO)░██ ░███████  
  ░██  ░███ ░██ ░██   ░██    ░██    ░██ ░██    ░██ ░██ ░██░██    ░██ ░██ o ░███      ░██ 
  ░█████░█ ░██ ░██   ░████   ░███████  ░██    ░██ ░██ ░██░██    ░██  ░█████░██ ░███████  
                                                                          ░██            
                                                                  ░███████             

                        Every language game breeds monsters.
```

![Python Versions](https://img.shields.io/pypi/pyversions/glitchlings.svg)
[![PyPI version](https://badge.fury.io/py/glitchlings.svg)](https://pypi.org/project/glitchlings/)
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

## Motivation

If your model performs well on a particular task, but not when `Glitchling`s are present, it's a sign that it hasn't actually generalized to the problem.

Conversely, training a model to perform well in the presence of the types of perturbations introduced by `Glitchling`s should help it generalize better.

## Quickstart

```python
pip install -U glitchlings
```

The fastest way to get started is to ask my assistant, `Auggie`, to prepare a custom mix of glitchlings for you:

```python
from glitchlings import Auggie, SAMPLE_TEXT

auggie = (
    Auggie(seed=404)
    .typo(rate=0.015)
    .confusable(rate=0.01)
    .homophone(rate=0.02)
)

print(auggie(SAMPLE_TEXT))
```

> One morning, when Gregor Samsa woke from troubld dreams, he found himself transformed in his bed into a horible vermin. He layed on his armour-like back, and if he lifted his head a little he could see his brown belly, slightly domed and divided by arches into stiff sections. The bedding was hardly able to cover it and seemed ready to slide off any moment. His many legs, pitifully thin compared with the size of the rest of him, waved about helplessly as he looked.

**You're more than welcome to summon them directly, if you're feeling brave:**

```python
from glitchlings import Gaggle, SAMPLE_TEXT, Typogre, Mim1c, Wherewolf

gaggle = Gaggle(
    [
        Typogre(rate=0.015),
        Mim1c(rate=0.01),
        Wherewolf(rate=0.02),
    ],
    seed=404
)
```

Consult the [Glitchlings Usage Guide](docs/index.md)
for end-to-end instructions spanning the Python API, CLI, and third-party integrations.

## Your First Battle

Summon your chosen `Glitchling` (_or a few, if ya nasty_) and call it on your text or slot it into `Dataset.map(...)`, supplying a seed if desired.
Glitchlings are standard Python classes:

```python
from glitchlings import Gaggle, Typogre, Mim1c

custom_typogre = Typogre(rate=0.1)
selective_mimic = Mim1c(rate=0.05, classes=["LATIN", "GREEK"])

gaggle = Gaggle([custom_typogre, selective_mimic], seed=99)
corrupted = gaggle("We Await Silent Tristero's Empire.")
print(corrupted)
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

Keyboard warriors can challenge them directly via the `glitchlings` command (see the generated CLI reference in `docs/cli.md` for the full contract):

```bash
# Discover which glitchlings are currently on the loose.
glitchlings --list
 
# Review the full CLI contract.
glitchlings --help
 
# Run Typogre against the contents of a file and inspect the diff.
glitchlings -g typogre --input-file documents/report.txt --diff

# Configure glitchlings inline by passing keyword arguments.
glitchlings -g "Typogre(rate=0.05)" "Ghouls just wanna have fun"

# Pipe text straight into the CLI for an on-the-fly corruption.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c

# Emit an Attack summary with metrics and counts.
glitchlings --attack --sample

# Emit a full Attack report with tokens, token IDs, and metrics.
glitchlings --report --sample
```

## Configuration Files

Configurations live in plain YAML files so you can version-control experiments without touching code:

```bash
# Load a roster from a YAML attack configuration.
glitchlings --config experiments/chaos.yaml "Let slips the glitchlings of war"
```

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

## Attack on Token

Looking to compare before/after corruption with metrics and stable seeds? Reach for the [`Attack` helper](docs/attack.md), which bundles tokenization, metrics, and transcript batching into a single utility. It accepts plain `list[str]` batches, renders quick `summary()` reports, and can compare multiple tokenizers via `Attack.compare(...)` when you need a metrics matrix.

## Development

Follow the [development setup guide](docs/development.md) for editable installs, automated tests, and tips on enabling the Rust pipeline while you hack on new glitchlings.

## Starter 'lings

For maintainability reasons, all `Glitchling` have consented to be given nicknames once they're in your care. See the [Monster Manual](MONSTER_MANUAL.md) for a complete bestiary.

### Typogre

_What a nice word, would be a shame if something happened to it._

> _**Fatfinger.**_ Typogre introduces character-level errors (duplicating, dropping, adding, or swapping) based on the layout of a keyboard (QWERTY by default, with Dvorak and Colemak variants built-in).
>
> Typogre supports **motor coordination weighting** based on biomechanical research from the Aalto 136M Keystrokes dataset. Use `motor_weighting="wet_ink"` for uncorrected errors (cross-hand typos slip through) or `motor_weighting="hastily_edited"` for raw typing patterns before correction.

### Mim1c

_Wait, was that...?_

> _**Confusion.**_ Mim1c replaces non-space characters with Unicode Confusables, characters that are distinct but would not usually confuse a human reader.
>
> **Substitution Modes:**
> - `single_script` (safest): Only same-script confusables (Latin→Latin variants)
> - `mixed_script` (default): Allow cross-script substitutions (Latin↔Cyrillic↔Greek)
> - `compatibility`: Include fullwidth, math alphanumerics, enclosed forms
> - `aggressive`: All confusable types combined
>
> **Locality Control:** Caps consecutive substitutions at 3 by default to prevent "ransom note" effect. Set `max_consecutive=0` to disable.
>
> **Script Affinity:** In mixed_script mode, substitutions are weighted by visual plausibility (Latin↔Cyrillic: 0.9, Latin↔Greek: 0.8).

### Hokey

_She's soooooo coooool!_

> _**Passionista.**_ Hokey gets a little excited and streeeeetches words for emphasis.
>
> _Apocryphal Glitchling contributed by Chloé Nunes_

### Scannequin

_How can a computer need reading glasses?_

> _**OCArtifacts.**_ Scannequin mimics optical character recognition errors by swapping visually similar character sequences (like rn↔m, cl↔d, O↔0, l/I/1).

### Zeedub

_Watch your step around here._

> _**Invisible Ink.**_ Zeedub slips zero-width codepoints between non-space character pairs, forcing models to reason about text whose visible form masks hidden glyphs.
>
> **Placement Modes:**
> - `random` (default): Insert between any adjacent non-whitespace characters
> - `grapheme_boundary`: Only insert at grapheme cluster boundaries (safer for rendering)
> - `script_aware`: ZWJ/ZWNJ only where linguistically meaningful (Arabic, Indic scripts, emoji)
>
> **Visibility Modes:**
> - `glyphless` (default): True invisibles only (ZWSP, ZWNJ, ZWJ, WJ, CGJ, BOM)
> - `with_joiners`: Adds variation selectors VS1–VS16
> - `semi_visible`: Adds hair space, thin space, narrow NBSP
>
> **Safety:** Caps consecutive insertions at 4 by default to prevent pathological sequences. Set `max_consecutive=0` to disable.

### Wherewolf

_Did you hear what I heard?_

> _**Echo Chamber.**_ Wherewolf swaps words with curated homophones so the text still sounds right while the spelling drifts. Groups are normalised to prevent duplicates and casing is preserved when substitutions fire.

### Jargoyle

_Uh oh. The worst person you know just bought a thesaurus._

> _**Sesquipedalianism.**_ Jargoyle insufferably replaces words with synonyms at random, without regard for connotational or denotational differences.

### Rushmore

_I accidentally an entire word._

> _**Tactical Scrambler.**_ Rushmore randomly drops, duplicates, or swaps words in the text to simulate hasty writing, editing mistakes, or transmission errors.

### Redactyl

_Oops, that was my black highlighter._

> _**FOIA Reply.**_ Redactyl obscures random words in your document like an NSA analyst with a bad sense of humor.

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

## References

Glitchlings incorporates research from the following sources:

- **Aalto 136M Keystrokes Dataset** — Motor coordination weights for Typogre's biomechanically-informed error sampling:
  > Dhakal, V., Feit, A. M., Kristensson, P. O., & Oulasvirta, A. (2018). Observations on Typing from 136 Million Keystrokes. *Proceedings of the 2018 CHI Conference on Human Factors in Computing Systems (CHI '18)*, Article 646. https://doi.org/10.1145/3173574.3174220

- **Expressive Lengthening Research** — Linguistic foundations for Hokey's stretchability scoring and site selection:
  > Brody, S., & Diakopoulos, N. (2011). Cooooooooooooooollllllllllllll!!!!!!!!!!!!!!: Using Word Lengthening to Detect Sentiment in Microtext. *Proceedings of the 2011 Conference on Empirical Methods in Natural Language Processing (EMNLP '11)*, 562–570. https://aclanthology.org/D11-1052

  > Gray, B., Bruxvoort, C., Beigman Klebanov, B., & Leong, B. (2020). Expressive Lengthening in Social Media. *Proceedings of the 12th Language Resources and Evaluation Conference (LREC 2020)*, 4517–4523. https://aclanthology.org/2020.lrec-1.556

- **OCR Degradation Modeling** — Theoretical foundations for Scannequin's document-level corruption, burst error clustering, and segmentation failures:
  > Kanungo, T., Haralick, R. M., & Phillips, I. (1994). Nonlinear Local and Global Document Degradation Models. *International Journal of Imaging Systems and Technology*, 5(3), 220–230. https://doi.org/10.1002/ima.1850050305

  > Li, Y., Lopresti, D., Nagy, G., & Tompkins, A. (1996). Validation of Image Defect Models for Optical Character Recognition. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 18(2), 99–107. https://doi.org/10.1109/34.481540

  > Kolak, O., & Resnik, P. (2002). OCR Error Correction Using a Noisy Channel Model. *Proceedings of the Second International Conference on Human Language Technology Research (HLT '02)*, 257–262. https://dl.acm.org/doi/10.5555/1289189.1289227

- **OCR Evaluation Methodology** — Benchmark methodology informing Scannequin's quality presets and parameter calibration:
  > Rice, S. V., Jenkins, F. R., & Nartker, T. A. (1995). The Fourth Annual Test of OCR Accuracy. Technical Report 95-04, Information Science Research Institute, University of Nevada, Las Vegas. https://tesseract-ocr.github.io/docs/AT-1995.pdf

  > Lucas, S. M., Panaretos, A., Sosa, L., Tang, A., Wong, S., & Young, R. (2005). ICDAR 2003 Robust Reading Competitions: Entries, Results, and Future Directions. *International Journal on Document Analysis and Recognition*, 7(2–3), 105–122. https://doi.org/10.1007/s10032-004-0134-3

- **Unicode Text Segmentation** — Grapheme cluster boundary rules for Zeedub's `grapheme_boundary` placement mode:
  > The Unicode Consortium. (2024). Unicode Standard Annex #29: Unicode Text Segmentation. https://www.unicode.org/reports/tr29/

- **Unicode Security Considerations** — Default_Ignorable handling and safety constraints informing Zeedub's visibility classification and max_consecutive limits:
  > The Unicode Consortium. (2014). Unicode Technical Report #36: Unicode Security Considerations. https://www.unicode.org/reports/tr36/

- **Unicode Confusables** — Script-aware confusable character mappings for Mim1c's substitution modes and script classification:
  > The Unicode Consortium. (2024). Unicode Technical Standard #39: Unicode Security Mechanisms. https://www.unicode.org/reports/tr39/

  > The Unicode Consortium. (2024). Confusables Data File. https://www.unicode.org/Public/security/latest/confusables.txt

- **Hypercorrection Research** — Sociolinguistic foundations for Pedant's coordinate-structure pronoun overcorrection and split infinitive patterns:
  > Collins, P. (2022). Hypercorrection in English: an intervarietal corpus-based study. *English Language & Linguistics*, 26(2), 279–305. https://doi.org/10.1017/S1360674321000101

  > Labov, W. (1966). Hypercorrection by the Lower Middle Class as a Factor in Linguistic Change. *Sociolinguistic Patterns*, 122–142. University of Pennsylvania Press.

  > Angermeyer, P. S., & Singler, J. V. (2003). The case for politeness: Pronoun variation in co-ordinate NPs in object position in English. *Language Variation and Change*, 15(2), 171–209. https://doi.org/10.1017/S0954394503152027

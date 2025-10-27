# Hokey

**"She's so cooooooool"**

Hokey now performs linguistically informed expressive lengthening. Instead of merely
stretching short words, it scores each token using lexical priors, sentiment windows,
phonotactic cues, and nearby punctuation before sampling a heavy-tailed stretch length.

- **Scope**: character level (first ordering – runs before other character-level glitchlings).
- **Signature**: `Hokey(rate=0.3, extension_min=2, extension_max=5, word_length_threshold=6, base_p=0.45, seed=None)`.
- **Behaviour**:
  1. Tokenises the text while preserving punctuation.
  2. Scores each alphabetic token with a composite *Stretchability Score* derived from
     lexical priors (e.g., *so, wow, cool*), pragmatic cues, sentiment bursts, and
     phonotactics.
  3. Selects top candidates per clause according to `rate`, skipping URLs, code, and
     proper nouns.
  4. Locates the best stretch site (vowel nuclei, digraphs, or sibilant codas) and
     samples a clipped negative-binomial length using `extension_min`, `extension_max`,
     and `base_p`.

- **Parameters**:
  - `rate` (float, default 0.3): Proportion of high-scoring tokens to stretch.
  - `extension_min` / `extension_max` (ints, defaults 2 / 5): Bounds for the number of
    additional repetitions.
  - `word_length_threshold` (int, default 6): Preferred maximum alphabetic length.
    Longer words receive intensity penalties but are not outright excluded.
  - `base_p` (float, default 0.45): Base success probability for the negative-binomial
    sampler. Lower values yield heavier tails (longer stretches).
  - `seed` (int, optional): Seed for deterministic behaviour.

- **Usage tips**:
  - Call `extend_vowels(..., return_trace=True)` to inspect the chosen stretch sites.
  - Lower `base_p` to produce occasional dramatic stretches while keeping most
    output moderate.
  - When combining with other character glitchlings, run Hokey first so later agents
    operate on the stretched text.
  - Reduce `word_length_threshold` to focus on interjections ("so", "lol", "wow");
    increase it when you want verbs and adjectives to join the fun.

- **Examples**:
  ```python
  from glitchlings import Hokey
  from glitchlings.zoo.hokey import extend_vowels

  # Default usage with moderate emphasis
  hokey = Hokey(seed=42)
  hokey("This is so cool and fun!")
  # "This is sooo cooool and fuuun!"

  # Inspect the trace
  text, events = extend_vowels(
      "wow that launch was so cool",
      rate=0.9,
      seed=7,
      return_trace=True,
  )
  for event in events:
      print(event.original, event.stretched, event.repeats, event.site.category)

  # Heavier tails by lowering base_p
  dramatic = Hokey(rate=0.7, extension_min=3, extension_max=8, base_p=0.3, seed=99)
  dramatic("no way this is real!!!")
  # "noooo waaay this is reaaaal!!!"
  ```

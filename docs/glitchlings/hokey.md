# Hokey

**"She's so cooooooool"**

Hokey extends vowels in short words to create an emphatic, drawn-out effect, mimicking enthusiastic or exaggerated speech patterns.

- **Scope**: character level (first ordering - runs before other character-level glitchlings).
- **Signature**: `Hokey(rate=0.3, extension_min=2, extension_max=5, word_length_threshold=6, seed=None)`.
- **Behaviour**: identifies short words containing vowels, randomly selects a proportion based on `rate`, then extends the last vowel in each selected word by repeating it multiple times. The extension length is randomly chosen between `extension_min` and `extension_max` repetitions.
- **Parameters**:
  - `rate` (float, default 0.3): Proportion of eligible short words to affect (0.0 to 1.0).
  - `extension_min` (int, default 2): Minimum number of extra vowel repetitions.
  - `extension_max` (int, default 5): Maximum number of extra vowel repetitions.
  - `word_length_threshold` (int, default 6): Maximum word length to be considered "short".
  - `seed` (int, optional): Random seed for deterministic behavior.
- **Usage tips**:
  - Chain Hokey early (it runs at "first" order) to apply emphasis before other character transformations.
  - Adjust `rate` to control how much emphasis appears in your text - lower values (0.1-0.3) create subtle effects, while higher values (0.7-1.0) produce more dramatic results.
  - Use `word_length_threshold` to target different word sizes - smaller values (3-4) affect only very short words like "so" and "fun", while larger values (8-10) include medium-length words.
  - Combine with Typogre or other character-level glitchlings to create layered text corruption effects.
- **Examples**:
  ```python
  from glitchlings import Hokey

  # Default usage with moderate emphasis
  hokey = Hokey(seed=42)
  result = hokey("This is so cool and fun!")
  # Output: "This is soooo cooool and fuuuun!"

  # High emphasis with longer extensions
  enthusiastic = Hokey(rate=0.8, extension_min=4, extension_max=8, seed=42)
  result = enthusiastic("wow amazing")
  # Output: "wooooow amaziiiiing"

  # Target only very short words
  subtle = Hokey(rate=0.5, word_length_threshold=3, seed=42)
  result = subtle("I am so ready to go")
  # Output: "I aaaam sooooo ready toooo goooo"
  ```

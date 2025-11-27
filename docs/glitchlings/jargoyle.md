# Jargoyle

Jargoyle swaps words with synonyms from bundled dictionaries to inject domain drift and vocabulary variety.

- **Scope**: word level.
- **Signature**: `Jargoyle(lexemes="synonyms", mode="drift", rate=0.01, seed=None)`.
- **Behaviour**: swaps words with synonyms from the selected lexeme dictionary. Available dictionaries: `synonyms` (general), `colors` (color names), `corporate` (business jargon), `academic` (scholarly terms), `cyberpunk` (neon slang), `lovecraftian` (cosmic horror). Drop any additional `*.json` lexeme file into `assets/lexemes/` to make it available without code changes.
- **Modes**:
  - `literal` — always uses the first synonym in the dictionary entry (deterministic regardless of seed).
  - `drift` — randomly selects among available synonyms using the seed for determinism.
- **Usage tips**:
  - Use `lexemes="colors"` to swap color words (e.g., "red" -> "crimson").
  - Use `mode="literal"` for fully deterministic output when seed independence is required.
  - Use the default `rate=0.01` for gentle lexical drift; raise it (0.02–0.05) when you need bolder paraphrases.
  - List available dictionaries with `list_lexeme_dictionaries()` from `glitchlings.zoo.jargoyle`.

# Rushmore

Rushmore deletes words to remove context and test summarisation resilience.

- **Scope**: word level.
- **Signature**: `Rushmore(max_deletion_rate=0.01, seed=None)`.
- **Behaviour**: deletes randomly selected words (skipping the first to preserve context) and tidies double spaces/punctuation afterwards.
- **Usage tips**:
  - Keep `max_deletion_rate` conservative (<0.03) to avoid stripping sentences bare.
  - Because the first word is preserved, prepend short context sentences when you need deletions deeper in the passage.
  - Sandwich between Reduple and Redactyl to test summarisation robustness under missing context.

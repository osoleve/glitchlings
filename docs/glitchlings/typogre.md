# Typogre

Typogre simulates fat-finger typing errors by swapping or duplicating characters based on keyboard adjacency maps.

- **Scope**: character level (early in the pipeline).
- **Signature**: `Typogre(max_change_rate=0.02, keyboard="CURATOR_QWERTY", seed=None)`.
- **Behaviour**: simulates fat-finger typing by swapping neighbouring keys, dropping spaces, inserting doubles, or choosing layout-adjacent characters. Keyboard layouts map through `glitchlings.util.KEYNEIGHBORS` and include curated QWERTY, DVORAK, and custom research boards.
- **Usage tips**:
  - Lower `max_change_rate` (0.005–0.01) for gentle noise; raise it for more chaotic misspellings.
  - Swap to `keyboard="DVORAK"` or supply a custom adjacency dict to model alternative hardware.
  - Combine with Rushmore deletions to simulate hurried note-taking.

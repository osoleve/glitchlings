# Typogre

Typogre simulates fat-finger typing errors by swapping or duplicating characters based on keyboard adjacency maps.

- **Scope**: character level (early in the pipeline).
- **Signature**: `Typogre(rate=0.02, keyboard="CURATOR_QWERTY", shift_slip_rate=0.0, shift_slip_exit_rate=None, seed=None)`.
- **Behaviour**: simulates fat-finger typing by swapping neighbouring keys, dropping spaces, inserting doubles, or choosing layout-adjacent characters. Keyboard layouts map through `glitchlings.util.KEYNEIGHBORS` and include curated QWERTY, DVORAK, and custom research boards. Modifier slippage is applied first via `SHIFT_MAPS`, producing short shift bursts before the standard fatfinger actions run.
- **Usage tips**:
  - Lower `rate` (0.005-0.01) for gentle noise; raise it for more chaotic misspellings.
  - Swap to `keyboard="DVORAK"` or supply a custom adjacency dict to model alternative hardware.
  - Enable `shift_slip_rate` for bursty modifier slips (e.g., `Typogre(rate=0.0, shift_slip_rate=1.0, seed=151)` turns `hello` into `HEllo` before any fatfinger edits).
  - Combine with Rushmore deletions to simulate hurried note-taking.

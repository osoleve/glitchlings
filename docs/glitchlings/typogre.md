# Typogre

Typogre simulates fat-finger typing errors by swapping or duplicating characters based on keyboard adjacency maps.

- **Scope**: character level (early in the pipeline).
- **Signature**: `Typogre(rate=0.02, keyboard="CURATOR_QWERTY", shift_slip_rate=0.0, shift_slip_exit_rate=None, motor_weighting="uniform", seed=None)`.
- **Behaviour**: simulates fat-finger typing by swapping neighbouring keys, dropping spaces, inserting doubles, or choosing layout-adjacent characters. Keyboard layouts map through `glitchlings.util.KEYNEIGHBORS` and include curated QWERTY, DVORAK, and custom research boards. Modifier slippage is applied first via `SHIFT_MAPS`, producing short shift bursts before the standard fatfinger actions run.
- **Usage tips**:
  - Lower `rate` (0.005-0.01) for gentle noise; raise it for more chaotic misspellings.
  - Swap to `keyboard="DVORAK"` or supply a custom adjacency dict to model alternative hardware.
  - Enable `shift_slip_rate` for bursty modifier slips (e.g., `Typogre(rate=0.0, shift_slip_rate=1.0, seed=151)` turns `hello` into `HEllo` before any fatfinger edits).
  - Use `motor_weighting` to simulate biomechanically-realistic error patterns (see below).
  - Combine with Rushmore deletions to simulate hurried note-taking.

## Motor Coordination Weighting

Typogre supports biomechanically-informed error weights derived from the [Aalto 136M Keystrokes dataset](https://userinterfaces.aalto.fi/136Mkeystrokes/). Research on 168,000 typists shows that typing errors aren't uniformly distributed across key transitions—error rates vary based on finger and hand coordination.

### Weighting Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `uniform` | All keyboard neighbors equally likely (default) | Original behavior, maximum chaos |
| `wet_ink` | Cross-hand errors slip through; same-finger errors are caught | Simulates hastily typed text with no proofreading |
| `hastily_edited` | Same-finger errors occur most often | Simulates raw typing before autocorrect/proofreading |

### How It Works

- **Same-finger transitions** (e.g., 'e' → 'd', both left middle finger): Errors feel "wrong" and are often caught
- **Same-hand transitions** (e.g., 'e' → 'f', same hand, different fingers): Moderate error detection
- **Cross-hand transitions** (e.g., 'e' → 'j', alternating hands): Errors feel "normal" and slip through

### Example

```python
from glitchlings import Typogre

# Default uniform weighting (original behavior)
typo = Typogre(rate=0.1)

# Wet ink: uncorrected errors that survive to final output
typo_wet = Typogre(rate=0.1, motor_weighting="wet_ink")

# Hastily edited: raw typing patterns before correction
typo_hasty = Typogre(rate=0.1, motor_weighting="hastily_edited")
```

### Citation

> Dhakal, V., Feit, A. M., Kristensson, P. O., & Oulasvirta, A. (2018). Observations on Typing from 136 Million Keystrokes. *CHI '18*. https://doi.org/10.1145/3173574.3174220

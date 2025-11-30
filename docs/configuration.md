# Configuration files

Glitchlings supports loading attack rosters from YAML configuration files, making it easy to version-control experiments and share reproducible corruption setups without touching code.

## Basic usage

Load a configuration file via the CLI:

```bash
glitchlings --config experiments/chaos.yaml "Let slip the glitchlings of war"
```

Or in Python:

```python
from glitchlings import load_attack_config, build_gaggle

config = load_attack_config("experiments/chaos.yaml")
gaggle = build_gaggle(config)
print(gaggle("Your text here"))
```

## Configuration schema

A YAML attack configuration requires a `glitchlings` list and optionally accepts a `seed`:

```yaml
# Required: list of glitchlings to apply
glitchlings:
  - typogre
  - mim1c

# Optional: master seed for deterministic corruption
seed: 404
```

## Glitchling entry formats

Each entry in the `glitchlings` list can use one of three formats:

### 1. Simple name (string)

Use the glitchling name with default parameters:

```yaml
glitchlings:
  - typogre
  - mim1c
  - rushmore
```

Names are case-insensitive, so `typogre`, `Typogre`, and `TYPOGRE` all work.

### 2. Inline specification (string)

Pass parameters using Python-style syntax:

```yaml
glitchlings:
  - "Typogre(rate=0.05)"
  - "Rushmore(modes='delete', rate=0.02)"
  - "Mim1c(rate=0.01, classes=['LATIN', 'CYRILLIC'])"
```

This mirrors the CLI `-g` flag syntax exactly.

### 3. Object with name and parameters

Use a mapping for clearer multi-parameter configurations:

```yaml
glitchlings:
  - name: Typogre
    rate: 0.04
    keyboard: DVORAK

  - name: Rushmore
    parameters:
      modes: [delete, swap]
      rate: 0.02
      unweighted: true

  - name: Zeedub
    parameters:
      rate: 0.02
      characters: ["\u200b", "\u2060"]
```

Parameters can be specified either:

- Directly as sibling keys to `name`
- Nested under a `parameters` key (useful when parameter names might conflict)

## Complete example

```yaml
# experiments/aggressive.yaml
seed: 31337

glitchlings:
  # Keyboard typos at 4%
  - name: Typogre
    rate: 0.04
    shift_slip_rate: 0.01

  # Word-level chaos
  - "Rushmore(modes=['delete', 'duplicate'], rate=0.03)"

  # Homoglyph confusion
  - name: Mim1c
    parameters:
      rate: 0.02
      classes: [LATIN, GREEK, CYRILLIC]

  # Zero-width character injection
  - name: Zeedub
    rate: 0.01

  # OCR artifacts
  - scannequin
```

## Loading in Python

The `load_attack_config` function returns an `AttackConfig` dataclass:

```python
from glitchlings import load_attack_config, build_gaggle

# Load from file path
config = load_attack_config("path/to/config.yaml")

# Access the parsed configuration
print(f"Seed: {config.seed}")
print(f"Glitchlings: {[g.name for g in config.glitchlings]}")

# Build a Gaggle from the config
gaggle = build_gaggle(config)

# Override the seed if needed
gaggle_with_new_seed = build_gaggle(config, seed_override=999)
```

You can also load from a file-like object:

```python
from io import StringIO
from glitchlings import load_attack_config

yaml_content = """
glitchlings:
  - typogre
seed: 123
"""

config = load_attack_config(StringIO(yaml_content))
```

## Validation

Configuration files are validated against a JSON schema. Common errors:

| Error | Cause |
|-------|-------|
| `must contain a top-level mapping` | File is empty or contains a list at the root |
| `glitchlings is required` | Missing the `glitchlings` key |
| `glitchling #N is missing a 'name'` | Object entry without a `name` field |
| `Unknown glitchling` | Glitchling name not recognized |
| `failed to instantiate` | Invalid parameters for the glitchling |

## Tips

- **Version control**: Check configuration files into your repository alongside experiment code
- **Layering**: Use multiple config files for different corruption intensities (light, medium, aggressive)
- **Debugging**: Start with a single glitchling and low rates, then add complexity
- **Seeds**: Always specify a seed for reproducible experiments

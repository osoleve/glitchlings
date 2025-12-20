# glitchlings-nemo

NVIDIA NeMo DataDesigner plugin for [Glitchlings](https://github.com/osoleve/glitchlings) text corruption.

## Installation

```bash
pip install glitchlings-nemo
```

Or install from source:

```bash
cd plugins/nemo
pip install -e .
```

## Usage

Once installed, the plugin is automatically discovered by DataDesigner:

```python
from data_designer import DataDesigner, DataDesignerConfigBuilder
from glitchlings_nemo import GlitchlingColumnConfig

builder = DataDesignerConfigBuilder()

# Add a corrupted text column
builder.add_column(
    GlitchlingColumnConfig(
        name="corrupted_prompt",
        source_column="prompt",
        glitchlings=["Typogre(rate=0.02)", "Mim1c(rate=0.01)"],
        seed=404,
    )
)

# Build and run
config = builder.build()
designer = DataDesigner(config)
result = designer.run()
```

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Output column name |
| `glitchlings` | `str \| list[str]` | `"typogre"` | Glitchling specification |
| `source_column` | `str \| None` | `None` | Column to corrupt (defaults to `name`) |
| `seed` | `int \| None` | `None` | RNG seed for determinism |

## Glitchling Specifications

The `glitchlings` parameter accepts several formats:

```python
# Single glitchling by name
glitchlings="typogre"

# With parameters
glitchlings="Typogre(rate=0.02)"

# Multiple glitchlings (applied in sequence)
glitchlings=["Typogre(rate=0.02)", "Mim1c(rate=0.01)", "Wherewolf(rate=0.03)"]

# Path to YAML config
glitchlings="configs/chaos.yaml"
```

## Available Glitchlings

| Name | Description |
|------|-------------|
| `Typogre` | Keyboard typos (adjacent key errors) |
| `Mim1c` | Unicode confusables (homoglyphs) |
| `Wherewolf` | Homophone substitution |
| `Hokey` | Word stretching (elongation) |
| `Jargoyle` | Synonym/jargon replacement |
| `Rushmore` | Word drop/duplicate/swap |
| `Redactyl` | Word redaction |
| `Scannequin` | OCR-style errors |
| `Zeedub` | Zero-width character injection |
| `Pedant` | Grammar pedantry transforms |

See the [Glitchlings documentation](https://github.com/osoleve/glitchlings) for full details.

## License

Apache-2.0

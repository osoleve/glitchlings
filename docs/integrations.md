# Integrations and DLC

Optional extras patch popular libraries to make corruption frictionless. This page is a **quick reference catalog**—for detailed tutorials and examples, see [Pipeline Workflows](pipeline-workflows.md).

## Hugging Face Datasets (`hf` extra)

- Use `glitchlings.dlc.huggingface.GlitchedDataset` to wrap a dataset and corrupt
  one or more explicit text columns.
- Reuse gaggle seeds to reproduce corrupted datasets across machines.

```python
from glitchlings.dlc.huggingface import GlitchedDataset

corrupted = GlitchedDataset(dataset, "typogre", column="text", seed=404)
```

## PyTorch (`torch` extra)

- Use `glitchlings.dlc.pytorch.GlitchedDataLoader` to wrap a `DataLoader`.
- Accepts glitchling names, instances, or gaggles; auto-inferring text columns from batches when
  `columns` is omitted.

```python
from glitchlings.dlc.pytorch import GlitchedDataLoader

glitched = GlitchedDataLoader(loader, ["typogre", "mim1c"], seed=404)
```

## Lightning (`lightning` extra)

- Use `glitchlings.dlc.pytorch_lightning.GlitchedLightningDataModule` to wrap a
  `LightningDataModule`. Specify the text column(s) to corrupt.
- Designed for evaluation corruption with minimal boilerplate.

```python
from glitchlings.dlc.pytorch_lightning import GlitchedLightningDataModule

glitched = GlitchedLightningDataModule(datamodule, "typogre", column="text", seed=404)
```

## LangChain (`langchain` extra)

- Use `glitchlings.dlc.langchain.GlitchedRunnable` to wrap LCEL runnables and
  glitch inputs (optionally outputs) without modifying the chain.
- Columns/fields are inferred from the first payload when omitted; pass
  `input_columns`/`output_columns` for explicit control.

```python
from glitchlings.dlc.langchain import GlitchedRunnable
from glitchlings import Typogre

glitched = GlitchedRunnable(chain, Typogre(rate=0.01), glitch_output=True, seed=404)
response = glitched.invoke({"question": "Who guards the guardians?"})
```

## NVIDIA NeMo DataDesigner (`nemo` extra)

- Install the `nemo` extra for `glitchlings.dlc.nemo`, or install the standalone
  plugin package `glitchlings-nemo` for automatic DataDesigner discovery.
- `GlitchlingColumnConfig` defines a text corruption column generator.
- Accepts glitchling names, specs with parameters, lists, or YAML config paths.
- Use `source_column` to corrupt a different column than the output.

```python
from data_designer import DataDesignerConfigBuilder
from glitchlings.dlc.nemo import GlitchlingColumnConfig

builder = DataDesignerConfigBuilder()
builder.add_column(
    GlitchlingColumnConfig(
        name="corrupted_prompt",
        source_column="prompt",
        glitchlings=["Typogre(rate=0.02)", "Mim1c(rate=0.01)"],
        seed=404,
    )
)
```

### Standalone Usage (without DataDesigner)

For direct DataFrame corruption without the full DataDesigner infrastructure:

```python
import pandas as pd
from glitchlings.dlc.nemo import corrupt_dataframe

df = pd.DataFrame({"text": ["Hello world", "Test input"]})
result = corrupt_dataframe(df, "typogre", column="text", seed=42)
```

### Flexible Glitchling Specifications

The plugin accepts multiple specification formats:

```python
# Pre-constructed Gaggle
from glitchlings import Gaggle, Typogre, Mim1c
gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)

# Auggie fluent builder
from glitchlings import Auggie
auggie = Auggie(seed=404).typo(rate=0.02).confusable(rate=0.01)

# String specification
glitchlings = "Typogre(rate=0.02)"

# List of specifications
glitchlings = ["Typogre(rate=0.02)", "Mim1c(rate=0.01)"]

# YAML config path
glitchlings = "configs/chaos.yaml"
```

## Prime Intellect (`prime` extra)

- Install the `prime` extra for `glitchlings.dlc.prime`.
- `load_environment` wraps `verifiers.load_environment` and injects glitchlings into benchmarks.
- `echo_chamber` bootstraps text-cleaning challenges directly from Hugging Face datasets.
- Pass `seed=` to keep corrupted environments deterministic.

## Project Gutenberg (`gutenberg` extra)

- Install the `gutenberg` extra for `glitchlings.dlc.gutenberg`.
- `GlitchenbergAPI` wraps the py-gutenberg `GutenbergAPI` and corrupts book text on fetch.
- Accepts glitchling names, instances, or gaggles; seeds for deterministic corruption.
- Original titles are preserved in `original_title` for comparison.
- Use `get_text()` to fetch and corrupt the full book content.

```python
from glitchlings.dlc.gutenberg import GlitchenbergAPI

api = GlitchenbergAPI("typogre", seed=42)
book = api.get_book(1342)  # Pride and Prejudice

# Access corrupted and original titles
print(book.title)           # Corrupted title
print(book.original_title)  # "Pride and Prejudice"

# Fetch and corrupt the full text content
full_text = book.get_text()
print(full_text[:100])  # First 100 chars of corrupted text
```

### Custom Gutendex Instance

By default, `GlitchenbergAPI` uses the public Gutendex instance. For production
use or high-volume requests, you can specify a custom instance URL:

```python
from glitchlings.dlc.gutenberg import DEFAULT_GUTENDEX_URL, GlitchenbergAPI

# Use default public instance
api = GlitchenbergAPI("typogre")

# Or specify a custom/self-hosted Gutendex instance
api = GlitchenbergAPI("typogre", instance_url="https://my-gutendex.example.com")
```

### Batch Processing

For batch corruption of books fetched from other sources:

```python
from glitchlings.dlc.gutenberg import GlitchenbergAPI

api = GlitchenbergAPI(["typogre", "mim1c"], seed=42)

# Corrupt multiple books at once
books = api.get_books_by_search("shakespeare")
for book in books:
    print(f"{book.original_title} → {book.title}")
```

## Installing extras

```bash
pip install 'glitchlings[hf]'          # datasets
pip install 'glitchlings[torch]'       # PyTorch DataLoader
pip install 'glitchlings[lightning]'   # Lightning DataModule
pip install 'glitchlings[langchain]'   # LangChain runnables
pip install 'glitchlings[nemo]'        # NeMo DataDesigner
pip install 'glitchlings[prime]'       # Prime Intellect DLC
pip install 'glitchlings[gutenberg]'   # Project Gutenberg
pip install 'glitchlings[all]'         # everything

# Alternatively, install the standalone NeMo plugin for auto-discovery:
pip install glitchlings-nemo
```

# Integrations and DLC

Optional extras patch popular libraries to make corruption frictionless.

## Hugging Face Datasets (`hf` extra)

- Import `glitchlings.dlc.huggingface` to register `Dataset.glitch(...)`.
- Column inference targets common text fields when `columns` is omitted.
- Reuse gaggle seeds to reproduce corrupted datasets across machines.

## PyTorch (`torch` extra)

- Import `glitchlings.dlc.pytorch` to register `DataLoader.glitch(...)`.
- Accepts glitchling names, instances, or gaggles; supports column inference similar to datasets.

## Lightning (`lightning` extra)

- Import `glitchlings.dlc.pytorch_lightning` to patch `LightningDataModule.glitch(...)`.
- Designed for evaluation corruption with minimal boilerplate.

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
pip install 'glitchlings[prime]'       # Prime Intellect DLC
pip install 'glitchlings[gutenberg]'   # Project Gutenberg
pip install 'glitchlings[all]'         # everything
```

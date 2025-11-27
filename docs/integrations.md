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
- `GlitchenbergAPI` wraps the py-gutenberg `GutenbergAPI` and corrupts book titles on fetch.
- Accepts glitchling names, instances, or gaggles; seeds for deterministic corruption.
- Original titles are preserved in `original_title` for comparison.

```python
from glitchlings.dlc.gutenberg import GlitchenbergAPI

api = GlitchenbergAPI("typogre", seed=42)
book = api.get_book(1342)  # Pride and Prejudice
print(book.title)           # Corrupted title
print(book.original_title)  # "Pride and Prejudice"
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

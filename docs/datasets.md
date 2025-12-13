# Dataset workflows

Perturb datasets reproducibly for training or evaluation.

## Hugging Face datasets

```python
from datasets import load_dataset
from glitchlings import Gaggle, Typogre, Mim1c

dataset = load_dataset("ag_news")
gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)

corrupted = gaggle.corrupt_dataset(
    dataset,
    columns=["text"],
)
```

Prefer the wrapper when you want a standalone view:

```python
from glitchlings.dlc.huggingface import GlitchedDataset

corrupted = GlitchedDataset(dataset, "typogre", column="text", seed=404)
```

Notes:

- Explicit columns are required for dataset corruption; pass one or more names to target.
- The returned dataset is a lazy view; persist it with `push_to_hub(...)` or `save_to_disk(...)`.
- Keep the gaggle seed stable to reproduce corruption across machines.

## PyTorch DataLoader

Wrap a `DataLoader` with the DLC helper:

```python
from torch.utils.data import DataLoader
from glitchlings.dlc.pytorch import GlitchedDataLoader
from glitchlings import Typogre

loader = DataLoader(dataset, batch_size=32)
noisy_loader = GlitchedDataLoader(loader, Typogre(rate=0.02), columns=["text"])
```

When `columns` is omitted, `GlitchedDataLoader` infers textual fields from the first batch.

## LangChain runnables

Glitch LCEL chains without changing your graph:

```python
from glitchlings import Typogre
from glitchlings.dlc.langchain import GlitchedRunnable

glitched = GlitchedRunnable(chain, Typogre(rate=0.02), glitch_output=True, seed=404)
response = glitched.invoke({"question": "Where did the glitches go?"})
```

- `input_columns`/`output_columns` can specify which fields to corrupt; omit to
  infer from the first payload/response.

## Prime environments

Use the `prime` extra to inject glitchlings into RL environments:

```python
from glitchlings import Mim1c, Typogre
from glitchlings.dlc.prime import load_environment

env = load_environment(
    "osoleve/syllabify-en",
    glitchlings=[Mim1c(rate=0.01), Typogre(rate=0.02)],
    seed=404,
    columns=["prompt"],
)
```

- Inputs can be environment slugs, instantiated environments, glitchling names, instances, or gaggles.
- `columns=None` triggers the same prompt/question inference; pass explicit columns to constrain targets.

## Tips for large runs

- Run with the compiled Rust pipeline enabled for speed.
- Profile with a small subset before batch-corrupting large corpora.
- Persist seeds alongside experiment metadata so results are reproducible.

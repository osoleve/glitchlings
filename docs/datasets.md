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
    columns=["text"],  # inferred when omitted
    description="ag_news with typographic noise",
)
```

Notes:

- When `columns` is omitted, Glitchlings infers targets (`prompt`, `question`, or all string columns).
- The returned dataset is a shallow copy containing both clean and corrupted columns—persist it with `push_to_hub(...)` or `save_to_disk(...)`.
- Keep the gaggle seed stable to reproduce corruption across machines.

## PyTorch DataLoader

Import the DLC to patch `torch.utils.data.DataLoader.glitch(...)`:

```python
import glitchlings.dlc.pytorch  # registers .glitch
from torch.utils.data import DataLoader
from glitchlings import Typogre

loader = DataLoader(dataset, batch_size=32)
noisy_loader = loader.glitch(Typogre(rate=0.02), columns=["text"])
```

Column inference mirrors the dataset helper when `columns` is omitted.

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

# Pipeline Workflows

This page provides **detailed tutorials** for integrating glitchlings into your ML pipelines. For a quick reference of all available extras, see [Integrations & DLC](integrations.md).

Glitchlings integrate with popular ML libraries so you can inject corruption into datasets, data loaders, and inference chains without rewriting your pipeline. The key principle: specify which columns contain text, pass a seed for reproducibility, and let the glitchlings do the rest.

## Hugging Face Datasets

Two approaches: use the Gaggle's built-in method, or wrap the dataset with a dedicated helper.

### Gaggle Method

```python
from datasets import load_dataset
from glitchlings import Gaggle, Typogre, Mim1c

dataset = load_dataset("ag_news", split="train")
gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)

corrupted = gaggle.corrupt_dataset(dataset, columns=["text"])
```

The `columns` parameter is required—you must explicitly specify which fields to corrupt. This prevents accidental corruption of labels or metadata.

### Wrapper Class

For a standalone view that you can pass around:

```python
from datasets import load_dataset
from glitchlings.dlc.huggingface import GlitchedDataset

dataset = load_dataset("ag_news", split="train")
corrupted = GlitchedDataset(dataset, "typogre", column="text", seed=404)

# Use like any other HF dataset
for example in corrupted:
    print(example["text"])  # Corrupted
```

### Important Notes

**Lazy evaluation** — The returned dataset is a lazy view. Corruption happens on access, not upfront. This is memory-efficient for large datasets but means the first iteration is slower.

**Persistence** — To save the corrupted version, use standard HF methods:

```python
corrupted.save_to_disk("corrupted_ag_news/")
# or
corrupted.push_to_hub("yourname/corrupted-ag-news")
```

**Reproducibility** — Keep the gaggle seed stable across machines. Same seed + same input order = same corruption.

## PyTorch DataLoader

Wrap an existing DataLoader to corrupt batches on the fly:

```python
from torch.utils.data import DataLoader
from glitchlings.dlc.pytorch import GlitchedDataLoader
from glitchlings import Typogre

# Your existing loader
loader = DataLoader(dataset, batch_size=32, shuffle=True)

# Wrap it
noisy_loader = GlitchedDataLoader(
    loader,
    Typogre(rate=0.02),
    columns=["text"],
    seed=404
)

# Use as normal
for batch in noisy_loader:
    # batch["text"] is corrupted
    # other fields are untouched
    pass
```

### Column Inference

If you omit `columns`, the wrapper inspects the first batch and corrupts any field that looks like text (strings or lists of strings). This is convenient but can be surprising—explicit is better than implicit:

```python
# Explicit: corrupt only the "question" field
noisy = GlitchedDataLoader(loader, typo, columns=["question"])

# Implicit: let it guess (risky if you have multiple text fields)
noisy = GlitchedDataLoader(loader, typo)
```

## LangChain Runnables

Wrap LCEL chains to corrupt inputs, outputs, or both—without modifying the chain itself:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from glitchlings import Typogre
from glitchlings.dlc.langchain import GlitchedRunnable

# Build your chain as usual
prompt = ChatPromptTemplate.from_template("Answer: {question}")
chain = prompt | ChatOpenAI()

# Wrap it
glitched = GlitchedRunnable(
    chain,
    Typogre(rate=0.02),
    glitch_output=True,  # Also corrupt the response
    seed=404
)

response = glitched.invoke({"question": "What is the capital of France?"})
# Both input and output have typos
```

### Field Control

Specify which fields to corrupt:

```python
# Only corrupt the question field in input
glitched = GlitchedRunnable(chain, typo, input_columns=["question"])

# Only corrupt the content field in output
glitched = GlitchedRunnable(chain, typo, output_columns=["content"])
```

If omitted, fields are inferred from the first payload.

## Prime Intellect Environments

For RL experiments with the Prime ecosystem:

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

The `load_environment` helper wraps `verifiers.load_environment` and injects glitchlings into the benchmark's text fields. Inputs can be environment slugs, instantiated environments, or any combination of glitchling names and instances.

## Tips for Large Runs

**Use Rust** — The compiled Rust pipeline is significantly faster than pure Python. Install with the default build to enable it automatically.

**Profile first** — Before corrupting a million examples, test on a small subset to verify your configuration produces sensible output.

**Persist seeds** — Save seeds alongside experiment metadata. A corrupted dataset without its seed is unreproducible.

**Batch carefully** — For streaming datasets, corruption happens per-batch. If you change batch size, the corruption pattern changes (same seed, different output).

## Install Commands

```bash
pip install 'glitchlings[hf]'        # Hugging Face datasets
pip install 'glitchlings[torch]'     # PyTorch DataLoader
pip install 'glitchlings[langchain]' # LangChain runnables
pip install 'glitchlings[prime]'     # Prime Intellect
pip install 'glitchlings[all]'       # Everything
```

## See Also

- [Integrations & DLC](integrations.md) — Complete list of optional extras
- [Determinism Guide](determinism.md) — Seed hygiene for reproducible runs
- [Configuration Files](configuration.md) — YAML-based experiment configs

# LM-Eval Integration with Glitchconf Support

This integration provides seamless glitchling corruption for [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) evaluations. This is particularly useful for evaluating models trained with [Prime Intellect](https://github.com/PrimeIntellect-ai/prime) or any other training framework.

## Overview

The `glitchlings.dlc.prime_inference` module wraps lm-eval's evaluation pipeline to apply glitchling corruption to evaluation inputs. This allows you to:

- Test model robustness to typos, homoglyphs, and other text perturbations
- Run deterministic, reproducible evaluations with seeded corruption
- Compare model performance across different corruption profiles
- Use the same lm-eval interface you're familiar with, enhanced with glitchconf support

## Installation

Install glitchlings with lm-eval support:

```bash
pip install glitchlings
pip install lm-eval
```

For a complete setup with all Prime Intellect features:

```bash
pip install 'glitchlings[prime]'
pip install lm-eval
```

## Command-Line Interface

The `glitchlings prime-eval` command shadows the lm-eval CLI with added support for the `--glitchconf` flag:

### Basic Usage

```bash
glitchlings prime-eval \
    --model hf \
    --model_args pretrained=meta-llama/Llama-2-7b-hf \
    --tasks hellaswag \
    --glitchconf experiments/chaos.yaml \
    --seed 42
```

### With Multiple Tasks

```bash
glitchlings prime-eval \
    --model hf \
    --model_args pretrained=gpt2 \
    --tasks hellaswag,arc_easy,mmlu \
    --glitchconf experiments/mild_corruption.yaml \
    --seed 151 \
    --num_fewshot 10
```

### With Inline Glitchling Specification

You can also specify glitchlings directly without a YAML file:

```bash
glitchlings prime-eval \
    --model hf \
    --model_args pretrained=gpt2 \
    --tasks hellaswag \
    --glitchconf "Typogre(rate=0.05)" \
    --seed 42 \
    --limit 100
```

### Available Flags

#### Glitchconf-Specific Flags

- `--glitchconf PATH_OR_SPEC` (required): Path to YAML attack config or inline glitchling specification
- `--seed INT`: Random seed for deterministic corruption (default: 151)
- `--corruption-fields FIELD [FIELD ...]`: Specific fields to corrupt (default: query, context, question)

#### Standard lm-eval Flags

All standard lm-eval flags are supported:

- `--model`: Model type (e.g., "hf" for HuggingFace)
- `--model_args`: Model arguments (e.g., "pretrained=gpt2")
- `--tasks`: Comma-separated list of evaluation tasks
- `--num_fewshot`: Number of few-shot examples
- `--batch_size`: Batch size for evaluation
- `--device`: Device to use (cuda, cpu, etc.)
- `--limit`: Limit number of examples (useful for testing)
- `--verbosity`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- And many more...

Run `glitchlings prime-eval --help` for a complete list.

## Python API

### Basic Evaluation

```python
from glitchlings.dlc.prime_inference import eval_with_glitchconf

results = eval_with_glitchconf(
    model="hf",
    model_args="pretrained=gpt2",
    tasks=["hellaswag"],
    glitchconf="experiments/chaos.yaml",
    seed=42,
    limit=100,
)

print(results["results"]["hellaswag"])
```

### With Pre-Built Gaggle

```python
from glitchlings import Gaggle, Typogre, Mim1c
from glitchlings.dlc.prime_inference import eval_with_glitchconf

# Create custom corruption profile
gaggle = Gaggle([
    Typogre(rate=0.03),
    Mim1c(rate=0.02),
], seed=42)

results = eval_with_glitchconf(
    model="hf",
    model_args="pretrained=meta-llama/Llama-2-7b-hf",
    tasks=["hellaswag", "arc_easy"],
    glitchconf=gaggle,
    seed=42,
)
```

### With Inline Glitchling List

```python
from glitchlings import Typogre, Mim1c, Reduple
from glitchlings.dlc.prime_inference import eval_with_glitchconf

results = eval_with_glitchconf(
    model="hf",
    model_args="pretrained=gpt2",
    tasks=["hellaswag"],
    glitchconf=[
        Typogre(rate=0.05),
        Mim1c(rate=0.02),
        Reduple(reduplication_rate=0.01),
    ],
    seed=123,
)
```

### Custom Corruption Fields

By default, the evaluation corrupts `query`, `context`, and `question` fields. You can customize this:

```python
results = eval_with_glitchconf(
    model="hf",
    tasks=["hellaswag"],
    glitchconf="experiments/chaos.yaml",
    corruption_fields=["prompt", "passage"],
    seed=42,
)
```

## Glitchconf YAML Format

Create YAML configuration files to define reusable corruption profiles:

### Simple Configuration

```yaml
glitchlings:
  - Typogre
  - Mim1c
seed: 42
```

### Advanced Configuration with Parameters

```yaml
glitchlings:
  - name: Typogre
    rate: 0.03
  - name: Mim1c
    rate: 0.02
  - name: Reduple
    reduplication_rate: 0.01
  - name: Rushmore
    rate: 0.005
seed: 151
```

### Example Corruption Profiles

**Mild Corruption** (`experiments/mild.yaml`):
```yaml
glitchlings:
  - name: Typogre
    rate: 0.01
  - name: Apostrofae
    rate: 0.005
seed: 42
```

**Moderate Corruption** (`experiments/moderate.yaml`):
```yaml
glitchlings:
  - name: Typogre
    rate: 0.03
  - name: Mim1c
    rate: 0.02
  - name: Reduple
    reduplication_rate: 0.01
seed: 42
```

**Heavy Corruption** (`experiments/chaos.yaml`):
```yaml
glitchlings:
  - name: Typogre
    rate: 0.05
  - name: Mim1c
    rate: 0.03
  - name: Reduple
    reduplication_rate: 0.02
  - name: Rushmore
    rate: 0.01
  - name: Jargoyle
    rate: 0.02
seed: 42
```

## How It Works

The integration works by wrapping lm-eval task instances with a `GlitchedTaskWrapper` that intercepts text processing:

1. **Task Wrapping**: Each lm-eval task is wrapped with `GlitchedTaskWrapper`
2. **Text Interception**: The wrapper intercepts `doc_to_text()` and `construct_requests()` calls
3. **Corruption Application**: Configured glitchlings corrupt the text before it reaches the model
4. **Evaluation**: The corrupted text is evaluated normally through lm-eval
5. **Results**: Standard lm-eval results are returned with corrupted inputs

### Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│            lm-eval Task System                   │
│  ┌───────────────────────────────────────────┐  │
│  │  GlitchedTaskWrapper                      │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │  Original Task                      │  │  │
│  │  │  - doc_to_text()                    │  │  │
│  │  │  - construct_requests()             │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  │           ↓                                │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │  Gaggle (Corruption Pipeline)       │  │  │
│  │  │  - Typogre                          │  │  │
│  │  │  - Mim1c                            │  │  │
│  │  │  - ...                              │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────┘  │
│           ↓                                      │
│  Corrupted Text → Model → Results                │
└─────────────────────────────────────────────────┘
```

## Determinism and Reproducibility

All evaluations are fully deterministic when using the same seed:

```python
# These will produce identical results
results1 = eval_with_glitchconf(
    model="hf",
    tasks=["hellaswag"],
    glitchconf="experiments/chaos.yaml",
    seed=42,
)

results2 = eval_with_glitchconf(
    model="hf",
    tasks=["hellaswag"],
    glitchconf="experiments/chaos.yaml",
    seed=42,
)

assert results1 == results2
```

The seed is propagated to:
- Glitchling corruption (via Gaggle)
- lm-eval's random seed
- NumPy random seed
- PyTorch random seed
- Few-shot example sampling

## Use Cases

### Model Robustness Testing

Test how models perform under realistic text corruption:

```bash
# Baseline (no corruption)
lm_eval --model hf --model_args pretrained=gpt2 --tasks hellaswag

# With corruption
glitchlings prime-eval \
    --model hf \
    --model_args pretrained=gpt2 \
    --tasks hellaswag \
    --glitchconf experiments/chaos.yaml \
    --seed 42
```

### Comparative Analysis

Compare different models' robustness:

```bash
for model in gpt2 gpt2-medium gpt2-large; do
    echo "Testing $model..."
    glitchlings prime-eval \
        --model hf \
        --model_args pretrained=$model \
        --tasks hellaswag,arc_easy \
        --glitchconf experiments/moderate.yaml \
        --seed 42
done
```

### Corruption Profile Tuning

Find optimal corruption levels for your use case:

```python
from glitchlings import Typogre
from glitchlings.dlc.prime_inference import eval_with_glitchconf

# Test different corruption rates
for rate in [0.01, 0.02, 0.03, 0.05, 0.1]:
    print(f"\nTesting rate={rate}")
    results = eval_with_glitchconf(
        model="hf",
        model_args="pretrained=gpt2",
        tasks=["hellaswag"],
        glitchconf=[Typogre(rate=rate)],
        seed=42,
        limit=100,
    )
    acc = results["results"]["hellaswag"]["acc"]
    print(f"Accuracy: {acc:.4f}")
```

## Advanced Topics

### Custom Task Fields

If your task uses non-standard field names, specify them:

```python
results = eval_with_glitchconf(
    model="hf",
    tasks=["custom_task"],
    glitchconf="experiments/chaos.yaml",
    corruption_fields=["input_text", "reference"],
    seed=42,
)
```

### Integration with Prime Training

Prime is a distributed training framework. After training, you evaluate models using lm-eval (which Prime recommends). Here's the full workflow:

```bash
# 1. Train with Prime (https://github.com/PrimeIntellect-ai/prime)
uv run torchrun --nproc_per_node=2 src/zeroband/train.py @configs/10B/H100.toml

# 2. Export checkpoint to HuggingFace format
uv run python scripts/export_dcp.py @configs/10B/H100.toml \
    --ckpt.path /path/to/model \
    --ckpt.resume /path/to/checkpoint

# 3. Evaluate with lm-eval + glitchconf
glitchlings prime-eval \
    --model hf \
    --model_args pretrained=/path/to/model \
    --tasks hellaswag,arc_easy,mmlu \
    --glitchconf experiments/chaos.yaml \
    --seed 42
```

**Note**: Prime itself is a training framework and doesn't have built-in evaluation. It uses lm-eval for evaluations, which is what this integration extends with glitchconf support.

### Batch Evaluation

Evaluate multiple corruption profiles:

```python
from pathlib import Path
from glitchlings.dlc.prime_inference import eval_with_glitchconf

configs = Path("experiments").glob("*.yaml")
results_all = {}

for config_path in configs:
    print(f"Evaluating {config_path.name}...")
    results = eval_with_glitchconf(
        model="hf",
        model_args="pretrained=gpt2",
        tasks=["hellaswag"],
        glitchconf=str(config_path),
        seed=42,
        limit=100,
    )
    results_all[config_path.stem] = results["results"]["hellaswag"]["acc"]

# Print summary
for config_name, acc in sorted(results_all.items()):
    print(f"{config_name:20s} {acc:.4f}")
```

## API Reference

### `eval_with_glitchconf`

```python
def eval_with_glitchconf(
    model: str | Any,
    tasks: list[str] | str,
    glitchconf: str | Path | Gaggle | list[Glitchling] | Glitchling,
    *,
    model_args: str | None = None,
    num_fewshot: int | None = None,
    batch_size: int | str | None = None,
    device: str | None = None,
    seed: int = 151,
    corruption_fields: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]
```

Run lm_eval evaluation with glitchling corruption.

**Parameters:**
- `model`: Model name or instance (e.g., "hf")
- `tasks`: List of task names or single task name
- `glitchconf`: Glitchling config (YAML path, Gaggle, or glitchlings)
- `model_args`: Model arguments string
- `num_fewshot`: Number of few-shot examples
- `batch_size`: Batch size
- `device`: Device (cuda, cpu, etc.)
- `seed`: Random seed for deterministic corruption
- `corruption_fields`: Fields to corrupt (default: query, context, question)
- `**kwargs`: Additional lm-eval arguments

**Returns:**
- Dictionary with evaluation results

### `GlitchedTaskWrapper`

```python
class GlitchedTaskWrapper:
    def __init__(
        self,
        task: Any,
        gaggle: Gaggle,
        corruption_fields: list[str] | None = None,
    )
```

Wrapper that applies glitchling corruption to task text.

**Parameters:**
- `task`: Original lm-eval task instance
- `gaggle`: Gaggle to apply for corruption
- `corruption_fields`: Fields to corrupt

### `create_glitched_task_dict`

```python
def create_glitched_task_dict(
    task_dict: dict[str, Any],
    gaggle: Gaggle,
    corruption_fields: list[str] | None = None,
) -> dict[str, Any]
```

Wrap all tasks with glitchling corruption.

**Parameters:**
- `task_dict`: Dictionary of task name → task instance
- `gaggle`: Gaggle to apply
- `corruption_fields`: Fields to corrupt

**Returns:**
- Dictionary of wrapped task instances

## Troubleshooting

### Import Error: No module named 'lm_eval'

Install lm-evaluation-harness:

```bash
pip install lm-eval
```

### Task Not Found

Ensure the task is available in lm-eval:

```bash
lm_eval --tasks list
```

### CUDA Out of Memory

Reduce batch size or limit examples:

```bash
glitchlings prime-eval \
    --model hf \
    --tasks hellaswag \
    --glitchconf chaos.yaml \
    --batch_size 1 \
    --limit 100
```

### Non-Deterministic Results

Ensure you're using the same seed and the same version of:
- glitchlings
- lm-eval
- transformers
- PyTorch

## See Also

- [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) - The evaluation framework this integration extends
- [Prime Intellect](https://github.com/PrimeIntellect-ai/prime) - Distributed training framework that uses lm-eval for evaluations
- [Glitchling Reference](../glitchling-gallery.md) - Available corruption types
- [Declarative Attack Configurations](../index.md#declarative-attack-configurations) - YAML config format

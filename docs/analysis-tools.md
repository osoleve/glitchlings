# Analysis Tools

The attack module provides four analysis tools for systematically exploring how corruption affects tokenization. Each tool answers a different question:

| Tool | Question It Answers |
|------|---------------------|
| **SeedSweep** | "How variable are the results across random seeds?" |
| **GridSearch** | "What parameter values produce the best results?" |
| **compare_tokenizers** | "Which tokenizer is most affected by this corruption?" |
| **compare_glitchlings** | "Which corruption strategy is most effective?" |

## When to Use Each Tool

### Use SeedSweep when...

You want to understand the **statistical distribution** of outcomes rather than a single point estimate:

- Reporting robust metrics with confidence intervals
- Detecting high-variance corruption strategies
- Finding seeds that produce extreme outcomes
- Validating that corruption effects are consistent

**Intuition:** A single seed might give you an unusually high or low result. SeedSweep runs many seeds and tells you the mean, standard deviation, min, max, and median—giving you a complete picture of what to expect.

### Use GridSearch when...

You want to **tune parameters** for a specific goal:

- Finding the corruption rate that maximizes token disruption
- Discovering the "sweet spot" where corruption is noticeable but text remains readable
- Systematically exploring how multiple parameters interact
- Optimizing for a specific metric threshold

**Intuition:** Instead of manually trying `rate=0.01`, `rate=0.02`, etc., GridSearch tests all combinations and ranks them by your chosen metric.

### Use compare_tokenizers when...

You want to understand **tokenizer sensitivity**:

- Comparing how different models would perceive the same corruption
- Finding which tokenizer is most robust to your corruption
- Demonstrating that BPE tokenizers fragment differently on corrupted text
- Benchmarking across tokenizer generations (GPT-2 vs GPT-4)

**Intuition:** The same corrupted text can look very different to different tokenizers. One tokenizer might see it as 5 tokens, another as 15 tokens with completely different IDs.

### Use compare_glitchlings when...

You want to **compare corruption strategies**:

- Determining which glitchling is most disruptive for your use case
- Creating a "most effective attacker" profile
- Understanding which corruption type produces specific effects
- Building intuition about different corruption modes

**Intuition:** Typos, homophone swaps, and Unicode confusables are all "corruption," but they affect tokenization in fundamentally different ways.

---

## SeedSweep

Runs the same attack configuration across many random seeds to collect aggregate statistics.

### Basic Usage

```python
from glitchlings import Typogre, SeedSweep

sweep = SeedSweep(Typogre(rate=0.05), tokenizer="cl100k_base")
result = sweep.run("Hello world", seeds=range(100))

print(result.summary())
```

### Understanding the Output

```python
# Aggregate statistics per metric
print(result.aggregate_stats["normalized_edit_distance"])
# {"mean": 0.15, "std": 0.02, "min": 0.10, "max": 0.22, "median": 0.14}
```

The aggregate stats tell you:

- **mean**: The expected value across random seeds
- **std**: How much variation to expect (higher = less predictable)
- **min/max**: The extremes you might encounter
- **median**: The typical case (robust to outliers)

**When std is high:** Your corruption is highly variable. Consider using a higher rate for more consistent effects, or a different glitchling for more predictable outcomes.

**When min and max differ significantly:** There's a wide range of possible outcomes. If you need consistency, you may want to control the seed or adjust parameters.

### Finding Extreme Seeds

```python
# Find seeds that produced high disruption
high_impact = result.filter_by_metric(
    "normalized_edit_distance",
    min_value=0.2  # Only seeds with NED >= 0.2
)

for seed, attack_result in high_impact.items():
    print(f"Seed {seed}: {attack_result.corrupted}")
```

**Use case:** Finding "adversarial" seeds that maximize disruption, or "benign" seeds that minimize it.

### Progress Monitoring

```python
def on_progress(completed):
    print(f"Completed {len(completed)} / 1000 seeds")

result = sweep.run(
    text,
    seeds=range(1000),
    progress_callback=on_progress,
)
```

### Early Stopping

Stop the sweep when you find what you're looking for:

```python
result = sweep.run(
    text,
    seeds=range(10000),
    early_stop=lambda seed, result: result.metrics["normalized_edit_distance"] > 0.5,
)
print(f"Found high-disruption seed: {result.seeds[-1]}")
```

---

## GridSearch

Systematically searches parameter combinations to find optimal settings.

### Basic Usage

```python
from glitchlings import Typogre, GridSearch

grid = GridSearch(
    Typogre,
    param_grid={"rate": [0.01, 0.05, 0.1, 0.2]},
    tokenizer="cl100k_base",
)
result = grid.run("Hello world", rank_by="normalized_edit_distance")

print(result.summary())
print(f"Best rate: {result.best_point.params['rate']}")
```

### Multi-Parameter Search

Search across multiple parameters simultaneously:

```python
grid = GridSearch(
    Typogre,
    param_grid={
        "rate": [0.01, 0.05, 0.1],
        "transpose_rate": [0.0, 0.2, 0.4],
        "insert_rate": [0.0, 0.1, 0.2],
    },
    tokenizer="cl100k_base",
)
result = grid.run(text, rank_by="normalized_edit_distance", minimize=False)
```

This tests all 27 combinations (3 × 3 × 3) and finds the most disruptive configuration.

### Ranking Direction

- `minimize=True` (default): Lower metric values are better (e.g., minimize error)
- `minimize=False`: Higher metric values are better (e.g., maximize disruption)

```python
# Find most disruptive configuration
result = grid.run(text, rank_by="normalized_edit_distance", minimize=False)

# Find configuration with minimal token changes
result = grid.run(text, rank_by="subsequence_retention", minimize=False)
```

### Interpreting Results

```python
# View all tested combinations
for point in result.points:
    print(f"{point.params} -> NED={point.metrics['normalized_edit_distance']:.4f}")

# Filter by metric threshold
good_configs = result.filter_by_metric(
    "normalized_edit_distance",
    min_value=0.1,
    max_value=0.3,
)

# Filter by specific parameter values
low_rate_configs = result.filter_by_params(rate=0.01)
```

### Base Parameters

Set default parameters that aren't being searched:

```python
grid = GridSearch(
    Typogre,
    param_grid={"rate": [0.01, 0.05, 0.1]},
    base_params={"transpose_rate": 0.5},  # Fixed for all combinations
)
```

---

## compare_tokenizers

Applies the same corruption once, then tokenizes with multiple tokenizers to compare how each perceives the result.

### Basic Usage

```python
from glitchlings import Typogre, compare_tokenizers

result = compare_tokenizers(
    "Hello world",
    Typogre(rate=0.1),
    tokenizers=["cl100k_base", "o200k_base", "gpt2"],
    seed=42,
)

print(result.summary())
```

### Why Tokenizers Matter

Consider the corrupted string "Hé11o wör1d":

- **cl100k_base** might tokenize it as: `["H", "é", "11", "o", " wör", "1", "d"]`
- **gpt2** might tokenize it as: `["H", "é", "1", "1", "o", " w", "ö", "r", "1", "d"]`

Same text, completely different token sequences. This affects:

- **Token count**: More tokens = more cost per API call
- **Attention patterns**: Different token boundaries change what the model "sees"
- **Embeddings**: Token IDs map to different embedding vectors

### Understanding the Comparison

```python
# Metrics side-by-side
for metric, values in result.metric_comparison.items():
    print(f"{metric}:")
    for tokenizer, value in values.items():
        print(f"  {tokenizer}: {value:.4f}")

# Token count changes
for entry in result.entries:
    input_count = len(entry.result.input_tokens)
    output_count = len(entry.tokens)
    print(f"{entry.tokenizer_name}: {input_count} -> {output_count} tokens")
```

### Use Case: Finding Robust Tokenizers

```python
# Which tokenizer handles typos best?
result = compare_tokenizers(
    long_text,
    Typogre(rate=0.05),
    tokenizers=["cl100k_base", "o200k_base", "gpt2", "r50k_base"],
)

# Lower NED = less affected by corruption
for entry in result.entries:
    ned = entry.metrics["normalized_edit_distance"]
    print(f"{entry.tokenizer_name}: NED={ned:.4f}")
```

---

## compare_glitchlings

Compares multiple corruption strategies on the same text with the same tokenizer.

### Basic Usage

```python
from glitchlings import Typogre, Mim1c, Ekkokin, compare_glitchlings

result = compare_glitchlings(
    "Hello world",
    [
        ("typogre", Typogre(rate=0.05)),
        ("confusables", Mim1c(rate=0.05)),
        ("homophones", Ekkokin(rate=0.05)),
    ],
    tokenizer="o200k_base",
)

print(result.summary())
```

### Finding the Most Disruptive Strategy

```python
# Rank by disruption (higher NED = more disruptive)
ranked = result.rank_by("normalized_edit_distance", minimize=False)

print("Most disruptive strategies:")
for entry in ranked[:3]:
    print(f"  {entry.name}: NED={entry.metrics['normalized_edit_distance']:.4f}")
```

### Understanding Different Corruption Modes

Different glitchlings affect metrics differently:

| Corruption Type | Typical Effect |
|-----------------|----------------|
| **Typogre** (typos) | Moderate NED, high MSI (fragments tokens) |
| **Mim1c** (Unicode) | Low NED if confusables map to same tokens, otherwise high |
| **Ekkokin** (homophones) | Variable—depends on tokenizer vocabulary |
| **Rushmore** (word shuffle) | High NED, low SR (reordering destroys sequence) |

```python
# Compare character-level vs word-level corruption
result = compare_glitchlings(
    text,
    [
        ("char_typos", Typogre(rate=0.05)),
        ("word_drop", Rushmore(rate=0.05, drop_rate=1.0, dup_rate=0.0, swap_rate=0.0)),
        ("word_dup", Rushmore(rate=0.05, drop_rate=0.0, dup_rate=1.0, swap_rate=0.0)),
        ("word_swap", Rushmore(rate=0.05, drop_rate=0.0, dup_rate=0.0, swap_rate=1.0)),
    ],
    tokenizer="cl100k_base",
)
```

---

## Export and Integration

All result classes support data export for further analysis.

### CSV Export

```python
# SeedSweep
sweep_result.export_csv("sweep_results.csv")

# GridSearch
grid_result.export_csv("grid_results.csv", include_params=True)

# Comparisons
comparison_result.export_csv("comparison.csv")
```

### Pandas Integration

Requires `pip install pandas`:

```python
# SeedSweep -> DataFrame (seeds as index, metrics as columns)
df = sweep_result.to_dataframe()
df.describe()  # Statistical summary

# GridSearch -> DataFrame (params and metrics as columns)
df = grid_result.to_dataframe()
df.sort_values("normalized_edit_distance")

# Comparison -> DataFrame (names as index, metrics as columns)
df = comparison_result.to_dataframe()
df.plot(kind="bar")  # Visualization
```

### JSON Reports

```python
import json

# All result types have to_report()
report = result.to_report()
print(json.dumps(report, indent=2))
```

---

## Combining Tools

The tools work well together for comprehensive analysis:

```python
from glitchlings import (
    Typogre, Mim1c, Ekkokin,
    SeedSweep, GridSearch,
    compare_glitchlings, compare_tokenizers,
)

text = "The quick brown fox jumps over the lazy dog."

# Step 1: Which glitchling is most effective?
glitch_comparison = compare_glitchlings(
    text,
    [
        ("typogre", Typogre(rate=0.1)),
        ("mim1c", Mim1c(rate=0.1)),
        ("ekkokin", Ekkokin(rate=0.1)),
    ],
    tokenizer="cl100k_base",
)
best_glitchling = glitch_comparison.rank_by("normalized_edit_distance", minimize=False)[0]
print(f"Most effective: {best_glitchling.name}")

# Step 2: What's the optimal rate for that glitchling?
grid = GridSearch(
    Typogre,  # Using the winner
    param_grid={"rate": [0.01, 0.02, 0.05, 0.1, 0.15, 0.2]},
)
grid_result = grid.run(text, rank_by="normalized_edit_distance", minimize=False)
best_rate = grid_result.best_point.params["rate"]
print(f"Optimal rate: {best_rate}")

# Step 3: How consistent is this configuration?
sweep = SeedSweep(Typogre(rate=best_rate))
sweep_result = sweep.run(text, seeds=range(100))
print(f"NED: {sweep_result.aggregate_stats['normalized_edit_distance']}")

# Step 4: Which tokenizer is most affected?
tokenizer_comparison = compare_tokenizers(
    text,
    Typogre(rate=best_rate),
    tokenizers=["cl100k_base", "o200k_base", "gpt2"],
)
print(tokenizer_comparison.summary())
```

---

## Performance Considerations

### SeedSweep

- **Memory**: Stores all `AttackResult` objects. For very large sweeps, use `progress_callback` to process incrementally.
- **Speed**: Linear in number of seeds. Use `early_stop` to terminate early when you find what you need.

### GridSearch

- **Combinatorial explosion**: A grid with 4 parameters × 10 values each = 10,000 combinations. Start small and expand.
- **Independence**: Each combination is independent—could be parallelized in future versions.

### Comparisons

- **Same corruption**: `compare_tokenizers` applies corruption once, then re-tokenizes. Very efficient.
- **Different corruptions**: `compare_glitchlings` runs corruption separately for each. Cost scales with number of glitchlings.

---

## API Reference

For complete method signatures and parameters, see the source code or use Python's built-in help:

```python
from glitchlings import SeedSweep, GridSearch
help(SeedSweep)
help(GridSearch.run)
```

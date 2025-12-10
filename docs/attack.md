# Attack module

The `glitchlings.attack.Attack` helper runs a roster of glitchlings, tokenises both the clean and corrupted text, and reports similarity metrics in one call. It mirrors the rest of the library's determinism guarantees while handling transcripts as batches.

## When to use it

- You want the **original, corrupted text, tokens, token IDs, and metrics** in a single object.
- You need **deterministic runs** without hand-rolling Gaggle construction and seeding.
- You plan to **compare transcript-style chat turns**: transcripts are treated as batches and metrics return one value per turn.

## Parameters

- `glitchlings`: A `Glitchling`, a `Gaggle`, or any sequence of glitchlings. Sequences are wrapped in a `Gaggle`.
- `seed`: Master seed used when constructing a `Gaggle` from a sequence (defaults to `DEFAULT_ATTACK_SEED`). If you pass an existing `Gaggle` or `Glitchling`, Attack clones it before applying the seed so your original object stays untouched while the Attack-owned copy is reseeded.
- `transcript_target`: Controls which transcript turns are corrupted. See below for options.
- `tokenizer`: Optional tokenizer name or object. Defaults to a modern `tiktoken` encoding (`o200k_base`, falling back to `cl100k_base`, then whitespace). Hugging Face `tokenizers.Tokenizer` instances and names are also supported.
- `metrics`: Mapping of metric names to callables. Defaults to the Rust-backed `jensen_shannon_divergence`, `normalized_edit_distance`, and `subsequence_retention`.
- Sequences must contain glitchling instances; mixed types raise a `TypeError` at construction.

## Transcript handling

If you pass a transcript (list of dicts containing `content`), `Attack`:

- Treats each turn as a separate sample in a batch.
- Encodes each turn independently.
- Returns per-turn metrics as lists (aligned with the transcript order).
- Returns empty metric lists for empty transcripts (no turns in, no turns out).

Input and output types must match; mixed string/transcript pairs raise an error.

### Controlling which turns are corrupted

The `transcript_target` parameter controls which transcript turns are corrupted:

| Value | Effect |
|-------|--------|
| `"last"` | Corrupt only the last turn (default). |
| `"all"` | Corrupt all turns. |
| `"assistant"` | Corrupt only turns with `role="assistant"`. |
| `"user"` | Corrupt only turns with `role="user"`. |
| `int` | Corrupt a specific turn by index (negative indexing supported). |
| `Sequence[int]` | Corrupt multiple specific turns by index. |

This setting is available on `Attack`, `Gaggle`, and `Glitchling`. The default (`"last"`) matches the previous implicit behaviour.

```python
from glitchlings import Typogre, Gaggle
from glitchlings.attack import Attack

# Corrupt only assistant turns
attack = Attack([Typogre()], transcript_target="assistant")

# Or set it directly on a Gaggle
gaggle = Gaggle([Typogre()], transcript_target="all")
```

## Plain string batches

`Attack.run` accepts simple `list[str]` batches in addition to transcripts. Each entry is corrupted independently, tokenised, and scored, with metrics returned per element:

```python
attack = Attack(["Typogre(rate=0.02)"])
batched = attack.run(["left", "right"])
print(batched.metrics["normalized_edit_distance"])  # -> [0.0, 0.21]
```

## Example

```python
from glitchlings import Mim1c, Rushmore, Typogre
from glitchlings.attack import Attack

attack = Attack(
    [Rushmore(rate=0.05), Mim1c(rate=0.02), Typogre(rate=0.03)],
    seed=404,
)

result = attack.run("Glitchlings keep your evaluations honest.")
print(result.metrics["normalized_edit_distance"])
print(result.input_tokens)
print(result.output_tokens)
```

## Quick summaries

`AttackResult.summary()` renders a compact, human-readable view of token drift and metrics without manual iteration:

```python
summary = result.summary(max_rows=6)
print(summary)
```

It highlights token count deltas, metric values, and a small token-by-token comparison (truncated to keep the output scannable).

## Comparing tokenizers

Use `compare_tokenizers()` to benchmark multiple tokenizers against the same corruption:

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

This applies the same corruption once, then tokenizes with each tokenizer to compare impacts.

## Comparing glitchlings

Use `compare_glitchlings()` to find which corruption strategy has the most impact for a specific tokenizer:

```python
from glitchlings import Typogre, Mim1c, Wherewolf, compare_glitchlings

result = compare_glitchlings(
    "Hello world",
    [
        ("typogre", Typogre(rate=0.05)),
        ("confusables", Mim1c(rate=0.05)),
        ("homophones", Wherewolf(rate=0.05)),
    ],
    tokenizer="o200k_base",
)

print(result.summary())

# Find most disruptive glitchling
best = result.rank_by("normalized_edit_distance", minimize=False)[0]
print(f"Most disruptive: {best.name}")
```

## MetricName enum

Use `MetricName` for type-safe metric references with IDE completion:

```python
from glitchlings import MetricName
from glitchlings.attack import Attack

# Reference individual metrics
print(MetricName.NED.value)  # "normalized_edit_distance"

# Get the function for a metric
ned_func = MetricName.NED.func

# Get all default metrics as a dict
attack = Attack(Typogre(), metrics=MetricName.defaults())
```

Available metrics:

| Enum | Value | Description |
|------|-------|-------------|
| `MetricName.JSD` | `jensen_shannon_divergence` | Token distribution divergence |
| `MetricName.NED` | `normalized_edit_distance` | Edit distance normalized to [0,1] |
| `MetricName.SR` | `subsequence_retention` | Fraction of tokens preserved |
| `MetricName.HD` | `entropy_delta` | Change in token entropy [-1,1] |
| `MetricName.MSI` | `merge_split_index` | Subword merge/split events [0,1] |

## Token-level analysis

`AttackResult` provides methods for detailed token analysis:

```python
result = attack.run("Hello world")

# Get tokens that changed
changes = result.get_changed_tokens()  # [(orig, corrupted), ...]

# Get positions of mutations
positions = result.get_mutation_positions()  # [0, 3, 5, ...]

# Get detailed alignment with operation markers
alignment = result.get_token_alignment()
# [{"index": 0, "original": "Hello", "corrupted": "He1lo", "changed": True, "op": "!"}, ...]
```

For batch results, pass `batch_index` to analyze a specific item.

## Analysis tools

The attack module includes four analysis tools for systematic exploration. For detailed documentation with use cases, intuition, and examples, see the [Analysis Tools](analysis-tools.md) page.

| Tool | Purpose |
|------|---------|
| **SeedSweep** | Run attacks across many seeds to get aggregate statistics (mean, std, min, max, median) |
| **GridSearch** | Search parameter combinations to find optimal settings |
| **compare_tokenizers** | Compare how different tokenizers perceive the same corruption |
| **compare_glitchlings** | Compare different corruption strategies on the same text |

### Quick examples

```python
from glitchlings import SeedSweep, GridSearch, Typogre

# SeedSweep: understand variance across random seeds
sweep = SeedSweep(Typogre(rate=0.05), tokenizer="cl100k_base")
result = sweep.run("Hello world", seeds=range(100))
print(result.aggregate_stats["normalized_edit_distance"])
# {"mean": 0.15, "std": 0.02, "min": 0.10, "max": 0.22, "median": 0.14}

# GridSearch: find optimal parameters
grid = GridSearch(Typogre, param_grid={"rate": [0.01, 0.05, 0.1, 0.2]})
result = grid.run("Hello world", rank_by="normalized_edit_distance")
print(f"Best rate: {result.best_point.params['rate']}")
```

```python
from glitchlings import compare_tokenizers, compare_glitchlings, Typogre, Mim1c

# Compare tokenizers: same corruption, different tokenization
result = compare_tokenizers(
    "Hello world",
    Typogre(rate=0.1),
    tokenizers=["cl100k_base", "o200k_base", "gpt2"],
)
print(result.summary())

# Compare glitchlings: different corruptions, same tokenizer
result = compare_glitchlings(
    "Hello world",
    [("typos", Typogre(rate=0.05)), ("unicode", Mim1c(rate=0.05))],
    tokenizer="cl100k_base",
)
best = result.rank_by("normalized_edit_distance", minimize=False)[0]
print(f"Most disruptive: {best.name}")
```

## Pandas integration

Result classes provide `to_dataframe()` for analysis in pandas (requires `pip install pandas`):

```python
# SeedSweep results
df = sweep_result.to_dataframe()  # seeds as index, metrics as columns

# GridSearch results
df = grid_result.to_dataframe()  # params and metrics as columns

# Glitchling comparison
df = comparison_result.to_dataframe()  # glitchling names as index
```

## CSV export

Export results directly to CSV:

```python
sweep_result.export_csv("sweep_results.csv")
grid_result.export_csv("grid_results.csv", include_params=True)
```

## CLI reports

Prefer to stay in the terminal? The `glitchlings` CLI exposes the same report via `--report` and `--attack`:

```bash
# Output attack summary (metrics and counts) as JSON (default)
glitchlings --attack --sample

# Output full report as YAML
glitchlings --report --format yaml "Corrupt me"

# Specify a tokenizer for the report
glitchlings --attack --tokenizer cl100k_base --sample

# Save report to a file
glitchlings --report -t gpt-4 -o report.json "Corrupt me"
```

## Choosing a tokenizer

By default, Attack uses a lightweight `tiktoken` encoder:

- Tries `o200k_base` first (good coverage for modern LLM contexts).
- Falls back to `cl100k_base`, then to a whitespace tokenizer if tiktoken is unavailable.
- Pass a name (e.g., `"gpt2"`), a `tiktoken.Encoding`, a Hugging Face `tokenizers.Tokenizer`, or a custom object implementing `encode`/`decode`.

### Tokenizer caching

Resolved tokenizers are cached automatically for efficient reuse across multiple `Attack` instances. The cache holds up to 16 tokenizers with LRU eviction.

```python
from glitchlings.attack import (
    clear_tokenizer_cache,
    get_tokenizer_cache_info,
)

# Check cache state
info = get_tokenizer_cache_info()
print(f"Cached: {info['size']} / {info['max_size']}")
print(f"Keys: {info['cached_keys']}")

# Clear cache (useful for testing or memory constraints)
cleared = clear_tokenizer_cache()
print(f"Cleared {cleared} cached tokenizers")
```

To bypass the cache for a specific resolution:

```python
from glitchlings.attack.tokenization import resolve_tokenizer

# Force fresh tokenizer instance
tokenizer = resolve_tokenizer("cl100k_base", use_cache=False)
```

## Streaming and large datasets

For processing many texts or very large token sequences, the attack module provides streaming capabilities.

### Processing many texts with run_stream

Use `run_stream()` to process an iterator of texts without holding all results in memory:

```python
from glitchlings import Typogre
from glitchlings.attack import Attack

attack = Attack(Typogre(rate=0.05))

# Process texts one at a time
def load_texts():
    for line in open("large_corpus.txt"):
        yield line.strip()

for result in attack.run_stream(load_texts()):
    # Process each result immediately
    print(f"NED: {result.metrics['normalized_edit_distance']:.4f}")
```

### Windowed token access with StreamingAttackResult

For results with very large token sequences, use `run_streaming_result()` to get windowed access:

```python
result = attack.run_streaming_result(very_long_text, window_size=5000)

# Iterate over token windows without loading all at once
for window in result.stream_input_tokens():
    print(f"Window {window.start_index}: {len(window.tokens)} tokens")
    if window.is_last:
        print("Processing final window")

# Get token counts without full materialization
input_count, output_count = result.get_token_count()
print(f"Tokens: {input_count} -> {output_count}")

# Stream paired input/output windows for comparison
for input_window, output_window in result.stream_token_pairs():
    # Process aligned windows
    pass
```

**Note:** `StreamingAttackResult` provides windowed *access* to tokens, not lazy loading. The tokens are still stored in memory after the attack runs. For true memory savings with many texts, use `run_stream()` to process texts one at a time.

### Lightweight results without tokens

When you only need metrics and don't need the actual token lists, use `include_tokens=False` for reduced memory usage:

```python
# Lightweight result - metrics only, no tokens stored
result = attack.run(text, include_tokens=False)
print(result.metrics)  # Full metrics computed
print(result.input_tokens)  # [] - empty list
print(result.output_tokens)  # [] - empty list

# Also works with batch and streaming
results = attack.run_batch(texts, include_tokens=False)
for result in attack.run_stream(texts, include_tokens=False):
    print(result.metrics["normalized_edit_distance"])
```

**Note:** Metrics are still computed from the tokens internally—only the storage of tokens in the result is skipped. This is useful when processing many texts where you only need aggregate statistics.

## Tokenizer analysis metrics

Beyond corruption metrics, the attack module provides metrics for analyzing tokenizer behavior:

```python
from glitchlings.attack import (
    compression_ratio,
    characters_per_token,
    token_entropy,
    vocabulary_utilization,
    unknown_token_rate,
    analyze_tokenizer,
)
from glitchlings.attack.tokenization import resolve_tokenizer

tokenizer = resolve_tokenizer("cl100k_base")
text = "Hello, world! This is a test."
tokens, token_ids = tokenizer.encode(text)
```

### Available metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| `compression_ratio` | UTF-8 bytes per token | Lower = more compact encoding |
| `characters_per_token` | Characters per token | Higher = fewer tokens needed |
| `token_entropy` | Shannon entropy of token distribution | Higher = more uniform usage |
| `vocabulary_utilization` | Unique ratio, repetition rate, ID spread | Vocabulary coverage analysis |
| `unknown_token_rate` | Fraction of OOV/fallback tokens | Higher = poor domain coverage |

### Individual metrics

```python
# Encoding efficiency
print(f"Bytes/token: {compression_ratio(text, tokens):.2f}")
print(f"Chars/token: {characters_per_token(text, tokens):.2f}")

# Token distribution
print(f"Entropy: {token_entropy(tokens):.4f} bits")

# Vocabulary usage
stats = vocabulary_utilization(tokens, token_ids)
print(f"Unique ratio: {stats['unique_ratio']:.2%}")
print(f"Max token ID: {stats['max_id']:.0f}")
print(f"ID spread: {stats['id_spread']:.2f}")

# Unknown token detection
unk_rate = unknown_token_rate(tokens)
if unk_rate > 0.05:
    print(f"Warning: {unk_rate:.1%} unknown tokens")
```

### Comprehensive analysis

Use `analyze_tokenizer()` for all metrics at once:

```python
stats = analyze_tokenizer(text, tokenizer)
for key, value in stats.items():
    print(f"{key}: {value:.4f}")
```

Returns a dictionary with: `compression_ratio`, `characters_per_token`, `token_entropy`, `unknown_token_rate`, `unique_ratio`, `repetition_rate`, `max_id`, `id_spread`, and `token_count`.

### Batch processing

All tokenizer metrics have batch variants for efficient bulk analysis:

```python
from glitchlings.attack import (
    batch_compression_ratio,
    batch_token_entropy,
    batch_vocabulary_utilization,
)

texts = ["Hello world", "Goodbye world", "Testing 123"]
batch_data = [tokenizer.encode(t) for t in texts]
token_batches = [d[0] for d in batch_data]
id_batches = [d[1] for d in batch_data]

# Batch metrics
ratios = batch_compression_ratio(texts, token_batches)
entropies = batch_token_entropy(token_batches)
vocab_stats = batch_vocabulary_utilization(token_batches, id_batches)

for i, text in enumerate(texts):
    print(f"{text}: ratio={ratios[i]:.2f}, entropy={entropies[i]:.4f}")
```

## Determinism

- Default seeds align with the rest of the library (`DEFAULT_ATTACK_SEED = 151`).
- Passing `seed=` stabilises both roster ordering and per-glitchling RNGs when Attack builds the `Gaggle`.
- When a `Gaggle` or `Glitchling` instance is supplied directly, Attack clones it before applying the seed so caller-owned instances are never mutated while the Attack copy is reseeded.

## Metrics and performance

The default metrics include five Rust-accelerated metrics:

**Rust-accelerated (fast):**
- **Jensen-Shannon divergence** (`jensen_shannon_divergence`) - Distribution similarity
- **Normalized edit distance** (`normalized_edit_distance`) - Token-level changes
- **Subsequence retention** (`subsequence_retention`) - Preserved tokens
- **Entropy delta** (`entropy_delta`) - Change in token distribution entropy, normalized to [-1, 1]
- **Merge-split index** (`merge_split_index`) - Measures subword restructuring (1→k splits and k→1 merges)

Custom metrics can be supplied; they should accept two token sequences or two batches of token sequences and return either a float or a list of floats.

## Built-in metric reference

This section provides detailed explanations and mathematical definitions for each built-in metric.

### Choosing the right metric

Different metrics capture different aspects of corruption impact:

| If you want to measure... | Use this metric |
|---------------------------|-----------------|
| Overall sequence difference | **NED** (Normalized Edit Distance) |
| Vocabulary/distribution shift | **JSD** (Jensen-Shannon Divergence) |
| How much original content survives | **SR** (Subsequence Retention) |
| Whether tokens became more/less diverse | **HD** (Entropy Delta) |
| Subword boundary disruption | **MSI** (Merge-Split Index) |

**Practical guidance:**

- **For general "how bad is it?"**: Start with NED—it's intuitive and captures most effects.
- **For adversarial attacks**: Use MSI—it specifically measures tokenization boundary disruption.
- **For preservation testing**: Use SR—it tells you what fraction of the original survived.
- **For distribution analysis**: Use JSD—it ignores order and focuses on vocabulary changes.
- **For detecting degenerate outputs**: Use HD—negative values indicate collapsed/repetitive text.

### Jensen-Shannon Divergence (JSD)

**Range:** `[0, 1]` where 0 = identical distributions, 1 = completely disjoint

**Purpose:** Measures how different the token frequency distributions are between original and corrupted text. Unlike KL-divergence, JSD is symmetric and always bounded.

**Mathematical definition:**

Given token sequences $A$ and $B$, compute their probability distributions $P$ and $Q$ where each token's probability is its count divided by the total token count:

$$P(t) = \frac{\text{count}_A(t)}{|A|}, \quad Q(t) = \frac{\text{count}_B(t)}{|B|}$$

The mixture distribution is:

$$M(t) = \frac{1}{2}(P(t) + Q(t))$$

Jensen-Shannon divergence is the average of KL-divergences from each distribution to the mixture:

$$\text{JSD}(P \| Q) = \frac{1}{2} D_{\text{KL}}(P \| M) + \frac{1}{2} D_{\text{KL}}(Q \| M)$$

where the KL-divergence is:

$$D_{\text{KL}}(P \| M) = \sum_{t} P(t) \log_2 \frac{P(t)}{M(t)}$$

**Interpretation:**
- **0.0**: Identical token distributions (same tokens in same proportions)
- **~0.1-0.3**: Minor distribution shift (a few tokens changed)
- **~0.5+**: Significant vocabulary change
- **1.0**: Completely disjoint vocabularies (no tokens in common)

**Use case:** Best for detecting wholesale vocabulary shifts where the *types* of tokens change rather than their order.

---

### Normalized Edit Distance (NED)

**Range:** `[0, 1]` where 0 = identical sequences, 1 = completely different

**Purpose:** Measures the minimum number of token insertions, deletions, and substitutions needed to transform the original sequence into the corrupted one, normalized by sequence length.

**Mathematical definition:**

The Levenshtein distance $d(A, B)$ is computed via dynamic programming:

$$d_{i,j} = \begin{cases}
j & \text{if } i = 0 \\
i & \text{if } j = 0 \\
d_{i-1,j-1} & \text{if } A_i = B_j \\
1 + \min(d_{i-1,j}, d_{i,j-1}, d_{i-1,j-1}) & \text{otherwise}
\end{cases}$$

Normalized edit distance scales by the maximum sequence length:

$$\text{NED}(A, B) = \frac{d(A, B)}{\max(|A|, |B|)}$$

**Edge cases:**
- Both sequences empty: returns 0.0
- One sequence empty: returns 1.0

**Interpretation:**
- **0.0**: Sequences are identical
- **0.1**: ~10% of tokens need to change
- **0.5**: Half the tokens differ
- **1.0**: Complete replacement required

**Use case:** The most intuitive measure of "how different" two sequences are. Captures both content and ordering changes.

---

### Subsequence Retention (SR)

**Range:** `[0, 1]` where 1 = all tokens preserved in order, 0 = no common subsequence

**Purpose:** Measures what fraction of the original tokens survive in the corrupted output, preserving their relative order. Based on the Longest Common Subsequence (LCS).

**Mathematical definition:**

The LCS length $\text{LCS}(A, B)$ is computed via dynamic programming:

$$L_{i,j} = \begin{cases}
0 & \text{if } i = 0 \text{ or } j = 0 \\
L_{i-1,j-1} + 1 & \text{if } A_i = B_j \\
\max(L_{i-1,j}, L_{i,j-1}) & \text{otherwise}
\end{cases}$$

Subsequence retention normalizes by the original sequence length:

$$\text{SR}(A, B) = \frac{\text{LCS}(A, B)}{|A|}$$

**Edge cases:**
- Original sequence empty: returns 1.0 (nothing to preserve)
- Output sequence empty: returns 0.0 (everything lost)

**Interpretation:**
- **1.0**: All original tokens appear in corrupted output in order
- **0.8**: 80% of tokens survive with order preserved
- **0.5**: Half the tokens are gone or reordered
- **0.0**: No tokens retained in their original order

**Use case:** Measures preservation of the original content. Unlike NED, SR ignores insertions—a corrupted text with extra tokens can still have SR=1.0 if all originals are present.

---

### Entropy Delta (HD)

**Range:** `[-1, 1]` where negative = simpler, positive = more complex

**Purpose:** Measures how the diversity of the token distribution changed. Positive values mean the corrupted text has more varied tokens; negative values mean it became more repetitive.

**Mathematical definition:**

Shannon entropy for a token sequence:

$$H(X) = -\sum_{t} P(t) \log_2 P(t)$$

where $P(t)$ is the probability of token $t$ in the sequence.

The raw entropy delta is:

$$\Delta H = H(\text{corrupted}) - H(\text{original})$$

To normalize to $[-1, 1]$, we divide by the maximum possible entropy over the combined vocabulary $V$:

$$H_{\max} = \log_2 |V|$$

$$\text{HD} = \frac{\Delta H}{H_{\max}}$$

**Edge cases:**
- Both sequences empty or single-token vocabulary: returns 0.0

**Interpretation:**
- **-1.0**: Corrupted text collapsed to a single repeated token
- **~-0.3**: Noticeably less diverse
- **0.0**: Same entropy level
- **~0.3**: Noticeably more diverse
- **1.0**: Maximum entropy increase

**Use case:** Detects whether corruption simplified or complexified the token distribution. Useful for catching degenerate outputs (repetitive text) or explosions in vocabulary.

---

### Merge-Split Index (MSI)

**Range:** `[0, 1]` where 0 = no restructuring, 1 = complete restructuring

**Purpose:** Estimates how much subword tokenization restructuring occurred—detecting when single tokens split into multiple (1→k) or multiple tokens merge into one (k→1).

**Mathematical definition:**

Using LCS to find preserved tokens:

$$\text{preserved} = \text{LCS}(A, B)$$

Tokens that changed in each sequence:

$$\text{changed}_A = |A| - \text{preserved}$$

$$\text{changed}_B = |B| - \text{preserved}$$

Merge/split events are estimated by the difference (since pure substitutions affect both equally):

$$\text{events} = |\text{changed}_A - \text{changed}_B|$$

The index normalizes by the maximum sequence length:

$$\text{MSI} = \frac{\text{events}}{\max(|A|, |B|)}$$

**Interpretation:**
- If $\text{changed}_A > \text{changed}_B$: merges occurred (multiple original tokens → fewer corrupted tokens)
- If $\text{changed}_B > \text{changed}_A$: splits occurred (original tokens → multiple corrupted tokens)
- If equal: substitutions only (no net restructuring)

**Edge cases:**
- Both empty: returns 0.0
- One empty: returns 1.0 (complete transformation)

**Interpretation examples:**
- **0.0**: Token count changes match perfectly (only substitutions)
- **0.2**: ~20% of positions involved restructuring
- **0.5**: Significant tokenization boundary changes
- **1.0**: Every token was restructured

**Use case:** Specifically targets subword tokenizer behavior. High MSI indicates the corruption is particularly disruptive to BPE/WordPiece tokenizers, even if the text looks similar to humans.

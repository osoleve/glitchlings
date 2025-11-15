# Glitchlings Metrics Framework

A comprehensive framework for analyzing text transformation effects across different tokenizers.

## Overview

The metrics framework provides tools to:

- **Measure** how glitchlings transform text across 14 metrics spanning edit distance, distribution, structure, and complexity
- **Compare** glitchling behavior across different tokenizers (GPT-2, BERT, tiktoken, etc.)
- **Visualize** transformation patterns through radar charts, heatmaps, embeddings, and sparklines
- **Scale** with batch processing and efficient Parquet storage

**Key Design Principles:**

- ✅ **Optional by Design**: Separate package that doesn't bloat core library
- ✅ **Correctness First**: All metrics validated against hand-computed ground truth
- ✅ **Reproducible**: Complete run manifests with vocabulary hashing
- ✅ **Extensible**: Protocol-based design for custom metrics and tokenizers

## Installation

```bash
# Core metrics only (numpy, pandas, scipy)
pip install glitchlings[metrics]

# Add the Textual-based TUI
pip install glitchlings[metrics,metrics-tui]

# Add tokenizer support (HuggingFace, tiktoken)
pip install glitchlings[metrics,metrics-tokenizers]

# Add visualization tools
pip install glitchlings[metrics,metrics-viz]

# Everything
pip install glitchlings[metrics,metrics-tokenizers,metrics-viz,metrics-tui]
```

## Quick Start

### 1. Compute Metrics for a Single Transformation

```python
from glitchlings.metrics.metrics import create_default_registry

# Create registry with all 14 metrics
registry = create_default_registry()

# Token sequences (before and after glitchling)
before = [1, 2, 3, 4, 5]
after = [1, 3, 2, 4, 5]  # transposition

# Compute all metrics
results = registry.compute_all(before, after, context={})

print(f"Edit Distance: {results['ned.value']:.3f}")
print(f"LCS Retention: {results['lcsr.value']:.3f}")
print(f"Reordering: {results['rord.value']:.3f}")
```

### 2. Batch Processing with Multiple Tokenizers

```python
from glitchlings.metrics.core.batch import process_and_write
from glitchlings.metrics.core.tokenizers import create_huggingface_adapter
from glitchlings.metrics.metrics import create_default_registry

# Prepare data
texts = [
    "The quick brown fox jumps over the lazy dog.",
    "Machine learning models process natural language.",
    # ... more texts
]

# Create tokenizer adapters
tokenizers = [
    create_huggingface_adapter("gpt2"),
    create_huggingface_adapter("bert-base-uncased"),
]

# Define glitchling function
def typogre(text):
    """Swap adjacent characters."""
    return text.replace("th", "ht")

# Process and save
registry = create_default_registry()
manifest = process_and_write(
    texts=texts,
    glitchling_fn=typogre,
    glitchling_id="typogre",
    registry=registry,
    tokenizers=tokenizers,
    output_dir="results/",
    partition_by=["tokenizer_id"],
)

print(f"Processed {manifest.num_observations} observations")
print(f"Run ID: {manifest.run_id}")
```

### 3. Explore Transformations Interactively (TUI)

Install the TUI dependencies and launch the Textual application:

```bash
pip install glitchlings[metrics,metrics-tui]

# Default SAMPLE_TEXT + Typogre fingerprint
python -m glitchlings.metrics.cli.tui

# Custom glitchling/tokenizers/input
python -m glitchlings.metrics.cli.tui \
    --glitchling "rushmore(mode='swap')" \
    --tokenizer simple \
    --tokenizer hf:gpt2 \
    --text "Glitch me, please!"

# Or via the main CLI:
glitchlings metrics-tui --text "Deterministic sample" --glitchling typogre --tokenizer simple

# You can repeat --glitchling/--tokenizer flags to build gaggles and multi-tokenizer comparisons.
```

Keybindings:

| Shortcut | Action |
| --- | --- |
| `r` | Recompute metrics for the current text/glitchling selections |
| `g` / `k` | Open the glitchling or tokenizer pickers |
| `/` | Focus the active filter/customization input field |
| `?` | Open the inline help + shortcut overlay |
| `Ctrl+S` | Show workflow tips for saving/exporting the current run |
| `Ctrl+←` / `Ctrl+→` | Cycle through the Output/Metrics/Diff tabs |
| `q` / `Esc` | Quit the TUI |

The TUI now launches with a lightweight walkthrough overlay that anchors tooltips to each section so first-time sessions highlight the intended workflow. You can always reopen `?` for shortcuts or press `Ctrl+S` to review how to persist a run via `process_and_write` and the batch APIs.

Use `--text-file path/to/file.txt` for longer corpora and repeat `--metric ned.value` style flags to customize the table columns.
Inside the UI you can toggle multiple built-in glitchlings/tokenizers via checkboxes and paste custom specs in the comma-separated fields to build arbitrary gaggles.

### 4. Visualize Results

```python
from glitchlings.metrics.viz import (
    create_radar_chart,
    create_heatmap,
    create_embedding_plot,
    load_observations_from_parquet,
)

# Load results
observations = load_observations_from_parquet(
    "results/metrics_run.parquet"
)

# Create transformation fingerprint (radar chart)
fig = create_radar_chart(
    observations,
    title="Typogre Transformation Profile",
    backend="plotly",
    output_path="figures/typogre_radar.html"
)

# Create heatmap showing metric across tokenizers
fig = create_heatmap(
    observations,
    metric="ned.value",
    row_key="glitchling_id",
    col_key="tokenizer_id",
    title="Edit Distance by Tokenizer",
    backend="matplotlib",
    output_path="figures/ned_heatmap.png"
)

# Explore metric space with UMAP
fig = create_embedding_plot(
    observations,
    method="umap",
    color_by="tokenizer_id",
    title="Metric Space Projection",
    backend="plotly",
    output_path="figures/umap.html"
)
```

### 4. Config-Driven Rendering

Create `viz_config.yaml`:

```yaml
figures:
  - type: radar
    title: "Glitchling Fingerprint"
    data_source: "results/metrics_run.parquet"
    filters:
      glitchling_id: "typogre"
    params:
      backend: "matplotlib"
      output_path: "figures/radar.png"

  - type: heatmap
    title: "Metrics Across Tokenizers"
    data_source: "results/metrics_run.parquet"
    params:
      metric: "ned.value"
      backend: "plotly"
      output_path: "figures/heatmap.html"
```

Render all figures:

```python
from glitchlings.metrics.viz import render_config_file

figures = render_config_file("viz_config.yaml")
# All figures saved to specified paths
```

## The 14 Core Metrics

### Edit & Overlap (3 metrics)

| Metric | ID | Description | Range |
|--------|-----|-------------|-------|
| **Normalized Edit Distance** | `ned.value` | Damerau-Levenshtein distance with transpositions | [0, 1] |
| **LCS Retention** | `lcsr.value` | Fraction of tokens preserved in order | [0, 1] |
| **Position Match Rate** | `pmr.value` | Fraction of LCS tokens at original positions | [0, 1] |

### Set-based (2 metrics)

| Metric | ID | Description | Range |
|--------|-----|-------------|-------|
| **Jaccard Set Distance** | `jsdset.value` | Set dissimilarity (unique tokens) | [0, 1] |
| **Jaccard Bag Distance** | `jsdbag.value` | Multiset dissimilarity (with counts) | [0, 1] |

### Distributional (3 metrics)

| Metric | ID | Description | Range |
|--------|-----|-------------|-------|
| **Cosine Distance** | `cosdist.value` | Angular distance of frequency vectors | [0, 1] |
| **JS Divergence** | `jsdiv.value` | Jensen-Shannon divergence of distributions | [0, 1] |
| **Entropy Delta** | `h_delta.value` | Change in Shannon entropy | [-∞, +∞] |

### Structural (4 metrics)

| Metric | ID | Description | Range |
|--------|-----|-------------|-------|
| **Reordering Score** | `rord.value` | Kendall-tau distance (order disruption) | [0, 1] |
| **Span Perturbation Index** | `spi.value` | Degree of span disruption | [0, 1] |
| **Merge-Split Index** | `msi.value` | Tokenizer boundary sensitivity | [0, 1] |
| **Boundary Hit Rate** | `bhr.value` | Fraction of original boundaries preserved | [0, 1] |

### Complexity & Length (2 metrics)

| Metric | ID | Description | Range |
|--------|-----|-------------|-------|
| **Compression Delta** | `c_delta.value` | Change in gzip compressibility | [-1, +∞] |
| **Length Ratio** | `lr.value` | Token sequence length ratio | [0, +∞] |

## Architecture

```
glitchlings.metrics/
├── core/
│   ├── align.py          # Damerau-Levenshtein, LCS, Kendall-tau
│   ├── schema.py         # Observation and Manifest data structures
│   ├── batch.py          # Batch processing and Parquet writing
│   └── tokenizers.py     # Tokenizer adapters (protocol-based)
├── metrics/
│   ├── registry.py       # Metric registration and dispatch
│   ├── edit.py           # NED, LCSR, PMR
│   ├── sets.py           # JSDset, JSDbag, LR
│   ├── distro.py         # COSdist, JSDiv, HΔ
│   ├── structure.py      # RORD, SPI, MSI, BHR
│   ├── complexity.py     # CΔ
│   └── defaults.py       # Pre-configured registry
└── viz/
    ├── aggregate.py      # Aggregation utilities
    ├── radar.py          # Transformation fingerprints
    ├── heatmap.py        # Metric grids
    ├── embed.py          # UMAP/t-SNE projections
    ├── spark.py          # Length sensitivity sparklines
    └── config.py         # Config-driven rendering
```

## Key Concepts

### Observation

An `Observation` captures one (text, glitchling, tokenizer) measurement:

```python
@dataclass
class Observation:
    run_id: str                    # Batch run identifier
    observation_id: str            # Unique observation ID
    input_id: str                  # Input text identifier
    glitchling_id: str            # Glitchling name
    tokenizer_id: str             # Tokenizer name
    tokens_before: Sequence[int]  # Token IDs before transformation
    tokens_after: Sequence[int]   # Token IDs after transformation
    m: int                        # Length before
    n: int                        # Length after
    metrics: dict[str, float]     # Computed metric values
    # ... metadata fields
```

### Run Manifest

A `RunManifest` records complete batch run metadata for reproducibility:

```python
@dataclass(frozen=True)
class RunManifest:
    run_id: str                        # Unique run identifier
    created_at: str                    # ISO timestamp
    config: Mapping[str, Any]          # Full configuration
    tokenizers: Sequence[str]          # Tokenizer IDs + vocab hashes
    metrics: Sequence[str]             # Metric IDs
    num_observations: int              # Total observations
    seed: int | None                   # Random seed (if used)
```

### Metric Registry

The registry manages metric computation with automatic dependency resolution:

```python
registry = MetricRegistry()

# Register a metric
@registry.register(
    metric_id="my_metric",
    name="My Custom Metric",
    semantics={"higher_is_better": False},
    norm={"min": 0.0, "max": 1.0},
    requires=[]  # Optional: depends on other metrics
)
def my_metric(before, after, context):
    return {"my_metric.value": compute_value(before, after)}

# Compute all registered metrics
results = registry.compute_all(before, after, context={})
```

### Tokenizer Adapter Protocol

Create custom tokenizer adapters by implementing the protocol:

```python
from glitchlings.metrics.core.tokenizers import TokenizerAdapter

class MyTokenizer:
    def encode(self, text: str) -> Sequence[int]:
        """Encode text to token IDs."""
        return [...]

    @property
    def name(self) -> str:
        """Tokenizer identifier."""
        return "my_tokenizer"

    @property
    def vocab_size(self) -> int:
        """Vocabulary size."""
        return 50000

    def vocab_hash(self) -> str:
        """SHA256 hash of vocabulary for reproducibility."""
        return hashlib.sha256(vocab_bytes).hexdigest()[:16]
```

## Visualization Gallery

### Radar Charts (Transformation Fingerprints)

Shows glitchling effects across all metrics simultaneously:

```python
create_radar_chart(
    glitchling_metrics,
    normalization="percentile",  # Compare to dataset distribution
    backend="plotly"             # Interactive hover
)
```

**Use Cases:**

- Compare glitchling aggressiveness
- Identify which metrics are most affected
- Profile transformation characteristics

### Heatmaps (Metric Grids)

Reveals tokenizer-specific sensitivities:

```python
create_heatmap(
    observations,
    metric="ned.value",
    row_key="glitchling_id",
    col_key="tokenizer_id",
    show_iqr=True  # Show uncertainty
)
```

**Use Cases:**

- Find which tokenizers are most sensitive
- Compare multiple glitchlings side-by-side
- Spot cross-cutting patterns

### Embeddings (Metric Space Projections)

Projects high-dimensional metric space to 2D using UMAP or t-SNE:

```python
create_embedding_plot(
    observations,
    method="umap",
    color_by="glitchling_id",
    metrics=["ned.value", "lcsr.value", "jsdiv.value"]  # Focus on subset
)
```

**Use Cases:**

- Discover natural glitchling clusters
- Identify outliers or unexpected behavior
- Compare different "metric lenses" (edit vs. distributional)

### Sparklines (Length Sensitivity)

Shows how metrics vary with input length:

```python
create_sparklines(
    observations,
    metrics=["ned.value", "lcsr.value"],
    group_by="glitchling_id",
    length_bins=10
)
```

**Use Cases:**

- Identify length-dependent effects
- Find optimal input length ranges
- Debug unexpected behavior at extreme lengths

## Best Practices

### Metric Selection

**For edit-heavy transformations** (insertions, deletions, swaps):

- Primary: `ned.value`, `lcsr.value`, `pmr.value`
- Secondary: `rord.value` (if reordering), `lr.value` (if length changes)

**For distributional shifts** (frequency changes without structure):

- Primary: `jsdiv.value`, `cosdist.value`, `h_delta.value`
- Secondary: `jsdset.value`, `jsdbag.value`

**For structural transformations** (span modifications, boundary changes):

- Primary: `rord.value`, `spi.value`, `msi.value`
- Secondary: `bhr.value` (if context provided)

**For compression/complexity** analysis:

- Primary: `c_delta.value`
- Interpretation: Positive = harder to compress (more random), negative = easier (more regular)

### Normalization

**Percentile normalization** (default for radar charts):

- Best for: Comparing within a dataset
- Interpretation: "What percentile does this observation fall in?"

**Min-max normalization**:

- Best for: Cross-dataset comparison
- Interpretation: "Where does this fall in the theoretical range?"

**Z-score normalization**:

- Best for: Identifying outliers
- Interpretation: "How many standard deviations from the mean?"

### Performance Tips

**For large datasets**:

1. Use `partition_by=["tokenizer_id"]` in batch processing
2. Filter observations before visualization: `filters={"glitchling_id": "subset"}`
3. Limit metrics in embeddings to most relevant subset
4. Use `length_bins` parameter to reduce sparkline resolution

**For accuracy**:

1. Use at least 20 diverse input texts per glitchling-tokenizer pair
2. Include inputs of varying lengths (short, medium, long)
3. Verify edge cases: empty strings, single tokens, very long sequences
4. Check acceptance tests pass: `pytest tests/metrics/test_acceptance.py`

### Reproducibility Checklist

✅ Save run manifest with results
✅ Record vocabulary hashes for all tokenizers
✅ Set random seed if using sampling
✅ Document glitchling implementations
✅ Version all dependencies in requirements
✅ Store raw Parquet files, not just visualizations

## Performance Characteristics

**Pure Python Implementation** (no native extensions):

- 100 tokens: <50ms per observation (all 14 metrics)
- 500 tokens: <500ms per observation
- 1000 tokens: <2000ms per observation

**Bottlenecks** (from profiling):

- `ned.value`: ~60% of total time (O(m×n) Damerau-Levenshtein)
- `lcsr.value`: ~20% of total time (O(m×n) LCS)
- Other metrics: ~20% combined

**Optimization Options** (future work):

- Use `python-Levenshtein` library for 10-100× NED speedup
- Cythonize hot loops in `align.py`
- Lazy evaluation: compute only requested metrics
- Parallelize batch processing with multiprocessing

## Extending the Framework

### Custom Metrics

```python
from glitchlings.metrics.metrics import MetricRegistry

registry = MetricRegistry()

@registry.register(
    metric_id="repetition_score",
    name="Token Repetition Score",
    semantics={"higher_is_better": False, "category": "complexity"},
    norm={"min": 0.0, "max": 1.0},
    requires=[]
)
def repetition_score(before, after, context):
    """Measure increase in token repetition."""
    def repetition_rate(tokens):
        if len(tokens) == 0:
            return 0.0
        unique = len(set(tokens))
        return 1.0 - (unique / len(tokens))

    before_rep = repetition_rate(before)
    after_rep = repetition_rate(after)

    return {
        "repetition_score.value": after_rep,
        "repetition_score.delta": after_rep - before_rep,
    }
```

### Custom Tokenizers

```python
from glitchlings.metrics.core.tokenizers import TokenizerAdapter
import hashlib

class CharacterTokenizer:
    """Simple character-level tokenizer."""

    def encode(self, text: str) -> list[int]:
        return [ord(c) for c in text]

    @property
    def name(self) -> str:
        return "char_tokenizer"

    @property
    def vocab_size(self) -> int:
        return 256  # ASCII

    def vocab_hash(self) -> str:
        vocab_str = "".join(chr(i) for i in range(256))
        return hashlib.sha256(vocab_str.encode()).hexdigest()[:16]

# Use in batch processing
tokenizer = CharacterTokenizer()
process_and_write(..., tokenizers=[tokenizer], ...)
```

### Custom Visualizations

```python
from glitchlings.metrics.viz.aggregate import pivot_for_heatmap
import matplotlib.pyplot as plt

def create_custom_plot(observations, metric):
    """Custom visualization using aggregation utilities."""
    data = pivot_for_heatmap(
        observations,
        row_key="glitchling_id",
        col_key="tokenizer_id",
        metric=metric,
        aggregation="median"
    )

    # Custom plotting logic
    fig, ax = plt.subplots()
    # ... your visualization code
    return fig
```

## Troubleshooting

### ImportError: No module named 'pandas'

**Solution**: Install metrics dependencies:

```bash
pip install glitchlings[metrics]
```

### ImportError: No module named 'umap'

**Solution**: Install visualization dependencies:

```bash
pip install glitchlings[metrics-viz]
```

### ImportError: No module named 'transformers'

**Solution**: Install tokenizer dependencies:

```bash
pip install glitchlings[metrics-tokenizers]
```

### ValueError: Metric matrix contains NaN values

**Cause**: Some observations missing required metrics or have invalid values.

**Solution**: Check that all observations have complete metric coverage:

```python
for obs in observations:
    for metric in required_metrics:
        if metric not in obs.metrics or not np.isfinite(obs.metrics[metric]):
            print(f"Invalid metric {metric} in {obs.observation_id}")
```

### Performance: Processing too slow

**Solutions**:

1. Reduce metrics computed: `registry.compute(["ned.value", "lcsr.value"], ...)`
2. Use shorter input texts for testing
3. Process in batches with progress tracking
4. Consider future optimizations (Cython, native libraries)

### Embeddings: "Need at least 2 observations"

**Cause**: After filtering, too few observations remain.

**Solution**: Relax filters or use more diverse input data:

```python
# Check observation count after filtering
filtered = [obs for obs in observations if obs.glitchling_id == "target"]
print(f"Observations: {len(filtered)}")  # Should be ≥2
```

## Further Reading

- **Planning Document**: `docs/metrics-framework-plan.md` - Complete implementation roadmap
- **Acceptance Tests**: `docs/metrics-acceptance-tests.md` - Hand-computed test specifications
- **API Reference**: Generated from docstrings with `mkdocs`
- **Example Notebook**: `examples/metrics_tutorial.ipynb` - Interactive walkthrough
- **Config Examples**: `examples/metrics_viz_config.yaml` - Visualization configurations

## License

Same as parent glitchlings library - see LICENSE file.

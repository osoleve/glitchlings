# Metrics Framework: Best Practices & Guidelines

This guide provides recommendations for using the glitchlings metrics framework effectively in research and production.

## Table of Contents

1. [Experimental Design](#experimental-design)
2. [Metric Selection](#metric-selection)
3. [Data Preparation](#data-preparation)
4. [Batch Processing](#batch-processing)
5. [Visualization](#visualization)
6. [Reproducibility](#reproducibility)
7. [Performance Optimization](#performance-optimization)
8. [Common Pitfalls](#common-pitfalls)

---

## Experimental Design

### Sample Size

**Minimum recommendations:**
- **Exploratory analysis**: 10-20 diverse texts per glitchling-tokenizer pair
- **Comparative studies**: 50-100 texts per condition
- **Production evaluation**: 200+ texts covering edge cases

**Rationale**: Statistical significance and confidence intervals improve with larger samples. The framework is designed for batch processing, so prefer larger datasets.

### Input Text Selection

**Diversity dimensions to consider:**
1. **Length**: Include short (5-20 tokens), medium (20-100 tokens), and long (100+ tokens) inputs
2. **Domain**: Mix technical, conversational, formal, and informal text
3. **Structure**: Simple sentences, complex sentences, lists, code, etc.
4. **Vocabulary**: Common words, rare words, numbers, punctuation

**Example stratified sampling:**
```python
texts = {
    "short_common": ["The cat sat.", "Hello world.", ...],
    "medium_technical": ["Machine learning models...", ...],
    "long_conversational": ["So I was thinking about...", ...],
}

# Flatten for processing
all_texts = [t for category in texts.values() for t in category]
```

### Control Conditions

**Always include:**
1. **Identity transformation**: `lambda x: x` (expect all metrics ≈ 0)
2. **Known transformations**: e.g., "reverse word order" (expect high `rord.value`)
3. **Baseline glitchlings**: Simple, well-understood transformations for comparison

---

## Metric Selection

### By Transformation Type

| Transformation | Primary Metrics | Secondary Metrics |
|----------------|----------------|-------------------|
| **Character-level edits** | `ned.value`, `lcsr.value` | `pmr.value`, `lr.value` |
| **Word reordering** | `rord.value`, `pmr.value` | `ned.value`, `spi.value` |
| **Insertions/deletions** | `ned.value`, `lr.value`, `lcsr.value` | `jsdbag.value` |
| **Substitutions** | `jsdset.value`, `jsdbag.value`, `ned.value` | `cosdist.value` |
| **Frequency changes** | `jsdiv.value`, `cosdist.value`, `h_delta.value` | `jsdbag.value` |
| **Span disruption** | `spi.value`, `msi.value` | `rord.value` |
| **Compression** | `c_delta.value` | `h_delta.value` |

### Metric Families

**Edit Distance Family** (structural similarity):
- Use when: Measuring how different token sequences are
- Metrics: `ned.value`, `lcsr.value`, `pmr.value`
- Interpretation: Higher values = more different

**Set-based Family** (compositional changes):
- Use when: Analyzing vocabulary changes
- Metrics: `jsdset.value`, `jsdbag.value`
- Interpretation: Ignores order, focuses on token presence/frequency

**Distributional Family** (statistical properties):
- Use when: Comparing probability distributions
- Metrics: `jsdiv.value`, `cosdist.value`, `h_delta.value`
- Interpretation: Captures frequency shifts

**Structural Family** (ordering and alignment):
- Use when: Analyzing reorganization
- Metrics: `rord.value`, `spi.value`, `msi.value`, `bhr.value`
- Interpretation: Measures how structure changed

### Correlation Analysis

**Check metric correlations** to avoid redundancy:

```python
from glitchlings.metrics.viz import load_observations_from_parquet
import pandas as pd

obs = load_observations_from_parquet("results.parquet")

# Extract metric matrix
metric_cols = [k for k in obs[0].metrics.keys() if ".value" in k]
data = {m: [o.metrics[m] for o in obs] for m in metric_cols}
df = pd.DataFrame(data)

# Compute correlation matrix
corr = df.corr()
print(corr)
```

**Rule of thumb**: If two metrics correlate > 0.9, consider using only one for visualizations.

---

## Data Preparation

### Input Text Quality

**Best practices:**
- ✅ Clean HTML/markup if present
- ✅ Normalize whitespace (or document if intentional)
- ✅ Handle special characters consistently
- ✅ Document any preprocessing steps

**Example:**
```python
def clean_text(text: str) -> str:
    """Standardize text for consistent tokenization."""
    # Remove extra whitespace
    text = " ".join(text.split())
    # Normalize quotes
    text = text.replace(""", '"').replace(""", '"')
    return text

texts = [clean_text(t) for t in raw_texts]
```

### Handling Edge Cases

**Test your glitchlings on:**
- Empty strings: `""`
- Single tokens: `"hello"`
- Punctuation-only: `"..."`
- Numbers: `"12345"`
- Mixed scripts: `"hello世界"`

**Example edge case tests:**
```python
edge_cases = [
    ("empty", ""),
    ("single", "x"),
    ("punct", "!!!"),
    ("numbers", "123"),
    ("long", "word" * 100),
]

for name, text in edge_cases:
    try:
        result = glitchling_fn(text)
        tokens_before = tokenizer.encode(text)
        tokens_after = tokenizer.encode(result)
        metrics = registry.compute_all(tokens_before, tokens_after, {})
        print(f"✓ {name}: {metrics['ned.value']:.3f}")
    except Exception as e:
        print(f"✗ {name}: {e}")
```

---

## Batch Processing

### Partitioning Strategy

**Choose partition keys based on query patterns:**

| Query Pattern | Recommended Partition |
|---------------|----------------------|
| "Compare tokenizers for one glitchling" | `partition_by=["glitchling_id"]` |
| "Compare glitchlings for one tokenizer" | `partition_by=["tokenizer_id"]` |
| "Analyze one glitchling-tokenizer pair" | `partition_by=["glitchling_id", "tokenizer_id"]` |
| "General exploration" | `partition_by=["tokenizer_id"]` (smaller files) |

**Example:**
```python
# For tokenizer comparison
manifest = process_and_write(
    texts=texts,
    glitchling_fn=my_glitchling,
    glitchling_id="my_glitch",
    registry=registry,
    tokenizers=[tok1, tok2, tok3],
    output_dir="results/",
    partition_by=["glitchling_id"],  # One file, easy to load
)

# For glitchling comparison
manifest = process_and_write(
    texts=texts,
    glitchling_fn=my_glitchling,
    glitchling_id="my_glitch",
    registry=registry,
    tokenizers=[tok1],
    output_dir="results/",
    partition_by=["tokenizer_id"],  # Separate tokenizer results
)
```

### Memory Management

**For very large datasets:**

1. **Process in chunks:**
```python
chunk_size = 100
for i in range(0, len(all_texts), chunk_size):
    chunk = all_texts[i:i+chunk_size]
    process_and_write(
        texts=chunk,
        glitchling_fn=glitchling,
        glitchling_id=f"batch_{i}",
        registry=registry,
        tokenizers=tokenizers,
        output_dir=output_dir,
    )
```

2. **Filter observations during loading:**
```python
# Load only specific glitchling
obs = load_observations_from_parquet(
    "results/data.parquet",
    filters={"glitchling_id": "target_glitch"}
)
```

---

## Visualization

### Choosing the Right Visualization

| Goal | Recommended Visualization |
|------|--------------------------|
| **Characterize one glitchling** | Radar chart (transformation fingerprint) |
| **Compare glitchlings** | Multi-glitchling radar, metric lens embedding |
| **Compare tokenizers** | Heatmap (glitchling × tokenizer grid) |
| **Find clusters** | UMAP/t-SNE embedding |
| **Understand length effects** | Sparklines, length sensitivity plot |
| **Show multiple metrics** | Multi-metric heatmap grid |

### Normalization Choice

**Percentile normalization** (default):
- **Use when**: Comparing within a fixed dataset
- **Interpretation**: "X% of observations have lower values"
- **Good for**: Radar charts, identifying outliers

**Min-max normalization**:
- **Use when**: Cross-dataset comparison
- **Interpretation**: "This is X% of the way from min to max"
- **Good for**: Comparing across experiments

**Z-score normalization**:
- **Use when**: Statistical analysis
- **Interpretation**: "This is X standard deviations from the mean"
- **Good for**: Identifying anomalies

**Example:**
```python
# For within-dataset comparison (radar chart)
create_radar_chart(
    metrics,
    normalization="percentile",  # Compare to distribution
)

# For cross-dataset comparison
create_radar_chart(
    metrics,
    normalization="minmax",  # Use theoretical bounds
    reference_stats=known_bounds,
)
```

### Color Schemes

**For categorical data** (glitchlings, tokenizers):
- Use qualitative color schemes: `tab10`, `Set3`
- Ensure sufficient contrast between categories

**For continuous data** (metric values):
- Use sequential schemes: `YlOrRd`, `Blues`, `Viridis`
- Consider colorblind-friendly palettes

### Annotation Guidelines

**Always include:**
- ✅ Descriptive title
- ✅ Axis labels with units
- ✅ Legend identifying all groups
- ✅ Data source (run_id) in caption

**Example:**
```python
fig = create_heatmap(
    observations,
    metric="ned.value",
    title="Normalized Edit Distance by Glitchling × Tokenizer",
    # Include metadata in filename
    output_path=f"figures/ned_heatmap_{run_id}.png"
)
```

---

## Reproducibility

### Complete Manifests

**Always save and version run manifests:**

```python
import json

manifest = process_and_write(...)

# Save manifest
with open(f"manifests/{manifest.run_id}.json", "w") as f:
    json.dump({
        "run_id": manifest.run_id,
        "created_at": manifest.created_at,
        "config": manifest.config,
        "tokenizers": manifest.tokenizers,
        "metrics": manifest.metrics,
        "num_observations": manifest.num_observations,
        "seed": manifest.seed,
    }, f, indent=2)
```

### Version Control

**Track in git:**
- Glitchling implementations
- Input text lists
- Configuration files
- Analysis scripts

**Do NOT track:**
- Large Parquet files (use git-lfs or separate storage)
- Generated figures (regenerate from config)

### Documentation Template

**For each experiment, document:**

```markdown
## Experiment: [Name]

**Date**: YYYY-MM-DD
**Run ID**: `abc123...`
**Goal**: [Brief description]

### Configuration
- Glitchlings: [list]
- Tokenizers: [list]
- Input texts: [source, count]
- Metrics: [list or "all 14"]

### Results
- Key findings: [summary]
- Visualizations: [list of figures]
- Unexpected behavior: [notes]

### Artifacts
- Parquet files: `results/abc123_*.parquet`
- Manifest: `manifests/abc123.json`
- Figures: `figures/abc123_*.png`
```

---

## Performance Optimization

### Metric Subset Selection

**For exploratory analysis**, compute only essential metrics:

```python
from glitchlings.metrics.metrics import MetricRegistry
from glitchlings.metrics.metrics.edit import ned, lcsr
from glitchlings.metrics.metrics.distro import jensen_shannon_divergence

# Custom registry with subset
registry = MetricRegistry()
registry.register_fn(ned)
registry.register_fn(lcsr)
registry.register_fn(jensen_shannon_divergence)

# ~3x faster than full 14-metric suite
```

### Tokenizer Caching

**Cache tokenized texts** if running multiple glitchlings:

```python
# Cache tokenization
tokenized_cache = {}
for text in texts:
    for tokenizer in tokenizers:
        key = (text, tokenizer.name)
        tokenized_cache[key] = tokenizer.encode(text)

# Use cached values in custom batch processing
```

### Parallel Processing

**For truly large datasets**, parallelize:

```python
from multiprocessing import Pool

def process_chunk(chunk_data):
    texts_chunk, glitchling_fn, tokenizers = chunk_data
    return process_and_write(
        texts=texts_chunk,
        glitchling_fn=glitchling_fn,
        tokenizers=tokenizers,
        # ... other params
    )

# Split work
chunks = [texts[i:i+100] for i in range(0, len(texts), 100)]
chunk_data = [(c, glitchling_fn, tokenizers) for c in chunks]

# Process in parallel
with Pool(4) as pool:
    manifests = pool.map(process_chunk, chunk_data)
```

---

## Common Pitfalls

### 1. **Empty Token Sequences**

**Problem**: Some tokenizers may produce empty sequences for certain inputs.

**Solution**: Check and filter:
```python
if len(tokens_before) == 0 or len(tokens_after) == 0:
    print(f"Warning: Empty tokens for '{text}'")
    continue  # Skip this observation
```

### 2. **Context Requirements**

**Problem**: Metric `bhr.value` requires `original_spans` in context, but it's not provided.

**Solution**: Either provide context or exclude the metric:
```python
# Option 1: Provide context
context = {"original_spans": [(0, 5), (6, 10)]}
results = registry.compute_all(before, after, context)

# Option 2: Use registry without BHR
registry = create_default_registry()
# BHR will return 0.0 if context missing
```

### 3. **Metric Interpretation**

**Problem**: Misinterpreting metric semantics (e.g., thinking higher is always better).

**Solution**: Check metric semantics:
```python
spec = registry.specs["ned"]
print(f"Higher is better: {spec.semantics.get('higher_is_better', None)}")
# ned: False (distance metrics - lower is better)
```

### 4. **Insufficient Sample Size**

**Problem**: Drawing conclusions from too few observations.

**Solution**: Report confidence intervals:
```python
agg = aggregate_observations(obs, group_by=["glitchling_id"])
for result in agg:
    ned_mean = result["metric_ned.value"]["mean"]
    ned_std = result["metric_ned.value"]["std"]
    n = result["count"]

    # 95% confidence interval
    ci = 1.96 * (ned_std / (n ** 0.5))
    print(f"{result['glitchling_id']}: {ned_mean:.3f} ± {ci:.3f}")
```

### 5. **Tokenizer Version Drift**

**Problem**: Results change when tokenizer library is updated.

**Solution**: Pin versions and use vocabulary hashing:
```python
# requirements.txt
transformers==4.35.0  # Pin exact version

# Check vocab hash
print(f"GPT-2 vocab hash: {tokenizer.vocab_hash()}")
# Compare to manifest to detect changes
```

### 6. **Visualization Overload**

**Problem**: Creating too many visualizations without clear purpose.

**Solution**: Define specific questions first:
```python
# Good: Targeted analysis
questions = [
    "Which tokenizer is most sensitive to typogre?",
    "Do edit metrics correlate with distributional metrics?",
    "Are effects length-dependent?",
]

# Then create visualizations to answer each question
```

---

## Summary Checklist

**Before running experiments:**
- [ ] Define clear research questions
- [ ] Select appropriate metrics for transformation type
- [ ] Prepare diverse, representative input texts
- [ ] Test glitchling on edge cases
- [ ] Choose tokenizers and pin versions

**During processing:**
- [ ] Use batch processing for efficiency
- [ ] Partition data appropriately
- [ ] Save run manifests
- [ ] Monitor for errors/warnings

**After processing:**
- [ ] Verify results with acceptance tests
- [ ] Check for unexpected patterns
- [ ] Compute confidence intervals
- [ ] Create targeted visualizations
- [ ] Document findings and artifacts

**For reproducibility:**
- [ ] Version control code and configs
- [ ] Save manifests with full configuration
- [ ] Record tokenizer vocabulary hashes
- [ ] Document any manual steps
- [ ] Archive Parquet files long-term

---

## Further Resources

- **Framework README**: `docs/metrics-framework-README.md`
- **API Documentation**: Generated from docstrings
- **Example Code**: `examples/metrics_complete_example.py`
- **Tutorial Notebook**: `examples/metrics_tutorial.ipynb`
- **Planning Document**: `docs/metrics-framework-plan.md`

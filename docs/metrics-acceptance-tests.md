# Metrics Framework - Acceptance Test Specification

**Purpose:** Ground truth validation for all metrics before production use

**Status:** Milestone 1 - Implementation Target

---

## Test Philosophy

Every metric must pass **hand-computed** validation on toy sequences before being used on real data. This document contains:

1. **Test sequences** (before/after token pairs)
2. **Expected outputs** for each metric (computed by hand)
3. **Invariants** that must hold universally
4. **Edge cases** to handle gracefully

---

## Notation

- `[a, b, c]` = token sequence (letters represent token IDs 0, 1, 2, ...)
- `m` = length of `before` sequence
- `n` = length of `after` sequence
- All distance metrics normalized to [0, 1] unless noted
- 1 = maximum difference, 0 = identity

---

## Test Case 1: Transposition

**Scenario:** Single adjacent swap

```
before: [a, b, c]  (IDs: [0, 1, 2])
after:  [a, c, b]  (IDs: [0, 2, 1])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **NED** | 0.333... (1/3) | One transposition, normalized by max(3,3)=3 |
| **LCSR** | 0.333... (1/3) | LCS([a,b,c],[a,c,b])=2 (a,c or a,b); change=1-2/3=1/3 |
| **PMR** | 0.666... (2/3) | Position 0: match (a), 1: mismatch, 2: mismatch; change=2/3 |
| **JSDset** | 0.0 | Same token set {a,b,c} ∪ {a,c,b} = {a,b,c}; J=3/3=1; dist=0 |
| **JSDbag** | 0.0 | Same multiset counts; J_m=1; dist=0 |
| **COSdist** | 0.0 | Same frequency vectors [1,1,1]; cos=1; dist=0 |
| **JSDiv** | 0.0 | Identical distributions P=Q=[1/3,1/3,1/3]; JSD=0 |
| **HΔ** | 0.0 | Same entropy (uniform distribution) |
| **RORD** | ~0.333 | Kendall-τ distance: 1 inversion out of (3 choose 2)=3 pairs; τ=1/3 |
| **SPI** | 0.333... (1/3) | One contiguous span of edits (positions 1-2); 1/3 |
| **MSI** | 0.0 | No merge/split events |
| **BHR** | N/A | No boundaries in token sequence |
| **LR** | 1.0 | n/m = 3/3 = 1.0 |
| **LRΔ** | 0.0 | |1 - 3/3| = 0 |

---

## Test Case 2: Identity

**Scenario:** No change

```
before: [a, a, a]  (IDs: [0, 0, 0])
after:  [a, a, a]  (IDs: [0, 0, 0])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **All distances** | 0.0 | Perfect identity |
| **LR** | 1.0 | n/m = 3/3 = 1.0 |
| **HΔ** | 0.0 | H(P) = H(Q) = 0 (single token, entropy=0) |

**Invariant Check:** All metrics should return 0 (no change) for identity sequences.

---

## Test Case 3: Single Insertion

**Scenario:** One token added at end

```
before: [a, b, c]     (IDs: [0, 1, 2])
after:  [a, b, c, d]  (IDs: [0, 1, 2, 3])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **NED** | 0.25 | One insertion; normalized by max(3,4)=4 |
| **LCSR** | 0.0 | LCS=3 (entire original); change=1-3/3=0 |
| **PMR** | 0.0 | All original positions match (alignment dependent) |
| **JSDset** | 0.25 | {a,b,c} vs {a,b,c,d}; J=3/4; dist=1-3/4=0.25 |
| **JSDbag** | 0.20 | min_counts=3, max_counts=4; J_m=3/4=0.75; dist=0.25 |
| **COSdist** | ~0.134 | P=[1,1,1], Q=[1,1,1,1]; cos≈0.866; dist≈0.134 |
| **JSDiv** | ~0.061 | P=[1/3,1/3,1/3,0], Q=[1/4,1/4,1/4,1/4]; compute KL |
| **HΔ** | +0.415 | ΔH = log(4) - log(3) ≈ 0.415 (more uniform) |
| **RORD** | 0.0 | Original order preserved for matched tokens |
| **SPI** | 0.25 | One span (the insertion); 1/4 |
| **LR** | 1.333... (4/3) | Expansion |
| **LRΔ** | 0.333... | |1 - 4/3| = 1/3 |

---

## Test Case 4: Single Deletion

**Scenario:** One token removed

```
before: [a, b, c, d]  (IDs: [0, 1, 2, 3])
after:  [a, b, c]     (IDs: [0, 1, 2])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **NED** | 0.25 | One deletion; normalized by max(4,3)=4 |
| **LCSR** | 0.25 | LCS=3; change=1-3/4=0.25 |
| **LR** | 0.75 | n/m = 3/4 = 0.75 |
| **LRΔ** | 0.25 | |1 - 3/4| = 0.25 |

---

## Test Case 5: Single Substitution

**Scenario:** One token replaced

```
before: [a, b, c]  (IDs: [0, 1, 2])
after:  [a, x, c]  (IDs: [0, 9, 2])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **NED** | 0.333... (1/3) | One substitution; 1/max(3,3) |
| **LCSR** | 0.333... | LCS=2 (a,c); change=1-2/3=1/3 |
| **PMR** | 0.333... | 2 matches, 1 mismatch; change=1/3 |
| **JSDset** | 0.25 | {a,b,c} vs {a,x,c}; intersection={a,c}, union={a,b,c,x}; J=2/4; dist=0.5 |
| **JSDbag** | 0.40 | min=2, max=5 (a:1+1, b:1+0, c:1+1, x:0+1); J_m=2/5; dist=3/5=0.6 |

**Note:** Substitutions create both lexical (set) and positional changes.

---

## Test Case 6: Complete Shuffle

**Scenario:** Maximal reordering

```
before: [a, b, c, d]  (IDs: [0, 1, 2, 3])
after:  [d, c, b, a]  (IDs: [3, 2, 1, 0])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **NED** | 0.5 | 2 adjacent transpositions minimum (or 2 swaps); 2/4 |
| **LCSR** | 0.75 | LCS=1 (any single token); change=1-1/4=0.75 |
| **JSDset** | 0.0 | Same set |
| **JSDbag** | 0.0 | Same bag |
| **RORD** | 1.0 | Perfect reversal; all (4 choose 2)=6 pairs inverted; τ=6/6=1.0 |
| **SPI** | 0.25 or 0.5 | Depends on edit path; likely 1-2 spans / 4 |

---

## Test Case 7: Subword Merge

**Scenario:** Two tokens become one (BPE/WordPiece behavior)

```
before: ["play", "##ing"]  (IDs: [42, 314])
after:  ["playing"]        (IDs: [1337])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **MSI** | 1.0 | One 2→1 merge event; 1/max(2,1)=1.0 |
| **NED** | 0.5 | Complex: depends on alignment heuristic |
| **LR** | 0.5 | n/m = 1/2 |

**Note:** This tests tokenizer-sensitivity metrics.

---

## Test Case 8: Subword Split

**Scenario:** One token becomes two

```
before: ["playing"]        (IDs: [1337])
after:  ["play", "##ing"]  (IDs: [42, 314])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **MSI** | 1.0 | One 1→2 split event; 1/max(1,2)=1.0 |
| **LR** | 2.0 | n/m = 2/1 |

---

## Test Case 9: Boundary Edit (Punctuation)

**Scenario:** Punctuation token changed

**Context:** Requires defining "boundary" tokens (whitespace, punct, special)

```
before: ["Hello", ",", "world"]  (IDs: [100, 5, 200])
after:  ["Hello", ".", "world"]  (IDs: [100, 6, 200])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **BHR** | 1.0 | 1 boundary edited, 1 boundary total (assuming comma is boundary); 1/1 |
| **NED** | 0.333... | One substitution; 1/3 |

---

## Test Case 10: Zero-Length Sequences

**Scenario:** Edge case handling

```
before: []
after:  []
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **NED** | 0.0 | No edits; 0/max(0,0) → define as 0 |
| **LR** | undefined | 0/0; should return NaN or 1.0 by convention |

**Invariant:** Metrics should handle empty inputs gracefully (no crashes).

---

```
before: []
after:  [a]
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **NED** | 1.0 | One insertion; 1/max(0,1)=1.0 |
| **LCSR** | 1.0 | LCS=0; change=1-0/0 → define as 1.0 |

---

## Test Case 11: Entropy Change (Uniformity)

**Scenario:** From concentrated to uniform distribution

```
before: [a, a, a, a, a, a, a, b]  (IDs: [0]*7 + [1])
after:  [a, b, c, d, e, f, g, h]  (IDs: [0,1,2,3,4,5,6,7])
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **HΔ** | +2.435 | H(before)=-(7/8·log(7/8) + 1/8·log(1/8)) ≈ 0.544 bits<br>H(after)=log(8)=3 bits<br>ΔH ≈ 2.456 |
| **JSDiv** | ~0.8 | Large distribution shift |

---

## Test Case 12: Compression Delta

**Scenario:** Introduce redundancy

```
before: [a, b, c, d, e, f, g, h]  (8 unique tokens)
after:  [a, a, a, a, a, a, a, a]  (1 unique token)
```

**Expected Results:**

| Metric | Expected Value | Reasoning |
|--------|---------------|-----------|
| **CΔ** | Negative | Compressed size of `after` < `before`; sequence is more compressible |
| **HΔ** | -3.0 | ΔH = 0 - log(8) = -3.0 (less uniform) |

**Note:** Exact CΔ depends on compression algorithm (gzip settings).

---

## Universal Invariants

These properties **must** hold for all test cases and all metrics:

### Invariant 1: Bounds

**All distance/change metrics ∈ [0, 1] after normalization.**

```python
assert 0.0 <= metric_value <= 1.0, f"{metric_name} out of bounds"
```

Exceptions:
- `LR` (length ratio): [0, ∞)
- `HΔ` (entropy delta): [-log|V|, +log|V|]
- `CΔ` (compression delta): can be negative

### Invariant 2: Identity

**All distance metrics = 0 when before == after.**

```python
assert metric(seq, seq) == 0.0, f"{metric_name} failed identity test"
```

### Invariant 3: Symmetry

**Distance metrics where applicable:**

- NED: symmetric (d(x,y) = d(y,x))
- LCSR: asymmetric (normalized by |before|)
- JSDset/JSDbag: symmetric
- COSdist: symmetric
- JSDiv: symmetric
- RORD: asymmetric (order matters)

```python
if metric.is_symmetric:
    assert metric(a, b) == metric(b, a)
```

### Invariant 4: Triangle Inequality

**For true metrics (NED, JSDiv, COSdist):**

```python
# d(x,z) ≤ d(x,y) + d(y,z)
assert metric(x, z) <= metric(x, y) + metric(y, z) + epsilon
```

### Invariant 5: Non-Negativity

**All distance metrics ≥ 0.**

```python
assert metric_value >= 0.0, f"{metric_name} is negative"
```

---

## Edge Cases to Handle

### 1. Empty Sequences

- **Input:** `before=[]`, `after=[]`
- **Expected:** Most metrics return 0.0 (identity)
- **LR:** Return 1.0 by convention (or NaN with warning)

### 2. One Empty, One Non-Empty

- **Input:** `before=[]`, `after=[a,b]`
- **Expected:** Maximum change (1.0 for normalized metrics)

### 3. Single-Token Sequences

- **Input:** `before=[a]`, `after=[a]`
- **Expected:** All metrics handle without division-by-zero

### 4. Very Long Sequences

- **Input:** 10,000-token sequences
- **Expected:** Compute in <1 second (performance test)
- **No:** Memory overflow or precision loss

### 5. High Duplication

- **Input:** `before=[a]*1000`
- **Expected:** RORD handles duplicate matching via stable tie-breaking

### 6. Zero Vocabulary Overlap

- **Input:** `before=[a,b,c]`, `after=[x,y,z]`
- **Expected:**
  - JSDset = 1.0 (no overlap)
  - JSDiv = 1.0 (maximal divergence)
  - NED likely 1.0 (all substitutions)

---

## Test Data Format

**Fixture File:** `tests/metrics/fixtures/toy_sequences.py`

```python
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class MetricTestCase:
    name: str
    before: Sequence[int]
    after: Sequence[int]
    expected: dict[str, float]  # metric_id -> expected_value
    tolerance: float = 1e-6
    notes: str = ""

TOY_SEQUENCES = [
    MetricTestCase(
        name="transposition",
        before=[0, 1, 2],
        after=[0, 2, 1],
        expected={
            "ned": 1/3,
            "lcsr_change": 1/3,
            "pmr_change": 2/3,
            "jsdset": 0.0,
            "jsdbag": 0.0,
            "cosdist": 0.0,
            "jsdiv": 0.0,
            "h_delta": 0.0,
            "rord": 1/3,
            "spi": 1/3,
            "msi": 0.0,
            "lr": 1.0,
            "lr_delta": 0.0,
        },
        notes="Single transposition: [a,b,c] → [a,c,b]"
    ),
    # ... more cases
]
```

---

## Acceptance Test Template

**File:** `tests/metrics/test_acceptance.py`

```python
import pytest
from glitchlings.metrics.fixtures.toy_sequences import TOY_SEQUENCES
from glitchlings.metrics import MetricRegistry

@pytest.fixture
def registry():
    return MetricRegistry()

@pytest.mark.parametrize("case", TOY_SEQUENCES, ids=lambda c: c.name)
def test_metric_acceptance(registry, case):
    """Validate all metrics against hand-computed ground truth."""
    results = registry.compute_all(
        before=case.before,
        after=case.after,
        context={}
    )

    for metric_id, expected in case.expected.items():
        # Handle nested metric names (e.g., "ned.value")
        actual = results.get(metric_id) or results.get(f"{metric_id}.value")

        assert actual is not None, f"Metric {metric_id} not computed"

        assert actual == pytest.approx(expected, abs=case.tolerance), (
            f"{case.name}: {metric_id} = {actual}, expected {expected}\n"
            f"Notes: {case.notes}"
        )

def test_invariant_identity(registry):
    """All distance metrics return 0 for identical sequences."""
    seq = [0, 1, 2, 3, 4]
    results = registry.compute_all(seq, seq, {})

    for metric_id, value in results.items():
        if "delta" in metric_id or "lr" in metric_id:
            continue  # Skip non-distance metrics

        assert value == pytest.approx(0.0, abs=1e-6), (
            f"Identity invariant failed: {metric_id} = {value}"
        )

def test_invariant_bounds(registry):
    """All normalized metrics stay in [0, 1]."""
    test_pairs = [
        ([0, 1, 2], [3, 4, 5]),  # Zero overlap
        ([0, 0, 0], [1, 1, 1]),  # Substitution
        ([0, 1], [1, 0]),        # Swap
    ]

    for before, after in test_pairs:
        results = registry.compute_all(before, after, {})

        for metric_id, value in results.items():
            # Skip unbounded metrics
            if metric_id in ("lr", "h_delta", "c_delta"):
                continue

            assert 0.0 <= value <= 1.0, (
                f"Bounds violation: {metric_id} = {value} for {before} → {after}"
            )
```

---

## Exit Criteria (Milestone 1)

✅ **All acceptance tests pass** with hand-computed values

✅ **All invariants hold** across test cases

✅ **Edge cases handled** (no crashes on empty/single-token sequences)

✅ **CI integration** (tests run on every commit)

✅ **Documentation** (this spec document + inline docstrings)

---

## Next Steps After Milestone 1

Once all acceptance tests are green:

1. ✅ Validate performance (<100ms for all metrics on 1k tokens)
2. ✅ Add property-based tests (hypothesis)
3. ✅ Benchmark against reference implementations
4. ✅ Document any deviations from textbook algorithms
5. ✅ Proceed to Milestone 2 (production implementations)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Status:** Ready for Implementation

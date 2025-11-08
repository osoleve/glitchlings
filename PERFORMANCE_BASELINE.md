# Performance Baseline & Optimization Tracking

## Targets (from checklist #1)

- **Speed Target**: ≥10× faster (≤1.5s end-to-end on 500k chars with typical operation mix)
- **Scaling Target**: Near-linear scaling (2× length ≈ ≤2.4× time)
- **Key Metrics**:
  - Total time for 500k char benchmark with typical ops
  - % time in tokenization
  - % time in `reindex()`
  - Allocations (MB)
  - Peak RSS (memory usage)

## Baseline Results (Before Optimizations)

### Environment
- Date: 2025-11-08
- Rust: 1.85+ (release mode with optimizations)
- Criterion: 0.5.1 with 10 samples, 1s warmup
- Build: Release mode (`cargo bench`)

### Benchmarks

#### 🎯 KEY METRIC: 500k Mixed Operations
- **Current: 11.77 seconds**
- **Target: ≤1.5 seconds**
- **Required speedup: 7.8× minimum (goal: ≥10×)**

#### Tokenization (TextBuffer creation from string)
- ~15k chars: 170 µs (88 Melem/s)
- ~75k chars: 3.4 ms (22 Melem/s)
- ~150k chars: 6.0 ms (25 Melem/s)
- ~754k chars: 24 ms (31 Melem/s)

**Observation**: Tokenization is FAST and roughly O(n) linear.

#### Pipeline Typical (Reduplicate 5% + Delete 3% + Swap 4%)
- ~15k chars: 4.7 ms (3.2 Melem/s)
- ~75k chars: 115 ms (653 Kelem/s)
- ~150k chars: 426 ms (354 Kelem/s)
- ~754k chars: ~11-12 seconds

**Observation**: Pipeline is 25-500× slower than tokenization! Most time spent in reindex.

#### Scaling Test (377k vs 754k = ~2× size)
- 377k chars: 2.67 seconds
- 754k chars: 12.14 seconds
- **Scaling ratio: 4.55× (vs target: ≤2.4×)**

**🔴 CRITICAL**: This confirms O(n²) or worse behavior from repeated reindexing!

## Profiling Analysis

### Flamegraph Insights
(To be filled after running with pprof)

### Time Breakdown (estimated from code analysis)
- Tokenization: ~X%
- Reindex operations: ~Y%
- Actual glitch operations: ~Z%

## Optimization Progress

| Optimization | Status | Before | After | Improvement |
|--------------|--------|--------|-------|-------------|
| #3: Eliminate per-edit reindexing | Not started | - | - | - |
| #4: Bulk mutation APIs | Not started | - | - | - |
| #5: Refactor GlitchOps to batch | Not started | - | - | - |
| #6: Make reindex() cheap | Not started | - | - | - |
| #7: Kill whole-buffer rebuilds | Not started | - | - | - |
| #8: Zero-copy tokenization | Not started | - | - | - |
| #9: Tokenizer hot path hygiene | Not started | - | - | - |

## Notes

### Current Known Bottlenecks
1. **Reindex called after every mutation** - O(n) per operation
2. **Character counting in reindex** - Calls `.chars().count()` per segment
3. **No bulk mutation APIs** - Each word change triggers reindex
4. **Weighted sampling** - O(k²) for k selected items

### Next Steps
1. Run baseline benchmarks
2. Analyze flamegraphs
3. Implement deferred reindexing (mutation scope)
4. Add bulk mutation APIs
5. Refactor operations to use batching

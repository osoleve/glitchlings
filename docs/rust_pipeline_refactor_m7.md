# Glitchlings Rust Pipeline Refactor — Milestone 7

Milestone 7 focuses on test hardening and benchmarking so the Rust pipeline can ship
with confidence.

## Expanded Test Coverage
- Added parity-focused unit tests for each glitch operation to assert their
  deterministic outputs against known Python results for representative seeds.
- Extended the pipeline unit tests with a composed descriptor scenario that
  matches a pre-recorded Python sequence, ensuring end-to-end determinism from
  seed derivation through mutation application.
- Enriched the Python regression suite with deterministic and error-propagation
  checks for `compose_glitchlings`, verifying that the Rust executor produces
  stable outputs across runs and raises the same `ValueError` semantics when an
  operation fails.

## Benchmark Harness
- Introduced `benchmarks/pipeline_benchmark.py`, a lightweight script that
  times the consolidated Rust pipeline against the existing Python orchestrator
  across short, medium, and long texts while reusing the shared descriptor
  fixtures.
- The script stubs optional dependencies (`datasets`) so it can run in minimal
  environments and automatically skips Rust timings when the extension is not
  available.

### Sample Results (Linux, Python 3.12, release build)
```
Text size: short (28 chars)
  Python pipeline :   0.202 ms (σ=0.231 ms)
  Rust pipeline   :   0.640 ms (σ=0.525 ms)

Text size: medium (231 chars)
  Python pipeline :   0.400 ms (σ=0.052 ms)
  Rust pipeline   :   0.763 ms (σ=0.072 ms)

Text size: long (927 chars)
  Python pipeline :   1.167 ms (σ=0.075 ms)
  Rust pipeline   :   1.985 ms (σ=0.069 ms)
```

These measurements were captured with `benchmarks/pipeline_benchmark.py --iterations 50`
after compiling the Rust extension in release mode and copying the resulting shared
library next to the Python package for import.

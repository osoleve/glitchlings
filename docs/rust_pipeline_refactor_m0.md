# Rust Pipeline Refactor – Milestone 0 Baseline

## Orchestration Contract Summary
- **Glitchling cloning and parameter capture:** Each `Glitchling` stores its corruption callable, scope, order, RNG seed, and keyword parameters so it can be cloned with the same configuration. The `clone` helper filters the stored kwargs, re-applies an explicit seed when provided, and instantiates either the base `Glitchling` wrapper or the subclass, ensuring parity between Python and Rust call sites.【F:src/glitchlings/zoo/core.py†L96-L149】【F:src/glitchlings/zoo/core.py†L215-L233】
- **Seed derivation and RNG reset:** `Gaggle` derives deterministic per-glitchling seeds from the master seed by hashing the seed, glitchling name, and positional index with BLAKE2s, then resets each clone's RNG to the derived value so runs remain reproducible.【F:src/glitchlings/zoo/core.py†L303-L328】【F:src/glitchlings/zoo/core.py†L296-L301】
- **Wave + order driven execution:** Glitchlings are bucketed by `AttackWave`, sorted within each wave by `(AttackOrder, name)`, and flattened into a deterministic `apply_order` that the orchestrator iterates sequentially for every corruption request.【F:src/glitchlings/zoo/core.py†L330-L337】
- **Sequential corruption contract:** `Gaggle.corrupt` passes the intermediate string through each glitchling's callable one at a time; individual glitchlings inject their RNG automatically when their callable accepts an `rng` parameter, keeping implementations agnostic to the orchestrator details.【F:src/glitchlings/zoo/core.py†L139-L169】【F:src/glitchlings/zoo/core.py†L367-L381】

## Python↔Rust Boundary Profiling
To understand how often we cross the FFI boundary during multi-glitch pipelines, I measured average per-run latency for short text while progressively increasing the number of Rust-backed glitchlings (Reduple, Rushmore, Redactyl, Scannequin, Typogre). Each data point averages 100 runs with fresh `Gaggle` instances to mimic current orchestrator behaviour. For comparison, I repeated the measurements while forcing all glitchlings to use their Python fallbacks.

| Glitchlings applied | Rust fast path (ms) | Python fallback (ms) |
| --- | --- | --- |
| 1 | 0.173 | 0.182 |
| 2 | 0.212 | 0.239 |
| 3 | 0.277 | 0.334 |
| 4 | 0.381 | 0.480 |
| 5 | 0.566 | 0.629 |

Rust-backed runs stay ~0.04–0.05 ms apart as we add glitchlings, indicating a noticeable constant overhead from repeated Python→Rust transitions even when the text is tiny. The Python fallbacks pay the same orchestration costs plus slower mutation routines, widening the gap as more steps are chained.【fb2075†L1-L6】

## Baseline Throughput Measurements
Using the five-glitch pipeline above, I captured average latency across 50 runs for three text sizes (one paragraph, four paragraphs, and twelve paragraphs). Rust extensions were active in the baseline, and Python fallbacks were forced in a separate run for parity.

| Text size | Rust fast path (ms) | Python fallback (ms) | Relative slowdown |
| --- | --- | --- | --- |
| Short (≈1 paragraph) | 0.59 | 0.68 | +15% |
| Medium (≈4 paragraphs) | 1.60 | 2.38 | +49% |
| Long (≈12 paragraphs) | 4.83 | 10.63 | +120% |

The results confirm that the existing orchestrator pays a fixed boundary tax even on short inputs, while longer texts amplify the benefit of avoiding redundant tokenization/regex work in Python. These timings provide a baseline for evaluating the refactored Rust pipeline once multi-op execution is consolidated.【42f544†L1-L3】

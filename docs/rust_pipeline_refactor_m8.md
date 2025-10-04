# Glitchlings Rust Pipeline Refactor — Milestone 8

Milestone 8 wraps up the refactor by documenting the orchestration
contract, adding guardrails for opt-in rollout, and ensuring safe
fallback paths remain intact.

## Documentation Refresh
- Captured the final orchestration contract, including how `Gaggle`
  derives per-glitchling seeds, builds pipeline descriptors, and gates
  Rust execution behind a feature flag.【F:src/glitchlings/zoo/core.py†L303-L381】
- Documented the environment variable toggle so operators know how to
  enable the Rust pipeline only after validating it in their own
  deployments.【F:README.md†L61-L71】

## Guardrails & Feature Flag
- Introduced the `GLITCHLINGS_RUST_PIPELINE` environment variable; when
  set to a truthy value (`1`, `true`, `yes`, or `on`), `Gaggle`
  leverages the Rust pipeline whenever the compiled extension is
  available.【F:src/glitchlings/zoo/core.py†L25-L36】【F:src/glitchlings/zoo/core.py†L339-L365】
- Exposed `Gaggle.rust_pipeline_supported()` and
  `Gaggle.rust_pipeline_enabled()` helpers so callers can check
  capabilities programmatically before opting in.【F:src/glitchlings/zoo/core.py†L339-L365】
- Added regression tests ensuring the feature flag disables the pipeline
  and that the orchestrator falls back to the Python loop whenever the
  flag is unset or resources are missing.【F:tests/test_rust_backed_glitchlings.py†L213-L295】

With these guardrails in place, consumers can adopt the new pipeline on
their own schedule while preserving deterministic behaviour whether or
not the Rust extension is present.

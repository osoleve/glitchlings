# Technical Debt Reduction Journal

## Completed Steps

- Centralised bundled resources under `src/glitchlings/zoo/assets` with helper loaders so that Python and Rust pipelines consume the same canonical copies for OCR confusions, Apostrofae pairs, and Hokey stretchability data.
- Added integrity checks in the pytest suite to guarantee staged Rust assets stay synchronised with the canonical Python sources and to catch regressions when legacy locations linger.
- Streamlined the Hokey stretchability loader in Python to rely on the shared asset helpers, removing ad-hoc file access logic and normalising data ingestion across pipelines.
- Tightened the Rust build process to stage assets exclusively from the canonical shared directory, preventing drift from deprecated resource paths.
- Introduced a shared `load_json` helper in the asset module and migrated Apostrofae and the Hokey stretchability pipeline to use it, eliminating bespoke JSON parsing paths in the Python codebase.
- Added a `python -m glitchlings.dev.sync_assets` helper plus a pytest guard to keep the vendored Rust asset bundle aligned with the canonical sources and surface divergence during CI runs.
- Introduced cryptographic hash checks in the asset integrity tests so staged resources surface corruption or partial updates immediately.

## Observations

- Maintaining parity between Python package data and the Rust crate still requires a vendored copy under `rust/zoo/assets/` for release builds; automated synchronisation would reduce the risk of stale files when packaging outside the monorepo.
- Ancillary tooling such as cache builders still dip into JSON files directly; migrating them onto the shared helpers will fully retire bespoke loaders.
- Asset integrity tests currently focus on text resources; binary assets (if introduced later) will need additional coverage to ensure checksums remain aligned.

## Next Steps

1. Continue auditing modules in `glitchlings.util` and `glitchlings.zoo` (along with ancillary tooling like cache builders) to ensure every bundled resource goes through the asset helpers, expanding the new JSON loader to cover any remaining bespoke file access.
2. Document the shared asset workflow in the contributor guide so future changes follow the canonical structure by default.
3. Generate an asset manifest (e.g., the new digests) during release packaging so downstream consumers can verify bundled resources without running the test suite.

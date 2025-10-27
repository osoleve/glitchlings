# Technical Debt Reduction Journal

## Completed Steps

- Centralised bundled resources under `src/glitchlings/zoo/assets` with helper loaders so that Python and Rust pipelines consume the same canonical copies for OCR confusions, Apostrofae pairs, and Hokey stretchability data.
- Added integrity checks in the pytest suite to guarantee staged Rust assets stay synchronised with the canonical Python sources and to catch regressions when legacy locations linger.
- Streamlined the Hokey stretchability loader in Python to rely on the shared asset helpers, removing ad-hoc file access logic and normalising data ingestion across pipelines.
- Tightened the Rust build process to stage assets exclusively from the canonical shared directory, preventing drift from deprecated resource paths.

## Observations

- Maintaining parity between Python package data and the Rust crate still requires a vendored copy under `rust/zoo/assets/` for release builds; automated synchronisation would reduce the risk of stale files when packaging outside the monorepo.
- Several legacy helpers in `glitchlings.util` still contain bespoke JSON loading code that predates the shared asset module and may benefit from consolidation.
- Asset integrity tests currently focus on text resources; binary assets (if introduced later) will need additional coverage to ensure checksums remain aligned.

## Next Steps

1. Introduce a lightweight sync command (e.g., `python -m glitchlings.dev.sync_assets`) that updates vendored Rust assets from the canonical directory and integrates with CI to flag divergence before publishing.
2. Audit remaining modules in `glitchlings.util` and `glitchlings.zoo` for filesystem access patterns and migrate them onto the shared loader abstractions where possible.
3. Expand the asset integrity tests to compute cryptographic hashes for each staged resource, giving us a quick way to detect silent corruption or partial updates.
4. Document the shared asset workflow in the contributor guide so future changes follow the canonical structure by default.

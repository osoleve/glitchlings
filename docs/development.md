# Glitchlings development setup

This guide walks through preparing a local development environment, running the automated checks, and exercising the optional Rust acceleration layer.

## Prerequisites

- Python 3.10+
- `pip` and a virtual environment tool of your choice (the examples below use `python -m venv`)
- [Optional] A Rust toolchain (`rustup` or system packages) and [`maturin`](https://www.maturin.rs/) for compiling the PyO3 extensions

## Install the project

1. Clone the repository and create an isolated environment:

   ```bash
   git clone https://github.com/osoleve/glitchlings.git
   cd glitchlings
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the package in editable mode with the development dependencies:

   ```bash
   pip install -e .[dev]
   ```

   Add the `prime` extra (`pip install -e .[dev,prime]`) when you need the Prime Intellect integration and its `verifiers` dependency.

3. If you plan to use the Jargoyle glitchling, download the WordNet corpus once per machine:

   ```bash
   python -m nltk.downloader wordnet
   ```

## Run the test suite

Execute the automated tests from the repository root:

```bash
pytest
```

The suite covers determinism guarantees, dataset integrations, and parity between Python and Rust implementations. When the WordNet corpus is unavailable, the Jargoyle-specific tests skip automatically.

## Optional Rust acceleration

Glitchlings ships PyO3 extensions that accelerate Typogre, Mim1c, Reduple, Rushmore, Redactyl, and Scannequin. Compile them with `maturin` and toggle the feature flag to exercise the new Rust pipeline:

```bash
# Compile the shared Rust crate (rerun after Rust or Python updates)
maturin develop -m rust/zoo/Cargo.toml

# Enable the fast path before importing glitchlings
export GLITCHLINGS_RUST_PIPELINE=1
```

Unset the environment variable (or set it to `0`/`false`) to fall back to the pure-Python orchestrator. The test suite automatically covers both code paths—re-run `pytest` with and without the flag to verify new changes across implementations.

## Additional tips

- Rebuild the Rust extension after editing files under `rust/zoo/`:

  ```bash
  maturin develop -m rust/zoo/Cargo.toml
  ```

- Use `python -m glitchlings --help` to smoke-test CLI changes quickly.
- Check `docs/index.md` for end-user guidance—keep it in sync with behaviour changes when you ship new glitchlings or orchestration features.
- When a TestPyPI publish fails, sync `dev` with `trunk` and recreate the release tag to trigger the workflow again. A helper script lives at `scripts/retry_testpypi_release.sh`—pass it the tag name (`./scripts/retry_testpypi_release.sh v1.2.3`) to fast-forward `dev`, delete and recreate the tag, and push both updates.

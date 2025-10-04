# Development setup

This guide walks through the exact steps required to hack on Glitchlings with
the Rust acceleration crates enabled and the full test suite running without
skips.

## Prerequisites

- Python 3.12 (matches the version used by the PyO3 bindings)
- A recent Rust toolchain with `cargo`
- [`maturin`](https://www.maturin.rs/) for building the extension module

## Create an isolated environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## Install Glitchlings in editable mode

Install the package with its development extras so linting, testing, and
documentation tools are available:

```bash
pip install -e '.[dev]'
```

## Compile the PyO3 extension

Use `maturin develop` to build the Rust pipeline crate against the same Python
version you are using in the virtual environment. Explicitly set
`PYO3_PYTHON=/usr/bin/python3.12` so the build script discovers the correct
interpreter headers and libraries:

```bash
pip install maturin
PYO3_PYTHON=/usr/bin/python3.12 maturin develop --release -m rust/zoo/Cargo.toml
```

## Run the Rust unit tests

Verify the compiled crate with `cargo test` before exercising the Python
bindings:

```bash
PYO3_PYTHON=/usr/bin/python3.12 cargo test --manifest-path rust/zoo/Cargo.toml
```

## Execute the Python test suite without skips

Enable skip reporting (`-rs`) so you can confirm the Rust-backed cases run with
the freshly compiled extension:

```bash
PYTHONPATH=src .venv/bin/pytest -rs
```

If you see skips mentioning WordNet, install the corpus and rerun the suite:

```bash
python -c "import nltk; nltk.download('wordnet')"
```

## Recap

Following the steps above keeps the Rust parity tests active and ensures
contributors see the same deterministic behaviour the documentation describes.

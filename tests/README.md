# Glitchlings Test Suite

This directory contains the test suite for the Glitchlings library.

## Structure

```
tests/
├── fixtures/           # Shared test fixtures
│   ├── glitchlings.py # Glitchling factory fixtures
│   ├── mocks.py       # Mock modules for optional dependencies
│   └── lexicon.py     # Lexicon test utilities
├── helpers/           # Test helper functions
│   ├── assertions.py  # Reusable assertion helpers
│   └── cli.py        # CLI testing utilities
├── data/             # Shared test data
│   └── samples.py    # Canonical test samples
├── core/             # Core glitchling tests
├── dlc/              # DLC integration tests
├── lexicon/          # Lexicon backend tests
├── integration/      # Integration tests
├── rust/             # Rust extension tests
├── cli/              # CLI tests
├── util/             # Utility function tests
├── conftest.py       # Root pytest configuration
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run by Category
```bash
# Core tests
pytest tests/core/ -v

# DLC tests
pytest tests/dlc/ -v

# Lexicon tests
pytest tests/lexicon/ -v

# Integration tests
pytest tests/integration/ -v
```

### Run by Marker
```bash
# Fast tests only (exclude slow tests)
pytest -m "not slow" -v

# Unit tests only
pytest -m "unit" -v

# Integration tests
pytest -m "integration" -v

# Tests that don't require optional dependencies
pytest -m "not requires_torch and not requires_datasets" -v
```

### With Coverage
```bash
pytest tests/ --cov=glitchlings --cov-report=html
```

## Available Markers

- `slow` - Tests that take more than 1 second
- `integration` - Integration tests requiring multiple components
- `requires_rust` - Tests requiring compiled Rust extension
- `requires_datasets` - Tests requiring Hugging Face datasets package
- `requires_torch` - Tests requiring PyTorch
- `requires_vectors` - Tests requiring vector lexicon dependencies
- `unit` - Unit tests (default)

## Writing Tests

### Using Fixtures

#### Glitchling Factory Fixture
```python
def test_something(fresh_glitchling):
    """Use the factory fixture to get any glitchling."""
    glitch = fresh_glitchling("typogre")
    glitch.set_param("rate", 0.1)
    result = glitch("test text")
    assert result != "test text"
```

#### Sample Text
```python
def test_something(sample_text):
    """Use the canonical sample text."""
    from glitchlings import typogre
    result = typogre(sample_text)
    assert len(result) > 0
```

### Using Assertion Helpers

```python
from tests.helpers.assertions import assert_deterministic

def test_determinism(fresh_glitchling, sample_text):
    """Test deterministic behavior."""
    glitch = fresh_glitchling("typogre")
    glitch.set_param("rate", 0.05)
    assert_deterministic(glitch, sample_text, seed=42)
```

### Using Test Data

```python
from tests.data.samples import SAMPLE_COLORS, SAMPLE_MULTILINE

def test_something():
    """Use centralized test data."""
    from glitchlings import typogre
    result = typogre(SAMPLE_COLORS)
    assert result != SAMPLE_COLORS
```

### Using Mocks

```python
def test_with_torch(torch_stub):
    """Test with mocked PyTorch."""
    DataLoader = torch_stub
    dataset = [1, 2, 3]
    loader = DataLoader(dataset)
    assert list(loader) == dataset
```

## Test Patterns

### Determinism Testing
```python
from tests.helpers.assertions import assert_deterministic

def test_glitchling_determinism(fresh_glitchling, sample_text):
    glitch = fresh_glitchling("typogre")
    glitch.set_param("rate", 0.05)
    assert_deterministic(glitch, sample_text, seed=42)
```

### Rate Parameter Testing
```python
def test_rate_bounds(fresh_glitchling, sample_text):
    glitch = fresh_glitchling("typogre")
    glitch.set_param("rate", 0.1)
    glitch.set_param("seed", 42)

    result = glitch(sample_text)
    # Add specific assertions about rate behavior
```

### CLI Testing
```python
from tests.helpers.cli import invoke_cli

def test_cli_command():
    code, stdout, stderr = invoke_cli(["--help"])
    assert "usage:" in stdout.lower()
```

## Best Practices

1. **Use Factory Fixtures**: Prefer `fresh_glitchling("name")` over individual fixtures
2. **Use Assertion Helpers**: Import from `tests.helpers.assertions` for common patterns
3. **Use Centralized Data**: Import from `tests.data.samples` instead of defining inline
4. **Add Markers**: Mark tests with appropriate markers for categorization
5. **Document Tests**: Add clear docstrings explaining what each test validates
6. **Avoid Duplication**: Reuse fixtures and helpers instead of duplicating logic

## Backward Compatibility

Legacy individual glitchling fixtures are still available but deprecated:
- `typogre_instance` → Use `fresh_glitchling("typogre")` instead
- `mim1c_instance` → Use `fresh_glitchling("mim1c")` instead
- etc.

## Migration Guide

If you're updating existing tests:

1. Replace individual glitchling fixtures with `fresh_glitchling`
2. Replace inline assertion logic with helpers from `tests.helpers.assertions`
3. Replace inline test data with imports from `tests.data.samples`
4. Add appropriate markers to test files
5. Update imports to use centralized fixtures


## Contributing

When adding new tests:

1. Follow existing patterns in refactored test files
2. Use shared fixtures and helpers where applicable
3. Add new reusable helpers to `tests/helpers/` if creating common patterns
4. Add new test data to `tests/data/samples.py` if defining reusable samples
5. Mark tests appropriately based on their requirements
6. Document test purpose clearly in docstrings


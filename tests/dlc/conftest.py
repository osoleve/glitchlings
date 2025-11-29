"""DLC (Downloadable Content) test configuration.

This module provides DLC-specific fixtures for testing integrations with
PyTorch, Hugging Face Datasets, and other optional dependencies.
"""

from __future__ import annotations

# Import shared mocks and fixtures from the centralized location
# torch_stub, verifiers classes are now in tests.fixtures.mocks
from tests.fixtures.mocks import (
    _load_environment,
    _Rubric,
    _SingleTurnEnv,
    _VerifierEnvironment,
    torch_stub,
)

# Re-export for backward compatibility with existing tests
__all__ = [
    "torch_stub",
    "_Rubric",
    "_SingleTurnEnv",
    "_VerifierEnvironment",
    "_load_environment",
]

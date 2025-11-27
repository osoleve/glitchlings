"""Compatibility helpers centralising optional dependency imports and extras.

This module provides lazy loading and availability checking for optional
dependencies. It re-exports from internal submodules for backward compatibility.

Architecture:
- compat/types.py - Pure type definitions (no side effects)
- compat/loaders.py - Impure lazy loading machinery
- compat/__init__.py - Re-exports for backward compatibility

Typical usage:
    from glitchlings.compat import require_datasets, datasets

    # Check availability without raising
    if datasets.available():
        ds = datasets.load()

    # Or require with custom error message
    ds_module = require_datasets("Install 'datasets' to use this feature")
"""

from __future__ import annotations

# Re-export everything from loaders for backward compatibility
from .loaders import (
    OptionalDependency,
    datasets,
    get_datasets_dataset,
    get_installed_extras,
    get_pytorch_lightning_datamodule,
    get_torch_dataloader,
    jellyfish,
    jsonschema,
    pytorch_lightning,
    require_datasets,
    require_jellyfish,
    require_pytorch_lightning,
    require_torch,
    require_verifiers,
    reset_optional_dependencies,
    torch,
    verifiers,
)

# Re-export types for anyone who needs the sentinel
from .types import MISSING, _MissingSentinel

__all__ = [
    # Types
    "MISSING",
    "_MissingSentinel",
    # Core class
    "OptionalDependency",
    # Global instances
    "datasets",
    "verifiers",
    "jellyfish",
    "jsonschema",
    "pytorch_lightning",
    "torch",
    # Accessors
    "get_datasets_dataset",
    "require_datasets",
    "get_pytorch_lightning_datamodule",
    "require_pytorch_lightning",
    "require_verifiers",
    "require_jellyfish",
    "require_torch",
    "get_torch_dataloader",
    # Utilities
    "reset_optional_dependencies",
    "get_installed_extras",
]

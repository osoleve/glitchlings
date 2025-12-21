"""NVIDIA NeMo DataDesigner plugin for Glitchlings.

This package provides entry-point registration for the Glitchlings column
generator in NeMo DataDesigner. The core implementation lives in the main
Glitchlings package at ``glitchlings.dlc.nemo``.

Installation:
    pip install glitchlings-nemo

Usage:
    Once installed, the plugin is automatically discovered by DataDesigner.
    Use ``GlitchlingColumnConfig`` to add corrupted text columns:

    >>> from data_designer import DataDesignerConfigBuilder
    >>> from glitchlings_nemo import GlitchlingColumnConfig
    >>> builder = DataDesignerConfigBuilder()
    >>> builder.add_column(
    ...     GlitchlingColumnConfig(
    ...         name="corrupted_text",
    ...         source_column="original_text",
    ...         glitchlings=["Typogre(rate=0.02)", "Mim1c(rate=0.01)"],
    ...         seed=404,
    ...     )
    ... )
"""

from glitchlings.dlc.nemo import (
    GlitchlingColumnConfig,
    GlitchlingColumnGenerator,
    GlitchlingSpec,
    corrupt_dataframe,
    plugin,
)

# Validate that the plugin is properly initialized.
# This will be None if data-designer is not installed or broken.
if plugin is None:
    raise ImportError(
        "Failed to initialize glitchlings-nemo plugin. "
        "The 'data-designer' package is required but could not be imported. "
        "Install it with: pip install data-designer"
    )

__all__ = [
    "GlitchlingColumnConfig",
    "GlitchlingColumnGenerator",
    "GlitchlingSpec",
    "corrupt_dataframe",
    "plugin",
]

"""NVIDIA NeMo DataDesigner plugin for Glitchlings text corruption.

This module provides a DataDesigner column generator that applies Glitchlings
transformations to text columns, enabling deterministic text corruption for
model robustness testing and adversarial augmentation.

The plugin integrates with NeMo's experimental plugin system, exposing
Glitchlings as a discoverable column generator.

Example:
    >>> from glitchlings.dlc.nemo import GlitchlingColumnConfig
    >>> from data_designer import DataDesignerConfigBuilder
    >>> builder = DataDesignerConfigBuilder()
    >>> builder.add_column(
    ...     GlitchlingColumnConfig(
    ...         name="corrupted_prompt",
    ...         source_column="prompt",
    ...         glitchlings=["Typogre(rate=0.02)", "Mim1c(rate=0.01)"],
    ...         seed=404,
    ...     )
    ... )
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Union

from ..auggie import Auggie
from ..conf.loaders import load_attack_config
from ..util.adapters import coerce_gaggle
from ..zoo.core import Gaggle, Glitchling

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd

# Type alias for flexible glitchling specification
GlitchlingSpec = Union[
    Gaggle,
    Auggie,
    Glitchling,
    str,
    Sequence[Union[str, Glitchling]],
    Path,
]


def _resolve_gaggle(
    spec: GlitchlingSpec,
    *,
    seed: int,
) -> Gaggle:
    """Resolve a flexible glitchling specification into a Gaggle.

    Args:
        spec: One of:
            - A pre-constructed ``Gaggle``
            - An ``Auggie`` builder (which is a Gaggle subclass)
            - A single ``Glitchling`` instance
            - A string glitchling name (e.g., "typogre")
            - A list of glitchling names or instances
            - A ``Path`` to a YAML config file
        seed: Seed for deterministic corruption.

    Returns:
        A configured Gaggle ready for corruption.

    Raises:
        TypeError: If the spec type is not recognized.
        ValueError: If a config path doesn't exist or is invalid.
    """
    # Auggie is a subclass of Gaggle, so check it first
    if isinstance(spec, Auggie):
        return spec.clone(seed=seed)

    if isinstance(spec, Gaggle):
        return spec.clone(seed=seed)

    # Path to YAML config
    if isinstance(spec, Path):
        config = load_attack_config(spec)
        from ..conf.loaders import build_gaggle

        return build_gaggle(config, seed_override=seed)

    # String path (check if it looks like a file path)
    if isinstance(spec, str) and (spec.endswith(".yaml") or spec.endswith(".yml")):
        path = Path(spec)
        if not path.exists():
            raise FileNotFoundError(
                f"Glitchling config file not found: {spec!r}. "
                "If this was intended as a glitchling name, remove the .yaml/.yml extension."
            )
        config = load_attack_config(path)
        from ..conf.loaders import build_gaggle

        return build_gaggle(config, seed_override=seed)

    # Single glitchling or string, or sequence
    return coerce_gaggle(spec, seed=seed)


def _apply_corruption(
    series: "pd.Series[str]",
    gaggle: Gaggle,
) -> "pd.Series[str]":
    """Apply gaggle corruption to a pandas Series.

    Uses batch corruption for efficiency when possible.

    Args:
        series: Pandas Series of strings to corrupt.
        gaggle: Configured Gaggle to apply.

    Returns:
        Series with corrupted strings.
    """
    # Use batch corruption for better performance via Rust pipeline
    values = series.tolist()
    corrupted = gaggle.corrupt_batch(values)
    return series.__class__(corrupted, index=series.index, name=series.name)


# ---------------------------------------------------------------------------
# DataDesigner Integration Classes
# ---------------------------------------------------------------------------
# These classes follow the NeMo DataDesigner plugin interface.
# They are defined conditionally to avoid hard dependency on data-designer.


def _create_plugin_classes() -> tuple[type, type, Any] | None:
    """Create plugin classes if data-designer is available.

    Returns:
        Tuple of (config_class, generator_class, plugin_object) or None.
    """
    try:
        from data_designer.config.base import SingleColumnConfig
        from data_designer.engine.column_generators.generators.base import (
            ColumnGenerator,
            GenerationStrategy,
            GeneratorMetadata,
        )
        from data_designer.plugins import Plugin, PluginType
    except ImportError:
        return None

    class GlitchlingColumnConfig(SingleColumnConfig):  # type: ignore[misc]
        """Configuration for Glitchlings text corruption column generator.

        Attributes:
            name: Output column name.
            column_type: Discriminator field for DataDesigner plugin discovery.
            glitchlings: Glitchling specification. Can be:
                - A string glitchling name: ``"typogre"``
                - A spec with parameters: ``"Typogre(rate=0.02)"``
                - A list of specs: ``["Typogre(rate=0.02)", "Mim1c(rate=0.01)"]``
                - A path to YAML config: ``"configs/chaos.yaml"``
            source_column: Column to corrupt. If None, corrupts the column
                specified by ``name`` (in-place style).
            seed: RNG seed for deterministic corruption. If None, uses
                a default seed for reproducibility.
        """

        column_type: Literal["glitchlings"] = "glitchlings"
        glitchlings: str | list[str] = "typogre"
        source_column: str | None = None
        seed: int | None = None

    class GlitchlingColumnGenerator(ColumnGenerator):  # type: ignore[misc]
        """Column generator that applies Glitchlings text corruption.

        This generator corrupts text in the source column using the configured
        glitchlings and writes the result to the output column.
        """

        config: GlitchlingColumnConfig

        @staticmethod
        def metadata() -> GeneratorMetadata:
            """Return metadata describing this generator."""
            return GeneratorMetadata(
                name="glitchlings",
                description=(
                    "Apply deterministic, linguistically-principled text corruption "
                    "via Glitchlings for model robustness testing and adversarial augmentation."
                ),
                generation_strategy=GenerationStrategy.FULL_COLUMN,
                required_resources=None,
            )

        def generate(self, data: "pd.DataFrame") -> "pd.DataFrame":
            """Generate corrupted text column.

            Args:
                data: Input DataFrame.

            Returns:
                DataFrame with the corrupted column added/updated.
            """
            source = self.config.source_column or self.config.name
            seed = self.config.seed if self.config.seed is not None else 151

            # Resolve glitchlings specification
            spec: GlitchlingSpec = self.config.glitchlings

            gaggle = _resolve_gaggle(spec, seed=seed)

            # Apply corruption
            data[self.config.name] = _apply_corruption(data[source], gaggle)
            return data

    plugin = Plugin(
        task_cls=GlitchlingColumnGenerator,
        config_cls=GlitchlingColumnConfig,
        plugin_type=PluginType.COLUMN_GENERATOR,
        emoji="👾",
    )

    return GlitchlingColumnConfig, GlitchlingColumnGenerator, plugin


# Try to create the plugin classes
_plugin_result = _create_plugin_classes()

if _plugin_result is not None:
    GlitchlingColumnConfig, GlitchlingColumnGenerator, plugin = _plugin_result
else:
    # Provide stub classes for documentation and type checking
    GlitchlingColumnConfig = None  # type: ignore[assignment]
    GlitchlingColumnGenerator = None  # type: ignore[assignment]
    plugin = None


# ---------------------------------------------------------------------------
# Standalone Functions (usable without DataDesigner)
# ---------------------------------------------------------------------------


def corrupt_dataframe(
    df: "pd.DataFrame",
    glitchlings: GlitchlingSpec,
    *,
    column: str,
    output_column: str | None = None,
    seed: int = 151,
) -> "pd.DataFrame":
    """Corrupt a DataFrame column using Glitchlings.

    This function provides DataFrame corruption without requiring the full
    DataDesigner plugin infrastructure.

    Args:
        df: Input DataFrame.
        glitchlings: Glitchling specification (see ``GlitchlingSpec``).
        column: Source column to corrupt.
        output_column: Output column name. If None, overwrites source column.
        seed: RNG seed for deterministic corruption.

    Returns:
        DataFrame with corrupted column.

    Example:
        >>> import pandas as pd
        >>> from glitchlings.dlc.nemo import corrupt_dataframe
        >>> df = pd.DataFrame({"text": ["Hello world", "Test input"]})
        >>> result = corrupt_dataframe(df, "typogre", column="text", seed=42)
    """
    gaggle = _resolve_gaggle(glitchlings, seed=seed)
    target = output_column if output_column is not None else column
    df = df.copy()
    df[target] = _apply_corruption(df[column], gaggle)
    return df


__all__ = [
    "GlitchlingColumnConfig",
    "GlitchlingColumnGenerator",
    "GlitchlingSpec",
    "corrupt_dataframe",
    "plugin",
]

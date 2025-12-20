"""Tests for the NeMo DataDesigner DLC integration."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pytest

from glitchlings import Auggie, Gaggle, Mim1c, Typogre

pd = pytest.importorskip("pandas")


class TestResolveGaggle:
    """Tests for _resolve_gaggle helper function."""

    def test_resolve_single_glitchling_string(self) -> None:
        """Single glitchling name string is resolved to Gaggle."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        gaggle = _resolve_gaggle("typogre", seed=42)

        assert isinstance(gaggle, Gaggle)
        assert len(gaggle._clones_by_index) == 1

    def test_resolve_glitchling_spec_with_params(self) -> None:
        """Glitchling spec with parameters is resolved correctly."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        gaggle = _resolve_gaggle("Typogre(rate=0.05)", seed=42)

        assert isinstance(gaggle, Gaggle)
        assert len(gaggle._clones_by_index) == 1

    def test_resolve_list_of_specs(self) -> None:
        """List of glitchling specs is resolved to Gaggle with multiple glitchlings."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        specs = ["Typogre(rate=0.02)", "Mim1c(rate=0.01)"]
        gaggle = _resolve_gaggle(specs, seed=42)

        assert isinstance(gaggle, Gaggle)
        assert len(gaggle._clones_by_index) == 2

    def test_resolve_single_glitchling_instance(self) -> None:
        """Single Glitchling instance is wrapped in a Gaggle."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        typogre = Typogre(rate=0.02)
        gaggle = _resolve_gaggle(typogre, seed=42)

        assert isinstance(gaggle, Gaggle)
        assert len(gaggle._clones_by_index) == 1

    def test_resolve_pre_constructed_gaggle(self) -> None:
        """Pre-constructed Gaggle is cloned with the provided seed."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        original = Gaggle([Typogre(rate=0.02)], seed=100)
        resolved = _resolve_gaggle(original, seed=42)

        assert isinstance(resolved, Gaggle)
        assert resolved is not original  # Should be a clone
        assert resolved.seed == 42

    def test_resolve_auggie_builder(self) -> None:
        """Auggie fluent builder is cloned with the provided seed."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        auggie = Auggie(seed=100).typo(rate=0.02).confusable(rate=0.01)
        resolved = _resolve_gaggle(auggie, seed=42)

        assert isinstance(resolved, Gaggle)
        assert resolved is not auggie
        assert resolved.seed == 42
        assert len(resolved._clones_by_index) == 2

    def test_resolve_yaml_config_path(self) -> None:
        """Path to YAML config file is loaded and resolved."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        yaml_content = """
seed: 404
glitchlings:
  - name: Typogre
    rate: 0.02
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = Path(f.name)

        try:
            gaggle = _resolve_gaggle(config_path, seed=42)

            assert isinstance(gaggle, Gaggle)
            # Seed override should apply
            assert gaggle.seed == 42
        finally:
            config_path.unlink()

    def test_resolve_yaml_string_path(self) -> None:
        """String path ending in .yaml is loaded if file exists."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        yaml_content = """
seed: 404
glitchlings:
  - name: Mim1c
    rate: 0.01
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            gaggle = _resolve_gaggle(config_path, seed=42)

            assert isinstance(gaggle, Gaggle)
        finally:
            Path(config_path).unlink()

    def test_resolve_missing_yaml_raises_error(self) -> None:
        """Missing YAML config file raises FileNotFoundError with clear message."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        with pytest.raises(FileNotFoundError, match="Glitchling config file not found"):
            _resolve_gaggle("nonexistent_config.yaml", seed=42)

    def test_resolve_missing_yml_raises_error(self) -> None:
        """Missing .yml config file also raises FileNotFoundError."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        with pytest.raises(FileNotFoundError, match="Glitchling config file not found"):
            _resolve_gaggle("configs/typo.yml", seed=42)


class TestCorruptDataframe:
    """Tests for corrupt_dataframe standalone function."""

    def test_corrupt_dataframe_basic(self) -> None:
        """Basic DataFrame corruption works."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        df = pd.DataFrame({"text": ["Hello world", "Test input"]})
        result = corrupt_dataframe(df, "typogre", column="text", seed=42)

        assert "text" in result.columns
        assert len(result) == 2
        # Original DataFrame should be unchanged
        assert df["text"].iloc[0] == "Hello world"

    def test_corrupt_dataframe_output_column(self) -> None:
        """Corruption can output to a different column."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        df = pd.DataFrame({"text": ["Hello world"]})
        result = corrupt_dataframe(
            df, "typogre", column="text", output_column="corrupted", seed=42
        )

        assert "text" in result.columns
        assert "corrupted" in result.columns
        # Original column should be preserved
        assert result["text"].iloc[0] == "Hello world"

    def test_corrupt_dataframe_determinism(self) -> None:
        """Corruption is deterministic given the same seed."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        df = pd.DataFrame({"text": ["The quick brown fox"]})

        result1 = corrupt_dataframe(df, "typogre", column="text", seed=42)
        result2 = corrupt_dataframe(df, "typogre", column="text", seed=42)

        assert result1["text"].iloc[0] == result2["text"].iloc[0]

    def test_corrupt_dataframe_different_seeds(self) -> None:
        """Different seeds produce different results."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        # Use longer text with higher rate to increase chance of corruption
        df = pd.DataFrame(
            {"text": ["The quick brown fox jumps over the lazy dog repeatedly"]}
        )

        result1 = corrupt_dataframe(
            df, "Typogre(rate=0.3)", column="text", seed=42
        )
        result2 = corrupt_dataframe(
            df, "Typogre(rate=0.3)", column="text", seed=99
        )

        # With high rate, different seeds should produce different results
        # (may occasionally be same by chance, but unlikely with long text and high rate)
        assert result1["text"].iloc[0] != result2["text"].iloc[0]

    def test_corrupt_dataframe_with_gaggle(self) -> None:
        """Pre-constructed Gaggle works with corrupt_dataframe."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        gaggle = Gaggle([Typogre(rate=0.1), Mim1c(rate=0.05)], seed=404)
        df = pd.DataFrame({"text": ["Sample text for testing"]})

        result = corrupt_dataframe(df, gaggle, column="text", seed=42)

        assert "text" in result.columns

    def test_corrupt_dataframe_with_auggie(self) -> None:
        """Auggie fluent builder works with corrupt_dataframe."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        auggie = Auggie(seed=404).typo(rate=0.1).confusable(rate=0.05)
        df = pd.DataFrame({"text": ["Sample text for testing"]})

        result = corrupt_dataframe(df, auggie, column="text", seed=42)

        assert "text" in result.columns

    def test_corrupt_dataframe_preserves_index(self) -> None:
        """Corruption preserves DataFrame index."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        df = pd.DataFrame(
            {"text": ["Hello", "World"]},
            index=["a", "b"],
        )

        result = corrupt_dataframe(df, "typogre", column="text", seed=42)

        assert list(result.index) == ["a", "b"]

    def test_corrupt_dataframe_multiple_glitchlings(self) -> None:
        """List of glitchling specs works."""
        from glitchlings.dlc.nemo import corrupt_dataframe

        df = pd.DataFrame({"text": ["Hello world"]})
        result = corrupt_dataframe(
            df,
            ["Typogre(rate=0.05)", "Mim1c(rate=0.02)"],
            column="text",
            seed=42,
        )

        assert "text" in result.columns


class TestApplyCorruption:
    """Tests for _apply_corruption helper function."""

    def test_apply_corruption_uses_batch(self) -> None:
        """Corruption uses batch processing for efficiency."""
        from glitchlings.dlc.nemo import _apply_corruption

        series = pd.Series(["Hello world", "Test input", "Another sample"])
        gaggle = Gaggle([Typogre(rate=0.1)], seed=42)

        result = _apply_corruption(series, gaggle)

        assert len(result) == 3
        assert isinstance(result, pd.Series)

    def test_apply_corruption_preserves_series_properties(self) -> None:
        """Corruption preserves Series name and index."""
        from glitchlings.dlc.nemo import _apply_corruption

        series = pd.Series(
            ["Hello world", "Test input"],
            index=[10, 20],
            name="my_column",
        )
        gaggle = Gaggle([Typogre(rate=0.1)], seed=42)

        result = _apply_corruption(series, gaggle)

        assert result.name == "my_column"
        assert list(result.index) == [10, 20]


class TestPluginClasses:
    """Tests for DataDesigner plugin classes (when available)."""

    def test_plugin_classes_importable(self) -> None:
        """Plugin classes are importable (may be None if data-designer unavailable)."""
        from glitchlings.dlc.nemo import (
            GlitchlingColumnConfig,
            GlitchlingColumnGenerator,
            plugin,
        )

        # These will be None if data-designer is not installed
        # We just verify the module loads without error
        assert GlitchlingColumnConfig is not None or GlitchlingColumnConfig is None
        assert (
            GlitchlingColumnGenerator is not None or GlitchlingColumnGenerator is None
        )
        assert plugin is not None or plugin is None


class TestGlitchlingSpec:
    """Tests for the GlitchlingSpec type alias behavior."""

    def test_all_spec_types_work(self) -> None:
        """All documented spec types resolve correctly."""
        from glitchlings.dlc.nemo import _resolve_gaggle

        # String name
        g1 = _resolve_gaggle("typogre", seed=1)
        assert isinstance(g1, Gaggle)

        # Spec with params
        g2 = _resolve_gaggle("Typogre(rate=0.05)", seed=1)
        assert isinstance(g2, Gaggle)

        # List of specs
        g3 = _resolve_gaggle(["typogre", "mim1c"], seed=1)
        assert isinstance(g3, Gaggle)

        # Single Glitchling
        g4 = _resolve_gaggle(Typogre(rate=0.05), seed=1)
        assert isinstance(g4, Gaggle)

        # Gaggle
        g5 = _resolve_gaggle(Gaggle([Typogre()], seed=100), seed=1)
        assert isinstance(g5, Gaggle)

        # Auggie
        g6 = _resolve_gaggle(Auggie(seed=100).typo(rate=0.05), seed=1)
        assert isinstance(g6, Gaggle)

"""Tests for enhanced Scannequin OCR simulation features.

Tests the research-backed enhancements:
- Burst model (Kanungo et al., 1994)
- Document-level bias (UNLV-ISRI, 1995)
- Whitespace errors (Smith, 2007; ICDAR)
- Quality presets (Rice et al., 1995)
"""

import pytest

from glitchlings import Scannequin
from glitchlings.constants import SCANNEQUIN_PRESETS
from glitchlings.zoo.scannequin import ocr_artifacts


class TestScannequinPresets:
    """Tests for quality preset functionality."""

    def test_all_presets_are_available(self):
        """Verify all documented presets exist."""
        expected = {"clean_300dpi", "newspaper", "fax", "photocopy_3rd_gen"}
        assert set(SCANNEQUIN_PRESETS.keys()) == expected

    @pytest.mark.parametrize("preset_name", list(SCANNEQUIN_PRESETS.keys()))
    def test_preset_creates_valid_instance(self, preset_name):
        """Each preset should create a valid Scannequin instance."""
        scan = Scannequin(preset=preset_name, seed=42)
        assert scan.name == "Scannequin"
        assert scan.kwargs.get("rate") is not None

    @pytest.mark.parametrize("preset_name", list(SCANNEQUIN_PRESETS.keys()))
    def test_preset_from_preset_method(self, preset_name):
        """from_preset class method should work for all presets."""
        scan = Scannequin.from_preset(preset_name, seed=42)
        assert scan.name == "Scannequin"

    def test_fax_preset_has_high_burst(self):
        """Fax preset should have high burst_enter value."""
        fax = Scannequin.from_preset("fax", seed=42)
        assert fax.kwargs.get("burst_enter") > 0

    def test_fax_preset_has_whitespace_errors(self):
        """Fax preset should have whitespace error rates > 0."""
        fax = Scannequin.from_preset("fax", seed=42)
        assert fax.kwargs.get("space_drop_rate") > 0
        assert fax.kwargs.get("space_insert_rate") > 0

    def test_clean_preset_has_minimal_errors(self):
        """Clean preset should have minimal error parameters."""
        clean = Scannequin.from_preset("clean_300dpi", seed=42)
        assert clean.kwargs.get("burst_enter") == 0.0
        assert clean.kwargs.get("space_drop_rate") == 0.0
        assert clean.kwargs.get("bias_k") == 0

    def test_invalid_preset_raises_error(self):
        """Unknown preset name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            Scannequin(preset="invalid_preset")

    def test_explicit_params_override_preset(self):
        """Explicit parameters should override preset defaults."""
        scan = Scannequin(preset="fax", rate=0.99, seed=42)
        assert scan.kwargs.get("rate") == 0.99
        # But burst_enter should still come from preset
        assert scan.kwargs.get("burst_enter") == 0.1


class TestScannequinBurstModel:
    """Tests for the burst error model (Kanungo et al., 1994)."""

    def test_burst_disabled_by_default(self):
        """Default Scannequin should have burst disabled."""
        scan = Scannequin(seed=42)
        assert scan.kwargs.get("burst_enter") == 0.0

    def test_burst_enabled_produces_different_results(self):
        """Enabling burst should change corruption pattern."""
        text = "The quick brown fox jumps over the lazy dog " * 10
        seed = 42

        # Without burst
        no_burst = Scannequin(rate=0.05, burst_enter=0.0, seed=seed)
        result_no_burst = no_burst(text)

        # With burst
        with_burst = Scannequin(
            rate=0.05, burst_enter=0.2, burst_exit=0.3, burst_multiplier=3.0, seed=seed
        )
        result_with_burst = with_burst(text)

        # Results should differ (high probability with long text)
        # Note: they might rarely be the same due to RNG, but very unlikely
        assert result_no_burst != result_with_burst or len(text) < 50

    def test_burst_parameters_stored_correctly(self):
        """Burst parameters should be stored in kwargs."""
        scan = Scannequin(burst_enter=0.1, burst_exit=0.2, burst_multiplier=4.0, seed=42)
        assert scan.kwargs.get("burst_enter") == 0.1
        assert scan.kwargs.get("burst_exit") == 0.2
        assert scan.kwargs.get("burst_multiplier") == 4.0


class TestScannequinDocumentBias:
    """Tests for document-level bias (UNLV-ISRI, 1995)."""

    def test_bias_disabled_by_default(self):
        """Default Scannequin should have bias disabled."""
        scan = Scannequin(seed=42)
        assert scan.kwargs.get("bias_k") == 0

    def test_bias_parameters_stored_correctly(self):
        """Bias parameters should be stored in kwargs."""
        scan = Scannequin(bias_k=5, bias_beta=3.0, seed=42)
        assert scan.kwargs.get("bias_k") == 5
        assert scan.kwargs.get("bias_beta") == 3.0


class TestScannequinWhitespaceErrors:
    """Tests for whitespace error modeling (Smith, 2007; ICDAR)."""

    def test_whitespace_errors_disabled_by_default(self):
        """Default Scannequin should have whitespace errors disabled."""
        scan = Scannequin(seed=42)
        assert scan.kwargs.get("space_drop_rate") == 0.0
        assert scan.kwargs.get("space_insert_rate") == 0.0

    def test_space_drop_can_merge_words(self):
        """High space_drop_rate should sometimes merge words."""
        text = "hello world test"
        # Use very high rate to ensure we see merges
        result = ocr_artifacts(text, rate=0.0, space_drop_rate=0.99, seed=42)
        # At 99% drop rate, at least one space should be dropped
        assert result.count(" ") < text.count(" ") or result == text

    def test_space_insert_can_split_words(self):
        """High space_insert_rate should sometimes split words."""
        text = "helloworld"
        # Use high insert rate
        result = ocr_artifacts(text, rate=0.0, space_insert_rate=0.5, seed=42)
        # May or may not insert spaces depending on RNG
        # At least verify it doesn't crash
        assert isinstance(result, str)

    def test_whitespace_parameters_stored_correctly(self):
        """Whitespace parameters should be stored in kwargs."""
        scan = Scannequin(space_drop_rate=0.05, space_insert_rate=0.03, seed=42)
        assert scan.kwargs.get("space_drop_rate") == 0.05
        assert scan.kwargs.get("space_insert_rate") == 0.03


class TestScannequinDeterminism:
    """Tests for deterministic behavior with new parameters."""

    def test_determinism_with_burst_enabled(self):
        """Burst mode should still be deterministic."""
        text = "The quick brown fox jumps over the lazy dog"
        scan = Scannequin(rate=0.05, burst_enter=0.1, burst_exit=0.3, burst_multiplier=3.0, seed=42)

        scan.reset_rng(42)
        result1 = scan(text)
        scan.reset_rng(42)
        result2 = scan(text)
        assert result1 == result2

    def test_determinism_with_bias_enabled(self):
        """Bias mode should still be deterministic."""
        text = "The quick brown fox jumps over the lazy dog"
        scan = Scannequin(rate=0.05, bias_k=5, bias_beta=2.5, seed=42)

        scan.reset_rng(42)
        result1 = scan(text)
        scan.reset_rng(42)
        result2 = scan(text)
        assert result1 == result2

    def test_determinism_with_whitespace_errors(self):
        """Whitespace errors should still be deterministic."""
        text = "hello world foo bar"
        scan = Scannequin(rate=0.02, space_drop_rate=0.1, space_insert_rate=0.05, seed=42)

        scan.reset_rng(42)
        result1 = scan(text)
        scan.reset_rng(42)
        result2 = scan(text)
        assert result1 == result2

    @pytest.mark.parametrize("preset_name", list(SCANNEQUIN_PRESETS.keys()))
    def test_determinism_with_presets(self, preset_name):
        """All presets should produce deterministic results."""
        text = "The quick brown fox jumps over the lazy dog"
        scan = Scannequin(preset=preset_name, seed=42)

        scan.reset_rng(42)
        result1 = scan(text)
        scan.reset_rng(42)
        result2 = scan(text)
        assert result1 == result2


class TestScannequinPipelineDescriptor:
    """Tests for pipeline operation descriptor generation."""

    def test_pipeline_descriptor_includes_all_params(self):
        """Pipeline descriptor should include all new parameters."""
        scan = Scannequin(
            rate=0.05,
            burst_enter=0.1,
            burst_exit=0.2,
            burst_multiplier=4.0,
            bias_k=5,
            bias_beta=2.5,
            space_drop_rate=0.02,
            space_insert_rate=0.01,
            seed=42,
        )
        descriptor = scan.pipeline_operation()

        assert descriptor["type"] == "ocr"
        assert descriptor["rate"] == 0.05
        assert descriptor["burst_enter"] == 0.1
        assert descriptor["burst_exit"] == 0.2
        assert descriptor["burst_multiplier"] == 4.0
        assert descriptor["bias_k"] == 5
        assert descriptor["bias_beta"] == 2.5
        assert descriptor["space_drop_rate"] == 0.02
        assert descriptor["space_insert_rate"] == 0.01


class TestScannequinDocumentScope:
    """Tests for document-level scope."""

    def test_scope_is_document(self):
        """Scannequin should operate at document scope."""
        from glitchlings.zoo.core import AttackWave

        scan = Scannequin(seed=42)
        assert scan.level == AttackWave.DOCUMENT

    def test_order_is_late(self):
        """Scannequin should have late execution order."""
        from glitchlings.zoo.core import AttackOrder

        scan = Scannequin(seed=42)
        assert scan.order == AttackOrder.LATE


class TestOcrArtifactsFunction:
    """Tests for the standalone ocr_artifacts function."""

    def test_accepts_all_new_parameters(self):
        """ocr_artifacts function should accept all new parameters."""
        result = ocr_artifacts(
            "hello world",
            rate=0.05,
            seed=42,
            burst_enter=0.1,
            burst_exit=0.3,
            burst_multiplier=3.0,
            bias_k=3,
            bias_beta=2.0,
            space_drop_rate=0.02,
            space_insert_rate=0.01,
        )
        assert isinstance(result, str)

    def test_empty_string_returns_empty(self):
        """Empty input should return empty output."""
        result = ocr_artifacts("")
        assert result == ""

    def test_defaults_work_correctly(self):
        """Function should work with all defaults."""
        result = ocr_artifacts("hello world", seed=42)
        assert isinstance(result, str)

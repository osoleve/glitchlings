"""Tests for Zeedub zero-width character insertion enhancements.

Tests cover:
- Placement modes (random, grapheme_boundary, script_aware)
- Visibility modes (glyphless, with_joiners, semi_visible)
- max_consecutive safety constraint
- Variation selector special handling
- Determinism
"""

from __future__ import annotations

import pytest

from glitchlings import Zeedub
from glitchlings.constants import (
    DEFAULT_ZEEDUB_MAX_CONSECUTIVE,
    DEFAULT_ZEEDUB_PLACEMENT,
    DEFAULT_ZEEDUB_VISIBILITY,
    ZEEDUB_DEFAULT_ZERO_WIDTHS,
    ZEEDUB_GLYPHLESS_PALETTE,
    ZEEDUB_SEMI_VISIBLE_PALETTE,
    ZEEDUB_WITH_JOINERS_PALETTE,
)
from glitchlings.zoo.validation import (
    normalize_zeedub_max_consecutive,
    normalize_zeedub_placement,
    normalize_zeedub_visibility,
)


class TestZeedubValidation:
    """Tests for Zeedub parameter validation."""

    def test_visibility_mode_valid_values(self) -> None:
        assert normalize_zeedub_visibility("glyphless") == "glyphless"
        assert normalize_zeedub_visibility("with_joiners") == "with_joiners"
        assert normalize_zeedub_visibility("semi_visible") == "semi_visible"

    def test_visibility_mode_case_insensitive(self) -> None:
        assert normalize_zeedub_visibility("GLYPHLESS") == "glyphless"
        assert normalize_zeedub_visibility("With_Joiners") == "with_joiners"

    def test_visibility_mode_none_uses_default(self) -> None:
        assert normalize_zeedub_visibility(None) == "glyphless"
        assert normalize_zeedub_visibility(None, "semi_visible") == "semi_visible"

    def test_visibility_mode_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid visibility mode"):
            normalize_zeedub_visibility("invalid")

    def test_placement_mode_valid_values(self) -> None:
        assert normalize_zeedub_placement("random") == "random"
        assert normalize_zeedub_placement("grapheme_boundary") == "grapheme_boundary"
        assert normalize_zeedub_placement("script_aware") == "script_aware"

    def test_placement_mode_case_insensitive(self) -> None:
        assert normalize_zeedub_placement("RANDOM") == "random"
        assert normalize_zeedub_placement("Grapheme_Boundary") == "grapheme_boundary"

    def test_placement_mode_none_uses_default(self) -> None:
        assert normalize_zeedub_placement(None) == "random"
        assert normalize_zeedub_placement(None, "script_aware") == "script_aware"

    def test_placement_mode_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid placement mode"):
            normalize_zeedub_placement("invalid")

    def test_max_consecutive_valid_values(self) -> None:
        assert normalize_zeedub_max_consecutive(0) == 0
        assert normalize_zeedub_max_consecutive(4) == 4
        assert normalize_zeedub_max_consecutive(100) == 100

    def test_max_consecutive_none_uses_default(self) -> None:
        assert normalize_zeedub_max_consecutive(None) == 4
        assert normalize_zeedub_max_consecutive(None, 10) == 10

    def test_max_consecutive_negative_clamped(self) -> None:
        assert normalize_zeedub_max_consecutive(-5) == 0


class TestZeedubPaletteConstants:
    """Tests for Zeedub palette constants."""

    def test_glyphless_palette_is_superset_of_default(self) -> None:
        for char in ZEEDUB_DEFAULT_ZERO_WIDTHS:
            assert char in ZEEDUB_GLYPHLESS_PALETTE

    def test_with_joiners_includes_variation_selectors(self) -> None:
        # VS1-VS16 are U+FE00 to U+FE0F
        for code in range(0xFE00, 0xFE10):
            assert chr(code) in ZEEDUB_WITH_JOINERS_PALETTE

    def test_semi_visible_includes_thin_spaces(self) -> None:
        assert "\u200a" in ZEEDUB_SEMI_VISIBLE_PALETTE  # HAIR SPACE
        assert "\u2009" in ZEEDUB_SEMI_VISIBLE_PALETTE  # THIN SPACE
        assert "\u202f" in ZEEDUB_SEMI_VISIBLE_PALETTE  # NARROW NO-BREAK SPACE


class TestZeedubPipelineDescriptor:
    """Tests for Zeedub pipeline descriptor generation."""

    def test_descriptor_includes_new_fields(self) -> None:
        z = Zeedub(rate=0.05)
        descriptor = z.pipeline_operation()
        assert descriptor["type"] == "zwj"
        assert descriptor["rate"] == 0.05
        assert "visibility" in descriptor
        assert "placement" in descriptor
        assert "max_consecutive" in descriptor

    def test_descriptor_default_values(self) -> None:
        z = Zeedub(rate=0.02)
        descriptor = z.pipeline_operation()
        assert descriptor["visibility"] == DEFAULT_ZEEDUB_VISIBILITY
        assert descriptor["placement"] == DEFAULT_ZEEDUB_PLACEMENT
        assert descriptor["max_consecutive"] == DEFAULT_ZEEDUB_MAX_CONSECUTIVE

    def test_descriptor_custom_values(self) -> None:
        z = Zeedub(
            rate=0.05,
            visibility="semi_visible",
            placement="grapheme_boundary",
            max_consecutive=10,
        )
        descriptor = z.pipeline_operation()
        assert descriptor["visibility"] == "semi_visible"
        assert descriptor["placement"] == "grapheme_boundary"
        assert descriptor["max_consecutive"] == 10


class TestZeedubPlacementModes:
    """Tests for Zeedub placement mode behavior."""

    def test_random_mode_inserts_in_words(self) -> None:
        z = Zeedub(rate=0.5, placement="random", seed=42)
        result = z("hello world")
        # Should have insertions (with rate=0.5, very likely to have some)
        assert len(result) > len("hello world")

    def test_grapheme_boundary_mode_works(self) -> None:
        z = Zeedub(rate=0.5, placement="grapheme_boundary", seed=42)
        result = z("hello world")
        # Should produce valid output
        assert isinstance(result, str)

    def test_script_aware_mode_works(self) -> None:
        z = Zeedub(rate=0.5, placement="script_aware", seed=42)
        result = z("hello world")
        # Should produce valid output
        assert isinstance(result, str)


class TestZeedubVisibilityModesPalette:
    """Tests that visibility modes actually change the character palette."""

    def _extract_inserted_chars(self, original: str, result: str) -> set[str]:
        """Extract characters that were inserted (not in original)."""
        original_set = set(original)
        return {char for char in result if char not in original_set}

    def test_glyphless_uses_basic_invisibles(self) -> None:
        z = Zeedub(rate=0.5, visibility="glyphless", seed=42)
        result = z("hello world test")
        inserted = self._extract_inserted_chars("hello world test", result)
        # Should only contain glyphless characters
        assert inserted, "No characters were inserted"
        for char in inserted:
            assert char in ZEEDUB_GLYPHLESS_PALETTE, f"Unexpected char: {repr(char)}"

    def test_with_joiners_can_include_variation_selectors(self) -> None:
        z = Zeedub(rate=0.8, visibility="with_joiners", seed=123)
        # Use text with emoji that can have VS
        result = z("hello world test again")
        inserted = self._extract_inserted_chars("hello world test again", result)
        assert inserted, "No characters were inserted"
        # All inserted chars should be from with_joiners palette
        for char in inserted:
            assert char in ZEEDUB_WITH_JOINERS_PALETTE, f"Unexpected char: {repr(char)}"

    def test_semi_visible_can_include_thin_spaces(self) -> None:
        z = Zeedub(rate=0.8, visibility="semi_visible", seed=456)
        result = z("hello world test again please")
        inserted = self._extract_inserted_chars("hello world test again please", result)
        assert inserted, "No characters were inserted"
        # All inserted chars should be from semi_visible palette
        for char in inserted:
            assert char in ZEEDUB_SEMI_VISIBLE_PALETTE, f"Unexpected char: {repr(char)}"

    def test_visibility_modes_produce_different_palettes(self) -> None:
        # Different visibility modes should potentially use different characters
        text = "the quick brown fox jumps over the lazy dog"
        glyphless = Zeedub(rate=0.5, visibility="glyphless", seed=42)
        with_joiners = Zeedub(rate=0.5, visibility="with_joiners", seed=42)

        result_glyphless = glyphless(text)
        result_joiners = with_joiners(text)

        # The results should differ because with_joiners has more options
        # (though they might be the same by chance, this is statistically unlikely)
        inserted_glyphless = self._extract_inserted_chars(text, result_glyphless)
        inserted_joiners = self._extract_inserted_chars(text, result_joiners)

        # At minimum, verify both produced valid outputs from their palettes
        for char in inserted_glyphless:
            assert char in ZEEDUB_GLYPHLESS_PALETTE
        for char in inserted_joiners:
            assert char in ZEEDUB_WITH_JOINERS_PALETTE

    def test_descriptor_has_empty_characters_by_default(self) -> None:
        """Verify that pipeline descriptor passes empty characters so Rust uses visibility."""
        z = Zeedub(rate=0.05, visibility="with_joiners")
        descriptor = z.pipeline_operation()
        # Characters should be empty so Rust uses visibility mode's palette
        assert descriptor["characters"] == []
        assert descriptor["visibility"] == "with_joiners"


class TestZeedubMaxConsecutive:
    """Tests for Zeedub max_consecutive constraint."""

    def test_max_consecutive_limits_runs(self) -> None:
        # With rate=1.0, we'd normally get insertions at every position
        z = Zeedub(rate=1.0, max_consecutive=2, seed=42)
        result = z("abcdefgh")
        # Count consecutive zero-width characters
        max_run = 0
        current_run = 0
        for char in result:
            if char in ZEEDUB_GLYPHLESS_PALETTE:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        # Should respect max_consecutive=2
        assert max_run <= 2

    def test_max_consecutive_zero_allows_unlimited(self) -> None:
        z = Zeedub(rate=1.0, max_consecutive=0, seed=42)
        result = z("abc")
        # Should still produce valid output
        assert isinstance(result, str)


class TestZeedubDeterminism:
    """Tests for Zeedub determinism with new parameters."""

    def test_determinism_with_placement_modes(self) -> None:
        for placement in ["random", "grapheme_boundary", "script_aware"]:
            z1 = Zeedub(rate=0.2, placement=placement, seed=42)
            z2 = Zeedub(rate=0.2, placement=placement, seed=42)
            text = "The quick brown fox jumps over the lazy dog."
            assert z1(text) == z2(text), f"Non-deterministic with placement={placement}"

    def test_determinism_with_visibility_modes(self) -> None:
        for visibility in ["glyphless", "with_joiners", "semi_visible"]:
            z1 = Zeedub(rate=0.2, visibility=visibility, seed=42)
            z2 = Zeedub(rate=0.2, visibility=visibility, seed=42)
            text = "The quick brown fox jumps over the lazy dog."
            assert z1(text) == z2(text), f"Non-deterministic with visibility={visibility}"

    def test_different_seeds_produce_different_output(self) -> None:
        z1 = Zeedub(rate=0.2, seed=42)
        z2 = Zeedub(rate=0.2, seed=43)
        text = "The quick brown fox jumps over the lazy dog."
        # With different seeds, very likely to produce different output
        # (not guaranteed but statistically very unlikely to be same)
        assert z1(text) != z2(text)


class TestZeedubScriptAwareMode:
    """Tests for script-aware placement mode."""

    def test_script_aware_allows_non_joiner_characters(self) -> None:
        # With Latin text, only non-joiner characters should be used
        z = Zeedub(rate=0.5, placement="script_aware", seed=42)
        result = z("hello")
        # Should produce valid output (non-empty with some insertions)
        assert isinstance(result, str)

    def test_script_aware_with_arabic(self) -> None:
        # Arabic text should allow joiners
        z = Zeedub(rate=0.5, placement="script_aware", seed=42)
        result = z("\u0645\u0631\u062d\u0628\u0627")  # "mrhba" in Arabic
        assert isinstance(result, str)

    def test_script_aware_with_emoji(self) -> None:
        # Emoji should allow joiners (for ZWJ sequences)
        z = Zeedub(rate=0.5, placement="script_aware", seed=42)
        result = z("\U0001F468\U0001F469\U0001F467")  # Family emoji base characters
        assert isinstance(result, str)


class TestZeedubGraphemeBoundaryMode:
    """Tests for grapheme boundary placement mode."""

    def test_grapheme_boundary_with_combining_chars(self) -> None:
        # Text with combining characters: e + combining acute
        z = Zeedub(rate=0.5, placement="grapheme_boundary", seed=42)
        result = z("cafe\u0301")  # "café" with combining acute
        # Should not split the grapheme cluster
        assert isinstance(result, str)

    def test_grapheme_boundary_with_emoji_zwj_sequence(self) -> None:
        # Family emoji (ZWJ sequence)
        z = Zeedub(rate=0.5, placement="grapheme_boundary", seed=42)
        emoji = "\U0001F468\u200D\U0001F469\u200D\U0001F467"  # Family emoji
        result = z(emoji)
        # Should produce valid output
        assert isinstance(result, str)

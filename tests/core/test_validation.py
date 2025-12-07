"""Tests for zoo/validation.py boundary validation layer."""

from __future__ import annotations

import math

import pytest

from glitchlings.zoo.validation import (
    clamp_rate,
    clamp_rate_unit,
    normalise_homophone_group,
    normalise_mim1c_banned,
    normalise_mim1c_classes,
    normalize_rushmore_mode_item,
    normalize_rushmore_modes,
    normalize_zero_width_palette,
    resolve_bool_flag,
    resolve_rate,
    resolve_rushmore_mode_rate,
)


class TestRateClamping:
    """Tests for rate clamping functions."""

    def test_clamp_rate_negative_to_zero(self) -> None:
        assert clamp_rate(-0.5) == 0.0

    def test_clamp_rate_positive_unchanged(self) -> None:
        assert clamp_rate(0.5) == 0.5

    def test_clamp_rate_allows_above_one(self) -> None:
        assert clamp_rate(2.5) == 2.5

    def test_clamp_rate_nan_to_zero(self) -> None:
        assert clamp_rate(float("nan")) == 0.0

    def test_clamp_rate_nan_preserved_when_allowed(self) -> None:
        result = clamp_rate(float("nan"), allow_nan=True)
        assert math.isnan(result)

    def test_clamp_rate_unit_caps_at_one(self) -> None:
        assert clamp_rate_unit(2.5) == 1.0

    def test_clamp_rate_unit_floor_at_zero(self) -> None:
        assert clamp_rate_unit(-1.0) == 0.0

    def test_clamp_rate_unit_mid_range(self) -> None:
        assert clamp_rate_unit(0.5) == 0.5

    def test_resolve_rate_uses_default_when_none(self) -> None:
        assert resolve_rate(None, 0.02) == 0.02

    def test_resolve_rate_uses_provided_value(self) -> None:
        assert resolve_rate(0.1, 0.02) == 0.1

    def test_resolve_rate_clamps_negative(self) -> None:
        assert resolve_rate(-0.5, 0.02) == 0.0

    def test_resolve_rate_no_clamp(self) -> None:
        assert resolve_rate(-0.5, 0.02, clamp=False) == -0.5

    def test_resolve_rate_unit_interval(self) -> None:
        assert resolve_rate(2.0, 0.02, unit_interval=True) == 1.0


class TestMim1cValidation:
    """Tests for Mim1c class/banned character validation."""

    def test_normalise_classes_none(self) -> None:
        assert normalise_mim1c_classes(None) is None

    def test_normalise_classes_all_string(self) -> None:
        assert normalise_mim1c_classes("all") == "all"

    def test_normalise_classes_all_uppercase(self) -> None:
        assert normalise_mim1c_classes("ALL") == "all"

    def test_normalise_classes_single_string(self) -> None:
        assert normalise_mim1c_classes("LATIN") == ("LATIN",)

    def test_normalise_classes_list(self) -> None:
        assert normalise_mim1c_classes(["LATIN", "GREEK"]) == ("LATIN", "GREEK")

    def test_normalise_classes_invalid_type(self) -> None:
        with pytest.raises(TypeError, match="iterable of strings"):
            normalise_mim1c_classes(123)

    def test_normalise_banned_none(self) -> None:
        assert normalise_mim1c_banned(None) is None

    def test_normalise_banned_string_to_chars(self) -> None:
        assert normalise_mim1c_banned("abc") == ("a", "b", "c")

    def test_normalise_banned_list(self) -> None:
        assert normalise_mim1c_banned(["x", "y"]) == ("x", "y")

    def test_normalise_banned_invalid_type(self) -> None:
        with pytest.raises(TypeError, match="iterable of strings"):
            normalise_mim1c_banned(123)


class TestWherewolfValidation:
    """Tests for homophone normalization."""

    def test_normalise_homophone_group_basic(self) -> None:
        result = normalise_homophone_group(["There", "Their", "They're"])
        assert result == ("there", "their", "they're")

    def test_normalise_homophone_group_deduplicates(self) -> None:
        result = normalise_homophone_group(["To", "to", "Too"])
        assert result == ("to", "too")

    def test_normalise_homophone_group_filters_empty(self) -> None:
        result = normalise_homophone_group(["", "foo", ""])
        assert result == ("foo",)


class TestRushmoreValidation:
    """Tests for Rushmore mode validation."""

    def test_normalize_mode_item_delete(self) -> None:
        assert normalize_rushmore_mode_item("delete") == ["delete"]

    def test_normalize_mode_item_alias_drop(self) -> None:
        assert normalize_rushmore_mode_item("drop") == ["delete"]

    def test_normalize_mode_item_all(self) -> None:
        assert normalize_rushmore_mode_item("all") == ["delete", "duplicate", "swap"]

    def test_normalize_mode_item_compound(self) -> None:
        assert normalize_rushmore_mode_item("delete+duplicate") == [
            "delete",
            "duplicate",
        ]

    def test_normalize_mode_item_invalid(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            normalize_rushmore_mode_item("unknown")

    def test_normalize_modes_none_uses_default(self) -> None:
        assert normalize_rushmore_modes(None) == ("delete",)

    def test_normalize_modes_single_string(self) -> None:
        assert normalize_rushmore_modes("swap") == ("swap",)

    def test_normalize_modes_list(self) -> None:
        assert normalize_rushmore_modes(["delete", "swap"]) == ("delete", "swap")

    def test_normalize_modes_deduplicates(self) -> None:
        result = normalize_rushmore_modes(["delete", "drop"])  # drop is alias
        assert result == ("delete",)

    def test_resolve_rushmore_mode_rate_specific(self) -> None:
        result = resolve_rushmore_mode_rate(
            mode="delete",
            global_rate=0.1,
            specific_rate=0.05,
            default_rates={"delete": 0.01},
            allow_default=True,
        )
        assert result == 0.05

    def test_resolve_rushmore_mode_rate_global(self) -> None:
        result = resolve_rushmore_mode_rate(
            mode="delete",
            global_rate=0.1,
            specific_rate=None,
            default_rates={"delete": 0.01},
            allow_default=True,
        )
        assert result == 0.1

    def test_resolve_rushmore_mode_rate_default(self) -> None:
        result = resolve_rushmore_mode_rate(
            mode="delete",
            global_rate=None,
            specific_rate=None,
            default_rates={"delete": 0.01},
            allow_default=True,
        )
        assert result == 0.01

    def test_resolve_rushmore_mode_rate_no_default(self) -> None:
        result = resolve_rushmore_mode_rate(
            mode="delete",
            global_rate=None,
            specific_rate=None,
            default_rates={"delete": 0.01},
            allow_default=False,
        )
        assert result is None

    def test_resolve_rushmore_swap_clamped(self) -> None:
        result = resolve_rushmore_mode_rate(
            mode="swap",
            global_rate=2.0,
            specific_rate=None,
            default_rates={},
            allow_default=False,
        )
        assert result == 1.0


class TestZeedubValidation:
    """Tests for zero-width character palette validation."""

    def test_normalize_palette_none_uses_default(self) -> None:
        default = ("\u200b", "\u200c")
        result = normalize_zero_width_palette(None, default)
        assert result == default

    def test_normalize_palette_filters_empty(self) -> None:
        result = normalize_zero_width_palette(["\u200b", "", "\u200c"], ())
        assert result == ("\u200b", "\u200c")


class TestBooleanFlags:
    """Tests for boolean flag resolution."""

    def test_resolve_bool_specific_true(self) -> None:
        assert resolve_bool_flag(True, False) is True

    def test_resolve_bool_specific_false(self) -> None:
        assert resolve_bool_flag(False, True) is False

    def test_resolve_bool_none_uses_global(self) -> None:
        assert resolve_bool_flag(None, True) is True
        assert resolve_bool_flag(None, False) is False

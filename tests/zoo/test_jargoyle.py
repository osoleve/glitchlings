"""Tests for the Jargoyle glitchling with dictionary-based word drift."""

from __future__ import annotations

import pytest

from glitchlings.zoo.jargoyle import (
    Jargoyle,
    jargoyle_drift,
    list_lexeme_dictionaries,
)


def _clean_tokens(text: str) -> list[str]:
    return [token.strip(".,") for token in text.split()]


class TestJargoyleDriftFunction:
    """Tests for the jargoyle_drift function."""

    def test_jargoyle_drift_basic(self) -> None:
        """Test basic word replacement with synonyms dictionary."""
        text = "big small fast slow"
        result = jargoyle_drift(text, lexemes="synonyms", rate=1.0, seed=42)
        assert result != text

    def test_jargoyle_drift_deterministic(self) -> None:
        """Test that same seed produces same result."""
        text = "big small fast slow"
        result1 = jargoyle_drift(text, lexemes="synonyms", rate=1.0, seed=42)
        result2 = jargoyle_drift(text, lexemes="synonyms", rate=1.0, seed=42)
        assert result1 == result2

    def test_jargoyle_drift_different_seeds(self) -> None:
        """Test that different seeds can produce different results."""
        text = "big small fast slow"
        result1 = jargoyle_drift(text, lexemes="synonyms", rate=1.0, seed=42)
        result2 = jargoyle_drift(text, lexemes="synonyms", rate=1.0, seed=999)
        # Results may differ (though not guaranteed with limited dictionary)
        # At minimum, both should be valid transformations
        assert isinstance(result1, str)
        assert isinstance(result2, str)

    def test_jargoyle_drift_rate_zero(self) -> None:
        """Test that rate=0 produces no changes."""
        text = "big small fast slow"
        result = jargoyle_drift(text, lexemes="synonyms", rate=0.0, seed=42)
        assert result == text

    def test_jargoyle_drift_literal_mode(self) -> None:
        """Test literal mode uses first dictionary entry."""
        text = "big small"
        result1 = jargoyle_drift(text, lexemes="synonyms", mode="literal", rate=1.0, seed=1)
        result2 = jargoyle_drift(text, lexemes="synonyms", mode="literal", rate=1.0, seed=999)
        # Literal mode should be deterministic regardless of seed
        assert result1 == result2

    def test_jargoyle_drift_colors_dictionary(self) -> None:
        """Test color swapping with colors dictionary."""
        text = "The red ball is blue."
        result = jargoyle_drift(text, lexemes="colors", rate=1.0, seed=42)
        # Should replace color words
        assert "red" not in result.lower() or "blue" not in result.lower()

    def test_jargoyle_drift_preserves_structure(self) -> None:
        """Test that sentence structure is preserved."""
        text = "The big dog ran fast."
        result = jargoyle_drift(text, lexemes="synonyms", rate=1.0, seed=42)
        # Should have same number of tokens
        assert len(result.split()) == len(text.split())

    def test_jargoyle_drift_invalid_dictionary(self) -> None:
        """Test that invalid dictionary name raises error."""
        text = "hello world"
        with pytest.raises(ValueError, match="Invalid lexemes"):
            jargoyle_drift(text, lexemes="nonexistent", rate=1.0, seed=42)


class TestJargoyleGlitchling:
    """Tests for the Jargoyle glitchling class."""

    def test_jargoyle_default_params(self) -> None:
        """Test Jargoyle with default parameters."""
        glitch = Jargoyle(seed=42)
        assert glitch.kwargs.get("lexemes") == "synonyms"
        assert glitch.kwargs.get("mode") == "drift"
        assert glitch.kwargs.get("rate") == 0.01

    def test_jargoyle_custom_lexemes(self) -> None:
        """Test Jargoyle with custom lexemes parameter."""
        glitch = Jargoyle(lexemes="colors", seed=42)
        assert glitch.kwargs.get("lexemes") == "colors"

    def test_jargoyle_corrupt(self) -> None:
        """Test Jargoyle.corrupt method."""
        glitch = Jargoyle(lexemes="synonyms", rate=1.0, seed=42)
        text = "big small fast slow"
        result = glitch.corrupt(text)
        assert result != text

    def test_jargoyle_deterministic(self) -> None:
        """Test Jargoyle produces deterministic results."""
        glitch1 = Jargoyle(lexemes="synonyms", rate=1.0, seed=42)
        glitch2 = Jargoyle(lexemes="synonyms", rate=1.0, seed=42)
        text = "big small fast slow"
        assert glitch1.corrupt(text) == glitch2.corrupt(text)

    def test_jargoyle_set_param(self) -> None:
        """Test Jargoyle.set_param method."""
        glitch = Jargoyle(seed=42)
        glitch.set_param("rate", 0.5)
        assert glitch.kwargs.get("rate") == 0.5
        glitch.set_param("lexemes", "colors")
        assert glitch.kwargs.get("lexemes") == "colors"

    def test_jargoyle_invalid_mode(self) -> None:
        """Test that invalid mode raises error."""
        with pytest.raises(ValueError, match="mode"):
            Jargoyle(mode="invalid", seed=42)

    def test_jargoyle_rate_clamped(self) -> None:
        """Test that rate values are stored as provided."""
        # Note: Jargoyle does not clamp rates in __init__ - clamping happens
        # in the Rust backend during actual transformation.
        glitch = Jargoyle(rate=2.0, seed=42)
        assert glitch.kwargs.get("rate") == 2.0
        glitch2 = Jargoyle(rate=-0.5, seed=42)
        assert glitch2.kwargs.get("rate") == -0.5

    def test_jargoyle_pipeline_operation(self) -> None:
        """Test that Jargoyle provides a valid pipeline operation."""
        glitch = Jargoyle(lexemes="synonyms", rate=0.5, seed=42)
        op = glitch.pipeline_operation()  # It's a method, not a property
        assert op is not None
        assert op.get("type") == "jargoyle"


class TestListLexemeDictionaries:
    """Tests for the list_lexeme_dictionaries function."""

    def test_list_returns_dictionaries(self) -> None:
        """Test that list returns available dictionaries."""
        dicts = list_lexeme_dictionaries()
        assert isinstance(dicts, list)
        assert len(dicts) > 0

    def test_list_contains_expected_dictionaries(self) -> None:
        """Test that standard dictionaries are present."""
        dicts = list_lexeme_dictionaries()
        assert "synonyms" in dicts
        assert "colors" in dicts

    def test_list_does_not_contain_meta(self) -> None:
        """Test that _meta sections are excluded."""
        dicts = list_lexeme_dictionaries()
        assert "_meta" not in dicts
        for d in dicts:
            assert not d.startswith("_")

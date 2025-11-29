"""Shared glitchling fixtures for all test modules."""

from __future__ import annotations

import pytest


@pytest.fixture
def fresh_glitchling():
    """Factory fixture that returns a fresh clone of any glitchling.

    Usage:
        def test_something(fresh_glitchling):
            glitch = fresh_glitchling("typogre")
            glitch.set_param("rate", 0.1)
            result = glitch("test text")

    Args:
        glitchling_name: Name of the glitchling (e.g., "typogre", "mim1c")

    Returns:
        A fresh clone of the requested glitchling
    """

    def _factory(glitchling_name: str):
        from glitchlings import zoo

        glitchling = getattr(zoo, glitchling_name.lower())
        return glitchling.clone()

    return _factory


@pytest.fixture(scope="session")
def sample_text():
    """Canonical sample text for testing.

    This is the standard SAMPLE_TEXT used throughout the glitchlings library.
    """
    from glitchlings import SAMPLE_TEXT

    return SAMPLE_TEXT

"""Shared test data and samples for the glitchlings test suite."""
from __future__ import annotations

from tests.data.samples import (
    COMMON_WORDS,
    EMPTY_TEXT,
    SAMPLE_COLORS,
    SAMPLE_EMOJI,
    SAMPLE_HOMOPHONES,
    SAMPLE_MIXED_CASE,
    SAMPLE_MULTILINE,
    SAMPLE_PARAGRAPH,
    SAMPLE_PEDANT_TEXT,
    SAMPLE_QUOTE_TEXT,
    SAMPLE_REPEATED,
    SAMPLE_UNICODE,
    SAMPLE_WITH_NUMBERS,
    SAMPLE_WITH_PUNCTUATION,
    SINGLE_CHAR,
    SINGLE_WORD,
    WHITESPACE_ONLY,
)

__all__ = [
    # Simple samples
    "SAMPLE_COLORS",
    "SAMPLE_HOMOPHONES",
    "SAMPLE_PEDANT_TEXT",
    "SAMPLE_QUOTE_TEXT",
    # Complex samples
    "SAMPLE_MULTILINE",
    "SAMPLE_PARAGRAPH",
    # Edge cases
    "EMPTY_TEXT",
    "WHITESPACE_ONLY",
    "SINGLE_WORD",
    "SINGLE_CHAR",
    # Unicode samples
    "SAMPLE_UNICODE",
    "SAMPLE_EMOJI",
    # Repeated patterns
    "SAMPLE_REPEATED",
    # Common word lists
    "COMMON_WORDS",
    # Structured samples
    "SAMPLE_WITH_PUNCTUATION",
    "SAMPLE_WITH_NUMBERS",
    "SAMPLE_MIXED_CASE",
]

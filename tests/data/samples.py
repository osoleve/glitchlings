"""Canonical test data used across the test suite."""
from __future__ import annotations

# Simple test strings
SAMPLE_COLORS = "red balloon green light blue sky"
SAMPLE_HOMOPHONES = "allowed write heir"
SAMPLE_PEDANT_TEXT = "If I was here, who you gonna call?"
SAMPLE_QUOTE_TEXT = '"Hello," they said. "How are you?"'

# Complex samples
SAMPLE_MULTILINE = """One morning, when Gregor Samsa woke from troubled dreams,
he found himself transformed in his bed into a horrible vermin."""

SAMPLE_PARAGRAPH = """The quick brown fox jumps over the lazy dog. This sentence
contains every letter of the alphabet and is commonly used for testing. It has
been a standard fixture in typography and font testing for many years."""

# Edge cases
EMPTY_TEXT = ""
WHITESPACE_ONLY = "   \t\n  "
SINGLE_WORD = "alpha"
SINGLE_CHAR = "x"

# Unicode samples
SAMPLE_UNICODE = "Héllo wörld! 你好世界 🌍"
SAMPLE_EMOJI = "Hello 👋 world 🌍 with emojis 🎉"

# Repeated patterns for rate testing
SAMPLE_REPEATED = "alpha " * 100  # 100 repetitions for statistical testing

# Common word lists for substitution tests
COMMON_WORDS = [
    "hello", "world", "test", "sample", "example",
    "quick", "brown", "fox", "jumps", "over",
]

# Text with specific structures
SAMPLE_WITH_PUNCTUATION = "Hello! How are you? I'm fine, thanks. What about you..."
SAMPLE_WITH_NUMBERS = "There are 42 items and 3.14 is approximately pi."
SAMPLE_MIXED_CASE = "ThIs Is A MiXeD CaSe StRiNg"

"""Fuzz tests for FFI boundary panic-safety.

These tests use hypothesis to generate adversarial inputs and verify that
the Rust FFI functions never panic (which would crash the Python interpreter)
but instead return clean PyValueError or equivalent for all malformed inputs.

The _corruption_engine module exposes functions like plan_operations and
compose_operations to Python. These are attack surfaces for unexpected input
that could cause Rust panics.

Run tests:
    pytest tests/test_ffi_fuzzing.py -v --hypothesis-seed=0
"""

from __future__ import annotations

import pytest

try:  # pragma: no cover - optional dependency guard
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st
except ModuleNotFoundError:  # pragma: no cover - triggered when hypothesis absent
    pytest.skip("hypothesis is required for fuzz tests", allow_module_level=True)

# Import the Rust module directly to fuzz the FFI boundary
try:
    from glitchlings import _corruption_engine as engine
except ImportError:
    pytest.skip("_corruption_engine not available", allow_module_level=True)


# ===========================================================================
# Shared Hypothesis Settings
# ===========================================================================

# Fast settings for CI - 10 examples per test for ~15s total test time
fuzz_settings = settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    deadline=None,  # FFI calls may be slow
)


# ===========================================================================
# Custom Strategies for Adversarial Input Generation
# ===========================================================================

# Seed values at integer boundaries
seed_strategy = st.sampled_from([None, 0, 1, 42, 2**63 - 1])

# Master seed for orchestration (signed 128-bit)
master_seed_strategy = st.sampled_from([0, -1, 42, 2**63 - 1, -(2**63)])

# Rate values including edge cases
rate_strategy = st.sampled_from([0.0, 0.1, 0.5, 1.0, -0.1, 1.5, float("inf"), float("nan")])

# Zero-width characters
ZERO_WIDTH_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]

# Text strategies with adversarial cases
adversarial_text = st.sampled_from([
    "",
    " ",
    "".join(ZERO_WIDTH_CHARS),
    "hello world",
    "The quick brown fox jumps over the lazy dog.",
    "Hello, World! How are you?",
    "a" * 100,
])


# ===========================================================================
# Word-Level Operations Tests
# ===========================================================================


class TestWordLevelOperations:
    """Fuzz tests for word-level FFI operations."""

    @fuzz_settings
    @given(text=adversarial_text, rate=rate_strategy, seed=seed_strategy)
    def test_reduplicate_words_no_crash(
        self, text: str, rate: float, seed: int | None
    ) -> None:
        """reduplicate_words should never crash."""
        try:
            result = engine.reduplicate_words(text, rate, False, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(text=adversarial_text, rate=rate_strategy, seed=seed_strategy)
    def test_delete_random_words_no_crash(
        self, text: str, rate: float, seed: int | None
    ) -> None:
        """delete_random_words should never crash."""
        try:
            result = engine.delete_random_words(text, rate, False, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(text=adversarial_text, rate=rate_strategy, seed=seed_strategy)
    def test_swap_adjacent_words_no_crash(
        self, text: str, rate: float, seed: int | None
    ) -> None:
        """swap_adjacent_words should never crash."""
        try:
            result = engine.swap_adjacent_words(text, rate, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        rate=rate_strategy,
        weighting=st.sampled_from(["flat", "length", "frequency", "invalid", ""]),
        seed=seed_strategy,
    )
    def test_substitute_homophones_no_crash(
        self, text: str, rate: float, weighting: str, seed: int | None
    ) -> None:
        """substitute_homophones should never crash."""
        try:
            result = engine.substitute_homophones(text, rate, weighting, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        replacement=st.sampled_from(["█", "*", "", "XX"]),
        rate=rate_strategy,
        seed=seed_strategy,
    )
    def test_redact_words_no_crash(
        self, text: str, replacement: str, rate: float, seed: int | None
    ) -> None:
        """redact_words should never crash."""
        try:
            result = engine.redact_words(text, replacement, rate, False, False, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass


# ===========================================================================
# Character-Level Operations Tests
# ===========================================================================


class TestCharacterLevelOperations:
    """Fuzz tests for character-level FFI operations."""

    @fuzz_settings
    @given(
        text=adversarial_text,
        rate=rate_strategy,
        seed=seed_strategy,
        mode=st.sampled_from([None, "single_script", "mixed_script", "invalid"]),
    )
    def test_swap_homoglyphs_no_crash(
        self, text: str, rate: float, seed: int | None, mode: str | None
    ) -> None:
        """swap_homoglyphs should never crash."""
        try:
            result = engine.swap_homoglyphs(text, rate, None, None, seed, mode, None)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(text=adversarial_text, rate=rate_strategy, seed=seed_strategy)
    def test_ocr_artifacts_no_crash(
        self, text: str, rate: float, seed: int | None
    ) -> None:
        """ocr_artifacts should never crash."""
        try:
            result = engine.ocr_artifacts(
                text, rate, seed, None, None, None, None, None, None, None
            )
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        rate=rate_strategy,
        characters=st.just(ZERO_WIDTH_CHARS),
        seed=seed_strategy,
    )
    def test_inject_zero_widths_no_crash(
        self, text: str, rate: float, characters: list[str], seed: int | None
    ) -> None:
        """inject_zero_widths should never crash."""
        try:
            result = engine.inject_zero_widths(
                text, rate, characters, seed, None, None, None
            )
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        rate=rate_strategy,
        extension_min=st.integers(min_value=-10, max_value=10),
        extension_max=st.integers(min_value=-10, max_value=10),
        seed=seed_strategy,
    )
    def test_stretch_word_no_crash(
        self, text: str, rate: float, extension_min: int, extension_max: int, seed: int | None
    ) -> None:
        """stretch_word should never crash."""
        try:
            result = engine.stretch_word(text, rate, extension_min, extension_max, 6, 0.45, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass


# ===========================================================================
# Keyboard Typo Operations Tests
# ===========================================================================


class TestKeyboardTypoOperations:
    """Fuzz tests for keyboard typo FFI operations."""

    MINIMAL_LAYOUT = {"a": ["s", "q"], "b": ["v", "g"]}

    @fuzz_settings
    @given(text=adversarial_text, rate=rate_strategy, seed=seed_strategy)
    def test_keyboard_typo_no_crash(
        self, text: str, rate: float, seed: int | None
    ) -> None:
        """keyboard_typo should never crash."""
        try:
            result = engine.keyboard_typo(text, rate, self.MINIMAL_LAYOUT, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        layout=st.sampled_from([{}, {"a": []}, {"": ["a"]}]),
        seed=seed_strategy,
    )
    def test_keyboard_typo_adversarial_layout_no_crash(
        self, text: str, layout: dict, seed: int | None
    ) -> None:
        """keyboard_typo with adversarial layouts should never crash."""
        try:
            result = engine.keyboard_typo(text, 0.1, layout, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        enter_rate=rate_strategy,
        exit_rate=rate_strategy,
        seed=seed_strategy,
    )
    def test_slip_modifier_no_crash(
        self, text: str, enter_rate: float, exit_rate: float, seed: int | None
    ) -> None:
        """slip_modifier should never crash."""
        shift_map = {"a": "A", "b": "B"}
        try:
            result = engine.slip_modifier(text, enter_rate, exit_rate, shift_map, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass


# ===========================================================================
# Lexeme Operations Tests
# ===========================================================================


class TestLexemeOperations:
    """Fuzz tests for lexeme substitution FFI operations."""

    @fuzz_settings
    @given(
        text=adversarial_text,
        lexemes=st.sampled_from(["synonyms", "colors", "invalid", ""]),
        mode=st.sampled_from(["literal", "drift", "invalid"]),
        rate=rate_strategy,
        seed=seed_strategy,
    )
    def test_substitute_lexeme_no_crash(
        self, text: str, lexemes: str, mode: str, rate: float, seed: int | None
    ) -> None:
        """substitute_lexeme should never crash."""
        try:
            result = engine.substitute_lexeme(text, lexemes, mode, rate, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    def test_list_lexeme_dictionaries_no_crash(self) -> None:
        """list_lexeme_dictionaries should never crash."""
        result = engine.list_lexeme_dictionaries()
        assert isinstance(result, list)

    def test_list_bundled_lexeme_dictionaries_no_crash(self) -> None:
        """list_bundled_lexeme_dictionaries should never crash."""
        result = engine.list_bundled_lexeme_dictionaries()
        assert isinstance(result, list)

    @fuzz_settings
    @given(name=st.sampled_from(["synonyms", "", "nonexistent"]))
    def test_is_bundled_lexeme_no_crash(self, name: str) -> None:
        """is_bundled_lexeme should never crash."""
        try:
            result = engine.is_bundled_lexeme(name)
            assert isinstance(result, bool)
        except (ValueError, TypeError):
            pass


# ===========================================================================
# Grammar Operations Tests
# ===========================================================================


class TestGrammarOperations:
    """Fuzz tests for grammar rule FFI operations."""

    @fuzz_settings
    @given(
        text=adversarial_text,
        stone=st.sampled_from(["split_infinitive", "dangling_preposition", "invalid", ""]),
        seed=master_seed_strategy,
    )
    def test_apply_grammar_rule_no_crash(self, text: str, stone: str, seed: int) -> None:
        """apply_grammar_rule should never crash."""
        try:
            result = engine.apply_grammar_rule(text, stone=stone, seed=seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(text=adversarial_text, seed=seed_strategy)
    def test_normalize_quote_pairs_no_crash(self, text: str, seed: int | None) -> None:
        """normalize_quote_pairs should never crash."""
        try:
            result = engine.normalize_quote_pairs(text, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass


# ===========================================================================
# Orchestration Operations Tests
# ===========================================================================


class TestOrchestrationOperations:
    """Fuzz tests for orchestration FFI operations."""

    @fuzz_settings
    @given(
        glitchlings=st.lists(
            st.fixed_dictionaries({
                "name": st.text(min_size=1, max_size=10),
                "scope": st.integers(min_value=0, max_value=5),
                "order": st.integers(min_value=0, max_value=5),
            }),
            min_size=0,
            max_size=5,
        ),
        master_seed=master_seed_strategy,
    )
    def test_plan_operations_no_crash(
        self, glitchlings: list[dict], master_seed: int
    ) -> None:
        """plan_operations should never crash."""
        try:
            result = engine.plan_operations(glitchlings, master_seed)
            assert isinstance(result, list)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(text=adversarial_text, master_seed=master_seed_strategy)
    def test_compose_operations_empty_no_crash(
        self, text: str, master_seed: int
    ) -> None:
        """compose_operations with empty descriptors should never crash."""
        try:
            result = engine.compose_operations(text, [], master_seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(text=adversarial_text, master_seed=master_seed_strategy)
    def test_compose_operations_valid_descriptor_no_crash(
        self, text: str, master_seed: int
    ) -> None:
        """compose_operations with a valid descriptor should never crash."""
        descriptor = {
            "name": "test_delete",
            "seed": 42,
            "operation": {"type": "delete", "rate": 0.1},
        }
        try:
            result = engine.compose_operations(text, [descriptor], master_seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(text=adversarial_text, master_seed=master_seed_strategy)
    def test_pipeline_empty_no_crash(self, text: str, master_seed: int) -> None:
        """Pipeline with empty descriptors should never crash."""
        try:
            pipeline = engine.Pipeline([], master_seed)
            result = pipeline.run(text)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        master_seed=master_seed_strategy,
        patterns=st.lists(st.text(min_size=0, max_size=10), min_size=0, max_size=3),
    )
    def test_pipeline_with_patterns_no_crash(
        self, text: str, master_seed: int, patterns: list[str]
    ) -> None:
        """Pipeline with pattern filtering should never crash."""
        try:
            pipeline = engine.Pipeline([], master_seed, patterns, patterns)
            result = pipeline.run(text)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass


# ===========================================================================
# Metrics Operations Tests
# ===========================================================================


class TestMetricsOperations:
    """Fuzz tests for metrics FFI operations."""

    @fuzz_settings
    @given(original=adversarial_text, corrupted=adversarial_text)
    def test_normalized_edit_distance_no_crash(
        self, original: str, corrupted: str
    ) -> None:
        """normalized_edit_distance should never crash."""
        try:
            result = engine.normalized_edit_distance(original, corrupted)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(original=adversarial_text, corrupted=adversarial_text)
    def test_subsequence_retention_no_crash(self, original: str, corrupted: str) -> None:
        """subsequence_retention should never crash."""
        try:
            result = engine.subsequence_retention(original, corrupted)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(
        original_tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=50),
        corrupted_tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=50),
    )
    def test_jensen_shannon_divergence_no_crash(
        self, original_tokens: list[int], corrupted_tokens: list[int]
    ) -> None:
        """jensen_shannon_divergence should never crash."""
        try:
            result = engine.jensen_shannon_divergence(original_tokens, corrupted_tokens)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(original=adversarial_text, corrupted=adversarial_text)
    def test_entropy_delta_no_crash(self, original: str, corrupted: str) -> None:
        """entropy_delta should never crash."""
        try:
            result = engine.entropy_delta(original, corrupted)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(original=adversarial_text, corrupted=adversarial_text)
    def test_merge_split_index_no_crash(self, original: str, corrupted: str) -> None:
        """merge_split_index should never crash."""
        try:
            result = engine.merge_split_index(original, corrupted)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass


# ===========================================================================
# Tokenizer Metrics Tests
# ===========================================================================


class TestTokenizerMetrics:
    """Fuzz tests for tokenizer-specific metrics."""

    @fuzz_settings
    @given(
        original_tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=30),
        corrupted_tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=30),
    )
    def test_compression_ratio_no_crash(
        self, original_tokens: list[int], corrupted_tokens: list[int]
    ) -> None:
        """compression_ratio should never crash."""
        try:
            result = engine.compression_ratio(original_tokens, corrupted_tokens)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(
        text=adversarial_text,
        tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=30),
    )
    def test_characters_per_token_no_crash(self, text: str, tokens: list[int]) -> None:
        """characters_per_token should never crash."""
        try:
            result = engine.characters_per_token(text, tokens)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=50))
    def test_token_entropy_no_crash(self, tokens: list[int]) -> None:
        """token_entropy should never crash."""
        try:
            result = engine.token_entropy(tokens)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(
        tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=50),
        vocab_size=st.integers(min_value=1, max_value=100000),
    )
    def test_vocabulary_utilization_no_crash(self, tokens: list[int], vocab_size: int) -> None:
        """vocabulary_utilization should never crash."""
        try:
            result = engine.vocabulary_utilization(tokens, vocab_size)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass

    @fuzz_settings
    @given(
        tokens=st.lists(st.integers(min_value=0, max_value=50000), max_size=50),
        unknown_token_id=st.integers(min_value=0, max_value=100000),
    )
    def test_unknown_token_rate_no_crash(self, tokens: list[int], unknown_token_id: int) -> None:
        """unknown_token_rate should never crash."""
        try:
            result = engine.unknown_token_rate(tokens, unknown_token_id)
            assert isinstance(result, float)
        except (ValueError, TypeError):
            pass


# ===========================================================================
# Pathological Regex Tests
# ===========================================================================


class TestPathologicalRegexPatterns:
    """Test that pathological regex patterns don't cause panics."""

    PATHOLOGICAL_PATTERNS = [
        "",
        "(",
        "[",
        "*",
        "((((((",
        "a{999999}",
        "(a+)+",  # ReDoS pattern
        "a" * 100,
        "\\",
    ]

    @fuzz_settings
    @given(pattern=st.sampled_from(PATHOLOGICAL_PATTERNS))
    def test_compose_with_pathological_patterns_no_crash(self, pattern: str) -> None:
        """compose_operations should handle pathological patterns without crashing."""
        try:
            result = engine.compose_operations("hello world", [], 42, [pattern], None)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(pattern=st.sampled_from(PATHOLOGICAL_PATTERNS))
    def test_pipeline_with_pathological_patterns_no_crash(self, pattern: str) -> None:
        """Pipeline should handle pathological patterns without crashing."""
        try:
            pipeline = engine.Pipeline([], 42, [pattern], [pattern])
            result = pipeline.run("hello world")
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass


# ===========================================================================
# Extreme Value Tests
# ===========================================================================


class TestExtremeValues:
    """Test extreme parameter values don't cause panics."""

    @fuzz_settings
    @given(
        rate=st.sampled_from([float("inf"), float("-inf"), float("nan"), 1e308, -1e308]),
    )
    def test_delete_words_extreme_rates(self, rate: float) -> None:
        """delete_random_words should handle extreme float values."""
        try:
            result = engine.delete_random_words("hello world", rate, False, 42)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass

    @fuzz_settings
    @given(seed=st.sampled_from([0, 2**64 - 1, 2**63, 2**63 - 1]))
    def test_operations_with_extreme_seeds(self, seed: int) -> None:
        """Operations should handle extreme seed values without overflow panics."""
        try:
            result = engine.delete_random_words("hello world", 0.1, False, seed)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError):
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-seed=0"])

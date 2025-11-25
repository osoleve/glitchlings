"""Tests for corrupt_dispatch.py pure functions.

These tests verify the pure dispatch functions work correctly without
invoking actual corruption. The dispatch logic should be fully testable
by examining the target structures produced.
"""

from __future__ import annotations

import pytest

from glitchlings.zoo.corrupt_dispatch import (
    StringCorruptionTarget,
    TranscriptCorruptionTarget,
    TranscriptTurnTarget,
    assemble_corruption_result,
    assemble_string_result,
    assemble_transcript_result,
    count_corruption_targets,
    extract_texts_to_corrupt,
    resolve_corruption_target,
    validate_text_input,
)


# ---------------------------------------------------------------------------
# Test Data
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_transcript():
    """A simple two-turn transcript."""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
    ]


@pytest.fixture
def multi_turn_transcript():
    """A multi-turn transcript for comprehensive testing."""
    return [
        {"role": "user", "content": "First user message"},
        {"role": "assistant", "content": "First assistant response"},
        {"role": "user", "content": "Second user message"},
        {"role": "assistant", "content": "Second assistant response"},
    ]


# ---------------------------------------------------------------------------
# StringCorruptionTarget Tests
# ---------------------------------------------------------------------------


class TestStringCorruptionTarget:
    """Tests for StringCorruptionTarget dataclass."""

    def test_creation(self) -> None:
        target = StringCorruptionTarget(text="Hello world")

        assert target.text == "Hello world"
        assert target.kind == "string"

    def test_frozen(self) -> None:
        target = StringCorruptionTarget(text="Hello")

        with pytest.raises(AttributeError):
            target.text = "Goodbye"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TranscriptTurnTarget Tests
# ---------------------------------------------------------------------------


class TestTranscriptTurnTarget:
    """Tests for TranscriptTurnTarget dataclass."""

    def test_creation(self) -> None:
        target = TranscriptTurnTarget(index=0, content="Hello")

        assert target.index == 0
        assert target.content == "Hello"

    def test_frozen(self) -> None:
        target = TranscriptTurnTarget(index=0, content="Hello")

        with pytest.raises(AttributeError):
            target.content = "Goodbye"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TranscriptCorruptionTarget Tests
# ---------------------------------------------------------------------------


class TestTranscriptCorruptionTarget:
    """Tests for TranscriptCorruptionTarget dataclass."""

    def test_creation(self, simple_transcript) -> None:
        turns = (TranscriptTurnTarget(index=1, content="I'm doing well"),)
        target = TranscriptCorruptionTarget(
            turns=turns,
            original_transcript=simple_transcript,
        )

        assert target.kind == "transcript"
        assert len(target.turns) == 1
        assert target.original_transcript == simple_transcript


# ---------------------------------------------------------------------------
# resolve_corruption_target Tests
# ---------------------------------------------------------------------------


class TestResolveCorruptionTarget:
    """Tests for resolve_corruption_target function."""

    def test_string_input(self) -> None:
        target = resolve_corruption_target("Hello world", "last")

        assert isinstance(target, StringCorruptionTarget)
        assert target.text == "Hello world"

    def test_transcript_last_target(self, simple_transcript) -> None:
        target = resolve_corruption_target(simple_transcript, "last")

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 1
        assert target.turns[0].index == 1
        assert target.turns[0].content == "I'm doing well, thank you!"

    def test_transcript_all_target(self, simple_transcript) -> None:
        target = resolve_corruption_target(simple_transcript, "all")

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 2
        assert target.turns[0].index == 0
        assert target.turns[1].index == 1

    def test_transcript_assistant_target(self, multi_turn_transcript) -> None:
        target = resolve_corruption_target(multi_turn_transcript, "assistant")

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 2
        assert all(
            multi_turn_transcript[turn.index]["role"] == "assistant" for turn in target.turns
        )

    def test_transcript_user_target(self, multi_turn_transcript) -> None:
        target = resolve_corruption_target(multi_turn_transcript, "user")

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 2
        assert all(multi_turn_transcript[turn.index]["role"] == "user" for turn in target.turns)

    def test_transcript_integer_index(self, multi_turn_transcript) -> None:
        target = resolve_corruption_target(multi_turn_transcript, 1)

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 1
        assert target.turns[0].index == 1

    def test_transcript_negative_index(self, multi_turn_transcript) -> None:
        target = resolve_corruption_target(multi_turn_transcript, -1)

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 1
        assert target.turns[0].index == 3  # Last index

    def test_transcript_index_list(self, multi_turn_transcript) -> None:
        target = resolve_corruption_target(multi_turn_transcript, [0, 2])

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 2
        assert target.turns[0].index == 0
        assert target.turns[1].index == 2

    def test_empty_transcript(self) -> None:
        target = resolve_corruption_target([], "last")

        assert isinstance(target, TranscriptCorruptionTarget)
        assert len(target.turns) == 0

    def test_list_of_strings_treated_as_string(self) -> None:
        """Lists that are not transcripts are cast to string for compatibility."""
        target = resolve_corruption_target(["alpha", "bravo"], "last")

        # For backwards compatibility, non-transcript lists are treated as strings
        assert isinstance(target, StringCorruptionTarget)
        assert target.text == "['alpha', 'bravo']"

    def test_non_string_non_transcript_treated_as_string(self) -> None:
        """Other types are cast to string for backwards compatibility."""
        target = resolve_corruption_target(12345, "last")  # type: ignore[arg-type]

        assert isinstance(target, StringCorruptionTarget)
        assert target.text == "12345"


# ---------------------------------------------------------------------------
# count_corruption_targets Tests
# ---------------------------------------------------------------------------


class TestCountCorruptionTargets:
    """Tests for count_corruption_targets function."""

    def test_string_target(self) -> None:
        target = StringCorruptionTarget(text="Hello")
        assert count_corruption_targets(target) == 1

    def test_transcript_target_single(self) -> None:
        turns = (TranscriptTurnTarget(index=0, content="Hello"),)
        target = TranscriptCorruptionTarget(turns=turns, original_transcript=[{"content": "Hello"}])
        assert count_corruption_targets(target) == 1

    def test_transcript_target_multiple(self) -> None:
        turns = (
            TranscriptTurnTarget(index=0, content="Hello"),
            TranscriptTurnTarget(index=1, content="World"),
        )
        target = TranscriptCorruptionTarget(
            turns=turns,
            original_transcript=[{"content": "Hello"}, {"content": "World"}],
        )
        assert count_corruption_targets(target) == 2


# ---------------------------------------------------------------------------
# extract_texts_to_corrupt Tests
# ---------------------------------------------------------------------------


class TestExtractTextsToCorrupt:
    """Tests for extract_texts_to_corrupt function."""

    def test_string_target(self) -> None:
        target = StringCorruptionTarget(text="Hello world")
        texts = extract_texts_to_corrupt(target)

        assert texts == ["Hello world"]

    def test_transcript_target(self) -> None:
        turns = (
            TranscriptTurnTarget(index=0, content="First"),
            TranscriptTurnTarget(index=1, content="Second"),
        )
        target = TranscriptCorruptionTarget(
            turns=turns,
            original_transcript=[{"content": "First"}, {"content": "Second"}],
        )
        texts = extract_texts_to_corrupt(target)

        assert texts == ["First", "Second"]


# ---------------------------------------------------------------------------
# assemble_string_result Tests
# ---------------------------------------------------------------------------


class TestAssembleStringResult:
    """Tests for assemble_string_result function."""

    def test_returns_corrupted_string(self) -> None:
        target = StringCorruptionTarget(text="Hello")
        result = assemble_string_result(target, "Corrupted")

        assert result == "Corrupted"


# ---------------------------------------------------------------------------
# assemble_transcript_result Tests
# ---------------------------------------------------------------------------


class TestAssembleTranscriptResult:
    """Tests for assemble_transcript_result function."""

    def test_updates_targeted_turns(self) -> None:
        original = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ]
        turns = (TranscriptTurnTarget(index=1, content="World"),)
        target = TranscriptCorruptionTarget(turns=turns, original_transcript=original)

        result = assemble_transcript_result(target, {1: "Corrupted"})

        assert result[0]["content"] == "Hello"  # Unchanged
        assert result[1]["content"] == "Corrupted"  # Updated

    def test_preserves_other_fields(self) -> None:
        original = [
            {"role": "user", "content": "Hello", "extra": "data"},
        ]
        turns = (TranscriptTurnTarget(index=0, content="Hello"),)
        target = TranscriptCorruptionTarget(turns=turns, original_transcript=original)

        result = assemble_transcript_result(target, {0: "Corrupted"})

        assert result[0]["extra"] == "data"
        assert result[0]["role"] == "user"

    def test_returns_deep_copy(self) -> None:
        original = [{"role": "user", "content": "Hello"}]
        turns = (TranscriptTurnTarget(index=0, content="Hello"),)
        target = TranscriptCorruptionTarget(turns=turns, original_transcript=original)

        result = assemble_transcript_result(target, {0: "Corrupted"})

        # Original should not be modified
        assert original[0]["content"] == "Hello"
        # Result should be different
        assert result[0]["content"] == "Corrupted"


# ---------------------------------------------------------------------------
# assemble_corruption_result Tests
# ---------------------------------------------------------------------------


class TestAssembleCorruptionResult:
    """Tests for assemble_corruption_result function."""

    def test_string_target(self) -> None:
        target = StringCorruptionTarget(text="Hello")
        result = assemble_corruption_result(target, "Corrupted")

        assert result == "Corrupted"

    def test_transcript_target(self) -> None:
        original = [{"role": "user", "content": "Hello"}]
        turns = (TranscriptTurnTarget(index=0, content="Hello"),)
        target = TranscriptCorruptionTarget(turns=turns, original_transcript=original)

        result = assemble_corruption_result(target, {0: "Corrupted"})

        assert isinstance(result, list)
        assert result[0]["content"] == "Corrupted"

    def test_string_target_with_wrong_type_raises(self) -> None:
        target = StringCorruptionTarget(text="Hello")

        with pytest.raises(TypeError, match="String target requires corrupted string"):
            assemble_corruption_result(target, {0: "Wrong"})  # type: ignore[arg-type]

    def test_transcript_target_with_wrong_type_raises(self) -> None:
        original = [{"role": "user", "content": "Hello"}]
        turns = (TranscriptTurnTarget(index=0, content="Hello"),)
        target = TranscriptCorruptionTarget(turns=turns, original_transcript=original)

        with pytest.raises(TypeError, match="Transcript target requires corrupted content"):
            assemble_corruption_result(target, "Wrong")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_text_input Tests
# ---------------------------------------------------------------------------


class TestValidateTextInput:
    """Tests for validate_text_input function."""

    def test_accepts_string(self) -> None:
        result = validate_text_input("Hello world")
        assert result == "Hello world"

    def test_accepts_transcript(self) -> None:
        transcript = [{"role": "user", "content": "Hello"}]
        result = validate_text_input(transcript)
        assert result == transcript

    def test_rejects_list_of_strings(self) -> None:
        with pytest.raises(TypeError, match="Expected string or transcript"):
            validate_text_input(["alpha", "bravo"])

    def test_rejects_invalid_type(self) -> None:
        with pytest.raises(TypeError, match="Expected string or transcript"):
            validate_text_input(12345)

    def test_rejects_none(self) -> None:
        with pytest.raises(TypeError, match="Expected string or transcript"):
            validate_text_input(None)

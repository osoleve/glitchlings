"""Tests for transcript_target functionality in Glitchling and Gaggle."""

from typing import Any

import pytest

from glitchlings import Gaggle, Glitchling, TranscriptTarget
from glitchlings.util.transcripts import resolve_transcript_indices
from glitchlings.zoo.core import AttackWave


class AppendBangGlitchling(Glitchling):
    """Simple glitchling that appends '!' to text for testing."""

    def __init__(
        self,
        name: str = "AppendBang",
        transcript_target: TranscriptTarget = "last",
    ):
        super().__init__(
            name,
            self._corrupt,
            AttackWave.WORD,
            transcript_target=transcript_target,
        )

    def _corrupt(self, text: str, **kwargs: Any) -> str:
        return text + "!"


class TestResolveTranscriptIndices:
    """Tests for the resolve_transcript_indices utility function."""

    def test_last_returns_final_index(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
        assert resolve_transcript_indices(transcript, "last") == [2]

    def test_all_returns_all_indices(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
        assert resolve_transcript_indices(transcript, "all") == [0, 1, 2]

    def test_assistant_filters_by_role(self) -> None:
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
            {"role": "assistant", "content": "goodbye"},
        ]
        assert resolve_transcript_indices(transcript, "assistant") == [1, 3]

    def test_user_filters_by_role(self) -> None:
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        assert resolve_transcript_indices(transcript, "user") == [0, 2]

    def test_integer_index_works(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
        assert resolve_transcript_indices(transcript, 1) == [1]

    def test_negative_index_works(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
        assert resolve_transcript_indices(transcript, -1) == [2]
        assert resolve_transcript_indices(transcript, -2) == [1]

    def test_sequence_of_indices_works(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
        assert resolve_transcript_indices(transcript, [0, 2]) == [0, 2]

    def test_sequence_deduplicates_and_sorts(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
        assert resolve_transcript_indices(transcript, [2, 0, 2, 1]) == [0, 1, 2]

    def test_empty_transcript_returns_empty(self) -> None:
        assert resolve_transcript_indices([], "last") == []
        assert resolve_transcript_indices([], "all") == []
        assert resolve_transcript_indices([], "assistant") == []

    def test_index_out_of_bounds_raises(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}]
        with pytest.raises(ValueError, match="out of bounds"):
            resolve_transcript_indices(transcript, 5)

    def test_negative_index_out_of_bounds_raises(self) -> None:
        transcript = [{"content": "a"}, {"content": "b"}]
        with pytest.raises(ValueError, match="out of bounds"):
            resolve_transcript_indices(transcript, -5)

    def test_invalid_target_raises(self) -> None:
        transcript = [{"content": "a"}]
        with pytest.raises(ValueError, match="Invalid transcript target"):
            resolve_transcript_indices(transcript, "invalid")  # type: ignore[arg-type]

    def test_sequence_with_non_int_raises(self) -> None:
        transcript = [{"content": "a"}]
        with pytest.raises(ValueError, match="must be integers"):
            resolve_transcript_indices(transcript, [0, "bad"])  # type: ignore[list-item]


class TestGlitchlingTranscriptTarget:
    """Tests for transcript_target in the base Glitchling class."""

    def test_default_corrupts_last_turn(self) -> None:
        glitchling = AppendBangGlitchling()
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = glitchling.corrupt(transcript)
        assert result[0]["content"] == "hi"
        assert result[1]["content"] == "hello!"

    def test_all_corrupts_every_turn(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target="all")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = glitchling.corrupt(transcript)
        assert result[0]["content"] == "hi!"
        assert result[1]["content"] == "hello!"

    def test_assistant_corrupts_only_assistant_turns(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target="assistant")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        result = glitchling.corrupt(transcript)
        assert result[0]["content"] == "hi"
        assert result[1]["content"] == "hello!"
        assert result[2]["content"] == "bye"

    def test_user_corrupts_only_user_turns(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target="user")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        result = glitchling.corrupt(transcript)
        assert result[0]["content"] == "hi!"
        assert result[1]["content"] == "hello"
        assert result[2]["content"] == "bye!"

    def test_integer_index_corrupts_specific_turn(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target=0)
        transcript = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]
        result = glitchling.corrupt(transcript)
        assert result[0]["content"] == "first!"
        assert result[1]["content"] == "second"

    def test_negative_index_corrupts_from_end(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target=-2)
        transcript = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "third"},
        ]
        result = glitchling.corrupt(transcript)
        assert result[0]["content"] == "first"
        assert result[1]["content"] == "second!"
        assert result[2]["content"] == "third"

    def test_index_list_corrupts_multiple_turns(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target=[0, 2])
        transcript = [
            {"content": "a"},
            {"content": "b"},
            {"content": "c"},
        ]
        result = glitchling.corrupt(transcript)
        assert result[0]["content"] == "a!"
        assert result[1]["content"] == "b"
        assert result[2]["content"] == "c!"

    def test_string_input_ignores_transcript_target(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target="all")
        result = glitchling.corrupt("hello")
        assert result == "hello!"

    def test_clone_preserves_transcript_target(self) -> None:
        glitchling = AppendBangGlitchling(transcript_target="assistant")
        clone = glitchling.clone()
        assert clone.transcript_target == "assistant"


class TestGaggleTranscriptTarget:
    """Tests for transcript_target in the Gaggle class."""

    def test_default_corrupts_last_turn(self) -> None:
        gaggle = Gaggle([AppendBangGlitchling()])
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = gaggle.corrupt(transcript)
        assert result[0]["content"] == "hi"
        assert result[1]["content"] == "hello!"

    def test_all_corrupts_every_turn(self) -> None:
        gaggle = Gaggle([AppendBangGlitchling()], transcript_target="all")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = gaggle.corrupt(transcript)
        assert result[0]["content"] == "hi!"
        assert result[1]["content"] == "hello!"

    def test_assistant_corrupts_only_assistant_turns(self) -> None:
        gaggle = Gaggle([AppendBangGlitchling()], transcript_target="assistant")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        result = gaggle.corrupt(transcript)
        assert result[0]["content"] == "hi"
        assert result[1]["content"] == "hello!"
        assert result[2]["content"] == "bye"

    def test_user_corrupts_only_user_turns(self) -> None:
        gaggle = Gaggle([AppendBangGlitchling()], transcript_target="user")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        result = gaggle.corrupt(transcript)
        assert result[0]["content"] == "hi!"
        assert result[1]["content"] == "hello"
        assert result[2]["content"] == "bye!"

    def test_gaggle_applies_full_pipeline_to_each_target_turn(self) -> None:
        # Two glitchlings that both append something
        gaggle = Gaggle(
            [AppendBangGlitchling("g1"), AppendBangGlitchling("g2")],
            transcript_target="all",
        )
        transcript = [{"content": "a"}, {"content": "b"}]
        result = gaggle.corrupt(transcript)
        # Each turn gets both glitchlings applied = two bangs
        assert result[0]["content"] == "a!!"
        assert result[1]["content"] == "b!!"

    def test_empty_transcript_returns_empty(self) -> None:
        gaggle = Gaggle([AppendBangGlitchling()], transcript_target="all")
        result = gaggle.corrupt([])
        assert result == []

    def test_string_input_ignores_transcript_target(self) -> None:
        gaggle = Gaggle([AppendBangGlitchling()], transcript_target="all")
        result = gaggle.corrupt("hello")
        assert result == "hello!"


class TestAttackTranscriptTarget:
    """Tests for transcript_target in the Attack class."""

    def test_attack_with_transcript_target_all(self) -> None:
        from glitchlings.attack import Attack

        attack = Attack([AppendBangGlitchling()], transcript_target="all")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = attack.run(transcript)
        assert result.corrupted[0]["content"] == "hi!"
        assert result.corrupted[1]["content"] == "hello!"

    def test_attack_default_corrupts_last_turn(self) -> None:
        from glitchlings.attack import Attack

        attack = Attack([AppendBangGlitchling()])
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = attack.run(transcript)
        assert result.corrupted[0]["content"] == "hi"
        assert result.corrupted[1]["content"] == "hello!"

    def test_attack_with_transcript_target_assistant(self) -> None:
        from glitchlings.attack import Attack

        attack = Attack([AppendBangGlitchling()], transcript_target="assistant")
        transcript = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        result = attack.run(transcript)
        assert result.corrupted[0]["content"] == "hi"
        assert result.corrupted[1]["content"] == "hello!"
        assert result.corrupted[2]["content"] == "bye"

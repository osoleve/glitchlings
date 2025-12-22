from __future__ import annotations

from glitchlings.zoo.core import Gaggle
from glitchlings.zoo.rushmore import Rushmore
from glitchlings.zoo.typogre import Typogre


def test_exclude_patterns_preserve_html_tokens() -> None:
    text = "alpha <br> beta"
    gaggle = Gaggle(
        [Rushmore(modes="duplicate", rate=1.0, seed=2)],
        seed=11,
        exclude_patterns=[r"<br>"],
    )

    result = gaggle.corrupt(text)

    assert "<br>" in result
    assert result.count("<br>") == text.count("<br>")
    assert result.count("alpha") >= 2
    assert result.count("beta") >= 2


def test_include_only_patterns_limit_scope() -> None:
    text = "intro `code block` outro"
    gaggle = Gaggle(
        [Typogre(rate=1.0, seed=5)],
        seed=7,
        include_only_patterns=[r"`[^`]+`"],
    )

    result = gaggle.corrupt(text)

    assert result.startswith("intro ")
    assert result.endswith(" outro")
    assert result != text
    inner = result[result.index("`") : result.rindex("`") + 1]
    assert inner != "`code block`"


def test_glitchlings_skip_immutable_segments() -> None:
    text = "alpha STATIC omega"
    gaggle = Gaggle(
        [
            Typogre(rate=1.0, seed=3),
            Rushmore(modes="duplicate", rate=1.0, seed=5),
        ],
        seed=13,
        exclude_patterns=[r"STATIC"],
    )

    result = gaggle.corrupt(text)

    assert "STATIC" in result
    assert result.count("STATIC") == 1
    assert result != text
    assert len(result.split()) > len(text.split())


# --- Heterogeneous mask tests ---


def test_heterogeneous_masks_detected() -> None:
    """Verify that glitchlings with different masks are detected as heterogeneous."""
    typo_a = Typogre(rate=0.1, exclude_patterns=[r"<a>"])
    typo_b = Typogre(rate=0.1, exclude_patterns=[r"<b>"])
    gaggle = Gaggle([typo_a, typo_b], seed=1)

    assert gaggle._has_heterogeneous_masks() is True


def test_homogeneous_masks_not_flagged() -> None:
    """Verify that identical masks are not flagged as heterogeneous."""
    typo_a = Typogre(rate=0.1, exclude_patterns=[r"<tag>"])
    typo_b = Typogre(rate=0.2, exclude_patterns=[r"<tag>"])  # Different rate, same mask
    gaggle = Gaggle([typo_a, typo_b], seed=1)

    assert gaggle._has_heterogeneous_masks() is False


def test_no_masks_is_homogeneous() -> None:
    """Glitchlings with no masks are considered homogeneous."""
    typo_a = Typogre(rate=0.1)
    typo_b = Typogre(rate=0.2)
    gaggle = Gaggle([typo_a, typo_b], seed=1)

    assert gaggle._has_heterogeneous_masks() is False


def test_heterogeneous_masks_independent_targets() -> None:
    """Test that glitchlings with different include_only patterns target independently."""
    text = "PREFIX FIRST MIDDLE SECOND SUFFIX"

    typo_first = Typogre(
        rate=1.0,
        seed=1,
        include_only_patterns=[r"FIRST"],
    )

    typo_second = Typogre(
        rate=1.0,
        seed=2,
        include_only_patterns=[r"SECOND"],
    )

    gaggle = Gaggle([typo_first, typo_second], seed=100)
    result = gaggle.corrupt(text)

    # Untargeted regions should be unchanged
    assert "PREFIX" in result
    assert "MIDDLE" in result
    assert "SUFFIX" in result

    # Targeted regions should be corrupted
    assert "FIRST" not in result
    assert "SECOND" not in result


def test_heterogeneous_masks_with_gaggle_level_exclude() -> None:
    """Test per-glitchling masks combined with Gaggle-level excludes."""
    text = "GLOBAL: A-REGION B-REGION END"

    typo_a = Typogre(
        rate=1.0,
        seed=1,
        include_only_patterns=[r"A-REGION"],
    )

    typo_b = Typogre(
        rate=1.0,
        seed=2,
        include_only_patterns=[r"B-REGION"],
    )

    gaggle = Gaggle(
        [typo_a, typo_b],
        seed=100,
        exclude_patterns=[r"GLOBAL:"],  # Gaggle-level exclusion
    )

    result = gaggle.corrupt(text)

    # Gaggle-level excluded region should be unchanged
    assert "GLOBAL:" in result
    # Regions outside all include patterns should be unchanged
    assert "END" in result
    # Targeted regions should be corrupted
    assert "A-REGION" not in result
    assert "B-REGION" not in result


def test_group_by_masks_creates_correct_groups() -> None:
    """Test that consecutive glitchlings with same masks are batched."""
    typo_a = Typogre(rate=0.1, exclude_patterns=[r"<a>"])
    typo_b = Typogre(rate=0.1, exclude_patterns=[r"<a>"])  # Same as a
    typo_c = Typogre(rate=0.1, exclude_patterns=[r"<c>"])  # Different
    typo_d = Typogre(rate=0.1, exclude_patterns=[r"<c>"])  # Same as c
    gaggle = Gaggle([typo_a, typo_b, typo_c, typo_d], seed=1)

    groups = gaggle._group_by_masks()

    # Should have 2 groups: [typo_a, typo_b] and [typo_c, typo_d]
    assert len(groups) == 2
    assert len(groups[0][2]) == 2  # First group has 2 glitchlings
    assert len(groups[1][2]) == 2  # Second group has 2 glitchlings

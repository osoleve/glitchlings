from __future__ import annotations

from glitchlings.zoo.core import Gaggle
from glitchlings.zoo.rushmore import Rushmore
from glitchlings.zoo.typogre import Typogre


def test_excluded_spans_are_byte_identical() -> None:
    text = "alpha <system>DO_NOT_TOUCH</system> omega"
    gaggle = Gaggle(
        [Rushmore(modes="duplicate", rate=1.0, seed=3)],
        seed=11,
        exclude_patterns=[r"<system>.*?</system>"],
    )

    result = gaggle.corrupt(text)

    assert "<system>DO_NOT_TOUCH</system>" in result
    assert result.count("DO_NOT_TOUCH") == 1
    assert result != text


def test_include_only_masks_external_text() -> None:
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


def test_tag_boundaries_split_mutation_regions() -> None:
    text = "pre<tag>frozen</tag>post"
    gaggle = Gaggle(
        [Rushmore(modes="duplicate", rate=1.0, seed=9)],
        seed=15,
        exclude_patterns=[r"<tag>.*?</tag>"],
    )

    result = gaggle.corrupt(text)

    assert "<tag>frozen</tag>" in result
    assert result.count("frozen") == 1
    assert "pre" in result
    assert "post" in result

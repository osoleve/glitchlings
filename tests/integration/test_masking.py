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

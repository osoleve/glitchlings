from collections.abc import Sequence

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from glitchlings.auggie import Auggie
from glitchlings.util import KEYNEIGHBORS
from glitchlings.zoo import (
    Ekkokin,
    Gaggle,
    Glitchling,
    Hokey,
    Jargoyle,
    Mim1c,
    Pedant,
    Redactyl,
    Rushmore,
    RushmoreMode,
    Scannequin,
    Typogre,
    Zeedub,
)
from glitchlings.zoo.pedant.stones import PedantStone


def _default_keyboard_name() -> str:
    if hasattr(KEYNEIGHBORS, "CURATOR_QWERTY"):
        return "CURATOR_QWERTY"

    for name in vars(KEYNEIGHBORS):
        if not name.startswith("_"):
            return name

    raise RuntimeError("No keyboard layouts registered for Typogre tests")


def _available_glitchling_cases() -> list[tuple[str, type[Glitchling], dict[str, object]]]:
    cases: list[tuple[str, type[Glitchling], dict[str, object]]] = [
        (
            "typo",
            Typogre,
            {
                "rate": 0.05,
                "keyboard": _default_keyboard_name(),
                "seed": 11,
            },
        ),
        (
            "confusable",
            Mim1c,
            {
                "rate": 0.03,
                "classes": ["LATIN", "GREEK"],
                "banned_characters": ["a", "o"],
                "seed": 17,
            },
        ),
        (
            "curly_quotes",
            Pedant,
            {"stone": PedantStone.CURLITE, "seed": 19},
        ),
        (
            "stretch",
            Hokey,
            {
                "rate": 0.2,
                "extension_min": 1,
                "extension_max": 3,
                "word_length_threshold": 4,
                "base_p": 0.35,
                "seed": 23,
            },
        ),
        (
            "homophone",
            Ekkokin,
            {
                "rate": 0.04,
                "seed": 29,
            },
        ),
        (
            "pedantry",
            Pedant,
            {"stone": PedantStone.OXFORDIUM, "seed": 31},
        ),
        (
            "remix",
            Rushmore,
            {
                "modes": [RushmoreMode.DELETE, RushmoreMode.SWAP],
                "rate": 0.1,
                "delete_rate": 0.2,
                "duplicate_rate": 0.05,
                "swap_rate": 0.15,
                "seed": 37,
                "unweighted": True,
                "delete_unweighted": True,
                "duplicate_unweighted": False,
            },
        ),
        (
            "redact",
            Redactyl,
            {
                "replacement_char": "#",
                "rate": 0.1,
                "merge_adjacent": True,
                "seed": 47,
                "unweighted": True,
            },
        ),
        (
            "recolor",
            Jargoyle,
            {
                "lexemes": "colors",
                "mode": "drift",
                "rate": 1.0,
                "seed": 53,
            },
        ),
        (
            "ocr",
            Scannequin,
            {
                "rate": 0.03,
                "seed": 59,
            },
        ),
        (
            "zero_width",
            Zeedub,
            {
                "rate": 0.15,
                "characters": ["\u200b", "\u2060"],
                "seed": 61,
            },
        ),
        (
            "drift",
            Jargoyle,
            {
                "lexemes": "synonyms",
                "mode": "drift",
                "rate": 0.02,
                "seed": 67,
            },
        ),
    ]

    return cases


GLITCHLING_CASES = _available_glitchling_cases()


_MANUAL_DEFAULTS: dict[str, dict[str, object]] = {
    "curly_quotes": {"stone": PedantStone.CURLITE},
    "drift": {"lexemes": "synonyms"},
    "recolor": {"lexemes": "colors", "rate": 1.0},
}


@pytest.mark.parametrize("method_name, glitchling_cls, params", GLITCHLING_CASES)
def test_auggie_builder_matches_glitchling_factory(
    method_name: str, glitchling_cls: type[Glitchling], params: dict[str, object]
) -> None:
    auggie = Auggie(seed=101)
    builder = getattr(auggie, method_name)
    builder_kwargs = dict(params)
    if method_name == "curly_quotes":
        builder_kwargs.pop("stone", None)
    if method_name == "recolor":
        # recolor only accepts mode and seed; it sets lexemes="colors" and rate=1.0 internally
        builder_kwargs.pop("lexemes", None)
        builder_kwargs.pop("rate", None)
    result = builder(**builder_kwargs)

    assert result is auggie
    assert len(auggie._clones_by_index) == 1  # type: ignore[attr-defined]
    assert len(auggie._blueprint) == 1  # type: ignore[attr-defined]

    expected = glitchling_cls(**params)
    blueprint_entry = auggie._blueprint[-1]  # type: ignore[attr-defined]

    assert type(blueprint_entry) is type(expected)

    actual_kwargs = dict(blueprint_entry.kwargs)
    expected_kwargs = dict(expected.kwargs)

    assert actual_kwargs == expected_kwargs
    assert blueprint_entry.seed == expected.seed


@settings(suppress_health_check=[HealthCheck.too_slow])
def _auggie_sequence_strategy() -> st.SearchStrategy[list[str]]:
    names = [entry[0] for entry in GLITCHLING_CASES]
    if not names:
        return st.just([])
    return st.lists(st.sampled_from(names), max_size=5)


@given(
    sequence=_auggie_sequence_strategy(),
    text=st.text(min_size=0, max_size=50),
    seed=st.integers(min_value=0, max_value=10_000),
)
def test_auggie_matches_gaggle_output(sequence: Sequence[str], text: str, seed: int) -> None:
    auggie = Auggie(seed=seed)
    manual_glitchlings = []

    for name in sequence:
        builder = getattr(auggie, name)
        builder()
        _, glitchling_cls, _ = next(entry for entry in GLITCHLING_CASES if entry[0] == name)
        manual_kwargs = dict(_MANUAL_DEFAULTS.get(name, {}))
        manual_glitchlings.append(glitchling_cls(**manual_kwargs))

    manual = Gaggle(manual_glitchlings, seed=seed)

    try:
        auggie_result = auggie.corrupt(text)
        auggie_error: Exception | None = None
    except Exception as exc:  # noqa: BLE001
        auggie_result = None
        auggie_error = exc

    try:
        manual_result = manual.corrupt(text)
        manual_error: Exception | None = None
    except Exception as exc:  # noqa: BLE001
        manual_result = None
        manual_error = exc

    if auggie_error or manual_error:
        assert type(auggie_error) is type(manual_error)
        if auggie_error is not None and manual_error is not None:
            assert str(auggie_error) == str(manual_error)
    else:
        assert auggie_result == manual_result

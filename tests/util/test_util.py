import pytest

from glitchlings.zoo.transforms import compute_string_diffs as string_diffs


def test_string_diffs_groups_consecutive_edits_and_skips_equals():
    result = string_diffs("kitten", "sitting")

    assert result == [
        [("replace", "k", "s")],
        [("replace", "e", "i")],
        [("insert", "", "g")],
    ]

    for group in result:
        assert group
        assert all(tag != "equal" for tag, *_ in group)


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("flaw", "lawn", [[("delete", "f", "")], [("insert", "", "n")]]),
        (
            "distance",
            "instance",
            [
                [("delete", "d", "")],
                [("insert", "", "n")],
            ],
        ),
    ],
)
def test_string_diffs_handles_multiple_edit_groups(
    a: str, b: str, expected: list[list[tuple[str, str, str]]]
) -> None:
    assert string_diffs(a, b) == expected

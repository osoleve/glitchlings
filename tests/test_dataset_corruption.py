import random

from datasets import Dataset

from glitchlings.zoo.core import AttackWave, Glitchling


def append_rng_token(text: str, *, rng: random.Random) -> str:
    """Append a deterministic RNG token to the supplied text."""

    return f"{text}-{rng.randint(0, 999)}"


def test_corrupt_dataset_is_deterministic_across_columns() -> None:
    dataset = Dataset.from_dict(
        {
            "text": ["alpha", "beta"],
            "summary": ["one", "two"],
            "label": [0, 1],
        }
    )

    glitchling = Glitchling(
        "rngster",
        append_rng_token,
        AttackWave.SENTENCE,
        seed=1337,
    )

    corrupted = glitchling.corrupt_dataset(dataset, ["text", "summary"])
    materialized_rows = list(corrupted)

    glitchling.reset_rng(1337)
    rematerialized_rows = list(glitchling.corrupt_dataset(dataset, ["text", "summary"]))

    assert materialized_rows == rematerialized_rows

    expected_rng = random.Random(1337)
    expected_rows = []
    for original_row in dataset:
        row = dict(original_row)
        for column in ("text", "summary"):
            row[column] = f"{original_row[column]}-{expected_rng.randint(0, 999)}"
        expected_rows.append(row)

    assert materialized_rows == expected_rows

    for idx, row in enumerate(materialized_rows):
        assert row["label"] == dataset[idx]["label"]

    assert corrupted.column_names == dataset.column_names

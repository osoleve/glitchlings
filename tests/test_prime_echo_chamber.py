from __future__ import annotations

from datasets import Dataset

from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling


def append_marker(text: str) -> str:
    """Deterministically mark the supplied text."""

    return f"{text} :: corrupted"


def test_prime_echo_chamber_prompt_corruption_is_stable() -> None:
    """Repeated dataset corruption should not compound transcript changes."""

    base_transcript = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Compute 2+2."},
    ]

    dataset = Dataset.from_dict({"prompt": [base_transcript], "id": [0]})

    glitchling = Glitchling("marker", append_marker, AttackWave.SENTENCE)
    gaggle = Gaggle([glitchling], seed=7)

    first_pass = list(gaggle.corrupt_dataset(dataset, ["prompt"]))
    second_pass = list(gaggle.corrupt_dataset(dataset, ["prompt"]))

    assert first_pass == second_pass
    assert first_pass[0]["prompt"][-1]["content"] == "Compute 2+2. :: corrupted"
    assert base_transcript[-1]["content"] == "Compute 2+2."

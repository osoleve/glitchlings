from datasets import Dataset

from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling


def append_marker(text: str) -> str:
    """Tag the provided text with a deterministic marker."""

    return f"{text}<<<"


def test_conversational_prompts_remain_structured() -> None:
    dataset = Dataset.from_dict(
        {
            "prompt": [
                [
                    {"role": "system", "content": "Restore the text."},
                    {"role": "user", "content": "coRRuPt3d"},
                ]
            ]
        }
    )

    glitchling = Glitchling("marker", append_marker, AttackWave.SENTENCE)
    gaggle = Gaggle([glitchling], seed=99)

    corrupted_rows = list(gaggle.corrupt_dataset(dataset, ["prompt"]))

    assert len(corrupted_rows) == 1
    prompt = corrupted_rows[0]["prompt"]

    assert isinstance(prompt, list)
    assert prompt[0] == {"role": "system", "content": "Restore the text."}
    assert prompt[1]["role"] == "user"
    assert prompt[1]["content"] == "coRRuPt3d<<<"

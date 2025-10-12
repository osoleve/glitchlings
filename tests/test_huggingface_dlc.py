from collections.abc import Iterable
from random import Random

import pytest

datasets = pytest.importorskip("datasets")
Dataset = datasets.Dataset

from glitchlings.dlc import huggingface as hf_dlc
from glitchlings.dlc.huggingface import _normalise_columns
from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling


def append_rng_token(text: str, *, rng: Random) -> str:
    """Append a deterministic RNG token to the supplied text."""

    return f"{text}-{rng.randint(0, 999)}"


@pytest.fixture(autouse=True)
def ensure_glitch_installed() -> Iterable[None]:
    hf_dlc.install()
    yield


def test_normalise_columns_rejects_empty_sequence() -> None:
    with pytest.raises(ValueError, match="At least one column"):
        _normalise_columns([])


def test_install_is_idempotent() -> None:
    hf_dlc.install()
    assert hasattr(Dataset, "glitch")


def test_module_exports_dataset_with_glitch_method() -> None:
    assert hf_dlc.Dataset is Dataset

    dataset = hf_dlc.Dataset.from_dict({"text": ["alpha"]})
    result = list(dataset.glitch("typogre", column="text"))

    assert len(result) == 1


def test_dataset_glitch_accepts_gaggle() -> None:
    dataset = Dataset.from_dict({"text": ["alpha", "beta"], "label": [0, 1]})
    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=1337)
    gaggle = Gaggle([glitchling], seed=99)

    corrupted = dataset.glitch(gaggle, column="text")

    comparison_gaggle = Gaggle([glitchling.clone()], seed=99)
    expected = list(comparison_gaggle.corrupt_dataset(dataset, ["text"]))
    assert list(corrupted) == expected
    assert list(dataset)[0]["text"] == "alpha"


def test_dataset_glitch_accepts_names_and_respects_seed() -> None:
    dataset = Dataset.from_dict({"text": ["alpha", "beta"]})

    corrupted = list(dataset.glitch("typogre", column="text", seed=42))
    rerun = list(dataset.glitch(["Typogre"], column="text", seed=42))

    assert corrupted == rerun

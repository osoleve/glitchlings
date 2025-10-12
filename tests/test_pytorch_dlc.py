from collections.abc import Iterable
from random import Random

import pytest

torch = pytest.importorskip("torch")
from torch.utils.data import DataLoader, Dataset

from glitchlings.dlc import pytorch as torch_dlc
from glitchlings.dlc.pytorch import _normalise_columns
from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling


class SimpleDataset(Dataset):
    """Minimal dataset returning dictionaries for collation."""

    def __init__(self) -> None:
        self._rows = [
            {"text": "alpha", "label": 0},
            {"text": "beta", "label": 1},
            {"text": "gamma", "label": 2},
        ]

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index: int) -> dict[str, object]:
        return dict(self._rows[index])


def append_rng_token(text: str, *, rng: Random) -> str:
    """Append a deterministic RNG token to the supplied text."""

    return f"{text}-{rng.randint(0, 999)}"


@pytest.fixture(autouse=True)
def ensure_glitch_installed() -> Iterable[None]:
    torch_dlc.install()
    yield


def test_normalise_columns_rejects_empty_sequence() -> None:
    with pytest.raises(ValueError, match="At least one column"):
        _normalise_columns([])


def test_install_is_idempotent() -> None:
    torch_dlc.install()
    assert hasattr(DataLoader, "glitch")


def test_module_exports_dataloader_with_glitch_method() -> None:
    assert torch_dlc.DataLoader is DataLoader

    dataset = SimpleDataset()
    loader = torch_dlc.DataLoader(dataset, batch_size=2, shuffle=False)
    result = list(loader.glitch("typogre", column="text"))

    assert len(result) == 2


def test_dataloader_glitch_accepts_gaggle() -> None:
    dataset = SimpleDataset()
    loader = DataLoader(dataset, batch_size=2, shuffle=False)
    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=1337)
    gaggle = Gaggle([glitchling], seed=99)

    corrupted = list(loader.glitch(gaggle, column="text"))

    comparison_loader = DataLoader(dataset, batch_size=2, shuffle=False)
    comparison_gaggle = Gaggle([glitchling.clone()], seed=99)
    expected = []
    for batch in comparison_loader:
        comparison_batch = dict(batch)
        comparison_batch["text"] = [
            comparison_gaggle.corrupt(item) for item in list(batch["text"])
        ]
        expected.append(comparison_batch)

    assert corrupted == expected

    original_rows = list(DataLoader(dataset, batch_size=2, shuffle=False))
    assert original_rows[0]["text"][0] == "alpha"


def test_dataloader_glitch_accepts_names_and_respects_seed() -> None:
    dataset = SimpleDataset()
    loader = DataLoader(dataset, batch_size=1, shuffle=False)

    corrupted = list(loader.glitch("typogre", column="text", seed=42))
    rerun = list(loader.glitch(["Typogre"], column="text", seed=42))

    assert corrupted == rerun

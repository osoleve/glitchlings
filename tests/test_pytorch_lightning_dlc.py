from collections.abc import Iterable
from random import Random

import pytest

torch = pytest.importorskip("torch")
pl = pytest.importorskip("pytorch_lightning")
from torch.utils.data import DataLoader, Dataset

from glitchlings.dlc import pytorch as torch_dlc
from glitchlings.dlc import pytorch_lightning as lightning_dlc
from glitchlings.dlc.pytorch_lightning import _normalise_loaders
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


class SimpleLightningDataModule(pl.LightningDataModule):
    """Lightning data module returning multiple dataloader structures."""

    def __init__(self) -> None:
        super().__init__()
        self.dataset = SimpleDataset()
        self.batch_size = 2

    def train_dataloader(self) -> DataLoader:
        return DataLoader(self.dataset, batch_size=self.batch_size, shuffle=False)

    def val_dataloader(self) -> DataLoader:
        return DataLoader(self.dataset, batch_size=1, shuffle=False)

    def test_dataloader(self) -> list[DataLoader]:
        return [
            DataLoader(self.dataset, batch_size=1, shuffle=False),
            DataLoader(self.dataset, batch_size=3, shuffle=False),
        ]

    def predict_dataloader(self) -> dict[str, DataLoader]:
        return {
            "predict": DataLoader(self.dataset, batch_size=3, shuffle=False),
        }


def append_rng_token(text: str, *, rng: Random) -> str:
    """Append a deterministic RNG token to the supplied text."""

    return f"{text}-{rng.randint(0, 999)}"


@pytest.fixture(autouse=True)
def ensure_glitch_installed() -> Iterable[None]:
    torch_dlc.install()
    lightning_dlc.install()
    yield


def test_normalise_loaders_rejects_empty_sequence() -> None:
    with pytest.raises(ValueError, match="At least one dataloader"):
        _normalise_loaders([])


def test_install_is_idempotent() -> None:
    lightning_dlc.install()
    assert hasattr(pl.LightningDataModule, "glitch")


def test_datamodule_glitch_accepts_gaggle_and_respects_seed() -> None:
    datamodule = SimpleLightningDataModule()
    glitchling = Glitchling("rngster", append_rng_token, AttackWave.SENTENCE, seed=1337)
    gaggle = Gaggle([glitchling], seed=99)

    glitched = datamodule.glitch(gaggle, column="text", seed=11, loaders="train")
    rerun = datamodule.glitch([glitchling.clone()], column="text", seed=11, loaders=["train"])

    train_batches = list(glitched.train_dataloader())
    rerun_batches = list(rerun.train_dataloader())

    assert train_batches == rerun_batches

    original_batches = list(datamodule.train_dataloader())
    assert original_batches[0]["text"][0] == "alpha"

    # val dataloader not requested for glitching should remain pristine
    glitched_val = list(glitched.val_dataloader())
    original_val = list(datamodule.val_dataloader())
    assert glitched_val == original_val


def test_datamodule_glitch_applies_to_all_supported_hooks() -> None:
    datamodule = SimpleLightningDataModule()
    glitched = datamodule.glitch("typogre", column="text")

    train_batch = next(iter(glitched.train_dataloader()))
    assert train_batch["text"][0] != "alpha"

    val_batch = next(iter(glitched.val_dataloader()))
    assert val_batch["text"][0] != "alpha"

    test_loaders = glitched.test_dataloader()
    assert isinstance(test_loaders, list)
    test_batch = next(iter(test_loaders[0]))
    assert test_batch["text"][0] != "alpha"

    predict_loaders = glitched.predict_dataloader()
    assert "predict" in predict_loaders
    predict_batch = next(iter(predict_loaders["predict"]))
    assert predict_batch["text"][0] != "alpha"

    # proxy should expose attributes from the underlying datamodule
    assert glitched.batch_size == datamodule.batch_size

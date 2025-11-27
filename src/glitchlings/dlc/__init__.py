"""Optional DLC integrations for Glitchlings.

This module provides explicit wrapper classes for integrating glitchlings
with popular ML frameworks:

- :class:`~glitchlings.dlc.huggingface.GlitchedDataset`: Wrap Hugging Face datasets
- :class:`~glitchlings.dlc.pytorch.GlitchedDataLoader`: Wrap PyTorch data loaders
- :class:`~glitchlings.dlc.pytorch_lightning.GlitchedLightningDataModule`: Wrap
  Lightning data modules
- :class:`~glitchlings.dlc.gutenberg.GlitchenbergAPI`: Wrap Project Gutenberg API

Example:
    >>> from glitchlings.dlc.huggingface import GlitchedDataset
    >>> from datasets import Dataset
    >>> dataset = Dataset.from_dict({"text": ["hello", "world"]})
    >>> corrupted = GlitchedDataset(dataset, "typogre", column="text")
"""

__all__: list[str] = []

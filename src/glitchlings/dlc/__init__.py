"""Optional DLC integrations for Glitchlings."""

from .huggingface import install as install_huggingface
from .pytorch_lightning import install as install_pytorch_lightning

__all__ = ["install_huggingface", "install_pytorch_lightning"]

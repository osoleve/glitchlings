"""Optional DLC integrations for Glitchlings."""

from .huggingface import install as install_huggingface
from .pytorch_lightning import install as install_pytorch_lightning
from .pytorch import install as install_pytorch

__all__ = ["install_huggingface", "install_pytorch", "install_pytorch_lightning"]

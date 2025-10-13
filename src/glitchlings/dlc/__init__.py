"""Optional DLC integrations for Glitchlings."""

from .huggingface import install as install_huggingface
from .pytorch import install as install_pytorch

__all__ = ["install_huggingface", "install_pytorch"]

import sys
from importlib import import_module
from importlib import util as importlib_util

from .config import AttackConfig, build_gaggle, load_attack_config
from .util import SAMPLE_TEXT
from .zoo import (
    Adjax,
    Apostrofae,
    Ekkokin,
    Gaggle,
    Glitchling,
    Hokey,
    Jargoyle,
    Mim1c,
    Redactyl,
    Reduple,
    Rushmore,
    Scannequin,
    Spectroll,
    Typogre,
    Zeedub,
    adjax,
    apostrofae,
    ekkokin,
    hokey,
    is_rust_pipeline_enabled,
    is_rust_pipeline_supported,
    jargoyle,
    mim1c,
    pipeline_feature_flag_enabled,
    plan_glitchling_specs,
    plan_glitchlings,
    redactyl,
    reduple,
    rushmore,
    scannequin,
    spectroll,
    summon,
    typogre,
    zeedub,
)


def _ensure_rust_extension_alias() -> None:
    """Expose the compiled Rust extension under the expected namespace."""

    target_name = "glitchlings._zoo_rust"
    if target_name in sys.modules:
        return

    if importlib_util.find_spec("_zoo_rust") is None:
        return

    module = import_module("_zoo_rust")
    sys.modules[target_name] = module
    setattr(sys.modules[__name__], "_zoo_rust", module)


_ensure_rust_extension_alias()

__all__ = [
    "Typogre",
    "typogre",
    "Mim1c",
    "mim1c",
    "Jargoyle",
    "jargoyle",
    "Adjax",
    "adjax",
    "Apostrofae",
    "apostrofae",
    "Ekkokin",
    "ekkokin",
    "Hokey",
    "hokey",
    "Redactyl",
    "redactyl",
    "Reduple",
    "reduple",
    "Rushmore",
    "rushmore",
    "Spectroll",
    "spectroll",
    "Scannequin",
    "scannequin",
    "Zeedub",
    "zeedub",
    "summon",
    "Glitchling",
    "Gaggle",
    "plan_glitchlings",
    "plan_glitchling_specs",
    "is_rust_pipeline_enabled",
    "is_rust_pipeline_supported",
    "pipeline_feature_flag_enabled",
    "SAMPLE_TEXT",
    "AttackConfig",
    "build_gaggle",
    "load_attack_config",
]

import importlib
import importlib.util
import random
import sys
from pathlib import Path

import pytest

def _ensure_rust_extension_importable() -> None:
    """Attempt to expose a locally built Rust extension for test runs."""
    if importlib.util.find_spec("glitchlings._zoo_rust") is not None:
        return

    repo_root = Path(__file__).resolve().parents[1]
    build_root = repo_root / "build"
    if not build_root.exists():
        return

    artifacts = sorted(
        build_root.glob("lib.*/glitchlings/_zoo_rust.*"),
        key=lambda candidate: candidate.stat().st_mtime,
        reverse=True,
    )

    if not artifacts:
        return

    importlib.import_module("glitchlings")

    for artifact in artifacts:
        spec = importlib.util.spec_from_file_location("glitchlings._zoo_rust", artifact)
        if spec is None or spec.loader is None:
            continue
        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules["glitchlings._zoo_rust"] = module
            spec.loader.exec_module(module)
            package = sys.modules.get("glitchlings")
            if package is not None and hasattr(package, "__path__"):
                package.__path__.append(str(artifact.parent))
            return
        except (ImportError, ModuleNotFoundError):
            # Extension exists but cannot be loaded (ABI mismatch, missing libraries, etc.)
            continue

_ensure_rust_extension_importable()

reduple_module = importlib.import_module("glitchlings.zoo.reduple")
rushmore_module = importlib.import_module("glitchlings.zoo.rushmore")
scannequin_module = importlib.import_module("glitchlings.zoo.scannequin")
redactyl_module = importlib.import_module("glitchlings.zoo.redactyl")
typogre_module = importlib.import_module("glitchlings.zoo.typogre")
zeedub_module = importlib.import_module("glitchlings.zoo.zeedub")
adjax_module = importlib.import_module("glitchlings.zoo.adjax")
ekkokin_module = importlib.import_module("glitchlings.zoo.ekkokin")
apostrofae_module = importlib.import_module("glitchlings.zoo.apostrofae")
core_module = importlib.import_module("glitchlings.zoo.core")
pedant_module = importlib.import_module("glitchlings.zoo.pedant")


def _with_descriptor_seeds(
    descriptors: list[dict[str, object]], master_seed: int
) -> list[dict[str, object]]:
    seeded: list[dict[str, object]] = []
    for index, descriptor in enumerate(descriptors):
        seeded.append(
            {
                "name": descriptor["name"],
                "operation": dict(descriptor["operation"]),
                "seed": core_module.Gaggle.derive_seed(
                    master_seed, descriptor["name"], index
                ),
            }
        )
    return seeded


def test_reduple_respects_explicit_rng():
    text = "Repeat me"
    expected = reduple_module._python_reduplicate_words(
        text,
        rate=1.0,
        rng=random.Random(99),
    )
    result = reduple_module.reduplicate_words(
        text,
        rate=1.0,
        rng=random.Random(99),
    )
    assert result == expected == "Repeat Repeat me me"


def test_redactyl_empty_text_raises_value_error():
    message = "contains no redactable words"
    with pytest.raises(ValueError, match=message):
        redactyl_module.redact_words("", seed=1)


def test_redactyl_whitespace_only_text_raises_value_error():
    message = "contains no redactable words"
    with pytest.raises(ValueError, match=message):
        redactyl_module.redact_words("   \t\n  ", seed=2)

def test_compose_glitchlings_propagates_glitch_errors():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    master_seed = 404
    descriptors = _with_descriptor_seeds(
        [
            {
                "name": "Redactyl",
                "operation": {
                    "type": "redact",
                    "replacement_char": redactyl_module.FULL_BLOCK,
                    "rate": 1.0,
                    "merge_adjacent": False,
                    "unweighted": False,
                },
            }
        ],
        master_seed,
    )
    with pytest.raises(ValueError, match="contains no redactable words"):
        zoo_rust.compose_glitchlings("   \t", descriptors, master_seed)

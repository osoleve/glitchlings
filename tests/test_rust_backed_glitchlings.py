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

    import glitchlings  # Ensure parent package exists before loading extension

    for artifact in artifacts:
        spec = importlib.util.spec_from_file_location("glitchlings._zoo_rust", artifact)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules["glitchlings._zoo_rust"] = module
        spec.loader.exec_module(module)
        package = sys.modules.get("glitchlings")
        if package is not None and hasattr(package, "__path__"):
            package.__path__.append(str(artifact.parent))
        return

_ensure_rust_extension_importable()

reduple_module = importlib.import_module("glitchlings.zoo.reduple")
rushmore_module = importlib.import_module("glitchlings.zoo.rushmore")
scannequin_module = importlib.import_module("glitchlings.zoo.scannequin")
redactyl_module = importlib.import_module("glitchlings.zoo.redactyl")
typogre_module = importlib.import_module("glitchlings.zoo.typogre")
core_module = importlib.import_module("glitchlings.zoo.core")


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


def test_reduple_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = reduple_module._python_reduplicate_words(
        text,
        rate=0.5,
        rng=random.Random(123),
    )
    result = reduple_module.reduplicate_words(text, rate=0.5, seed=123)
    assert (
        result
        == expected
        == "The The quick quick brown fox fox jumps over over the the lazy lazy dog."
    )


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


def test_reduple_unweighted_matches_python_fallback():
    text = "alpha beta gamma delta epsilon zeta"
    seed = 1
    expected = reduple_module._python_reduplicate_words(
        text,
        rate=0.5,
        rng=random.Random(seed),
        unweighted=True,
    )
    result = reduple_module.reduplicate_words(
        text,
        rate=0.5,
        seed=seed,
        unweighted=True,
    )
    assert result == expected



def test_rushmore_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = rushmore_module._python_delete_random_words(
        text,
        rate=0.5,
        rng=random.Random(123),
    )
    result = rushmore_module.delete_random_words(
        text, rate=0.5, seed=123
    )
    assert result == expected == "The over the lazy dog."


def test_rushmore_unweighted_matches_python_fallback():
    text = "alpha beta gamma delta epsilon"
    seed = 11
    expected = rushmore_module._python_delete_random_words(
        text,
        rate=0.5,
        rng=random.Random(seed),
        unweighted=True,
    )
    result = rushmore_module.delete_random_words(
        text,
        rate=0.5,
        seed=seed,
        unweighted=True,
    )
    assert result == expected



def test_scannequin_matches_python_fallback():
    text = "The m rn"
    expected = scannequin_module._python_ocr_artifacts(
        text,
        rate=1.0,
        rng=random.Random(1),
    )
    result = scannequin_module.ocr_artifacts(text, rate=1.0, seed=1)
    assert result == expected == "Tlie rn rri"


@pytest.mark.parametrize("seed", [0, 1, 2, 5, 13])
def test_scannequin_overlap_candidates_matches_python(seed: int):
    text = "cl rn li"
    expected = scannequin_module._python_ocr_artifacts(
        text,
        rate=1.0,
        rng=random.Random(seed),
    )
    result = scannequin_module.ocr_artifacts(text, rate=1.0, seed=seed)
    assert result == expected


def test_redactyl_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = redactyl_module._python_redact_words(
        text,
        replacement_char=redactyl_module.FULL_BLOCK,
        rate=0.5,
        merge_adjacent=False,
        rng=random.Random(123),
    )
    result = redactyl_module.redact_words(text, rate=0.5, seed=123)
    assert (
        result
        == expected
        == "███ █████ █████ fox █████ over the lazy dog."
    )



def test_redactyl_unweighted_matches_python_fallback():
    text = "alpha beta gamma delta epsilon"
    seed = 5
    expected = redactyl_module._python_redact_words(
        text,
        replacement_char="#",
        rate=0.5,
        merge_adjacent=False,
        rng=random.Random(seed),
        unweighted=True,
    )
    result = redactyl_module.redact_words(
        text,
        replacement_char="#",
        rate=0.5,
        merge_adjacent=False,
        seed=seed,
        unweighted=True,
    )
    assert result == expected



def test_typogre_matches_python_fallback():
    text = "Adjust the valves before launch"
    layout = getattr(typogre_module.KEYNEIGHBORS, "CURATOR_QWERTY")
    expected = typogre_module._fatfinger_python(
        text,
        rate=0.3,
        layout=layout,
        rng=random.Random(314),
    )
    result = typogre_module.fatfinger(
        text,
        rate=0.3,
        keyboard="CURATOR_QWERTY",
        seed=314,
    )
    assert result == expected

def test_redactyl_merge_adjacent_blocks():
    text = "redact these words"
    expected = redactyl_module._python_redact_words(
        text,
        replacement_char=redactyl_module.FULL_BLOCK,
        rate=1.0,
        merge_adjacent=True,
        rng=random.Random(7),
    )
    result = redactyl_module.redact_words(
        text,
        rate=1.0,
        merge_adjacent=True,
        seed=7,
    )
    assert result == expected == "█████████████████"


def test_redactyl_empty_text_raises_value_error():
    message = "contains no redactable words"
    with pytest.raises(ValueError, match=message):
        redactyl_module.redact_words("", seed=1)


def test_redactyl_whitespace_only_text_raises_value_error():
    message = "contains no redactable words"
    with pytest.raises(ValueError, match=message):
        redactyl_module.redact_words("   \t\n  ", seed=2)


def _run_python_sequence(text: str, descriptors: list[dict[str, object]], master_seed: int) -> str:
    current = text
    for index, descriptor in enumerate(descriptors):
        rng_seed = descriptor.get("seed")
        if rng_seed is None:
            rng_seed = core_module.Gaggle.derive_seed(
                master_seed, descriptor["name"], index
            )
        rng = random.Random(rng_seed)
        operation = descriptor["operation"]
        op_type = operation["type"]
        if op_type == "reduplicate":
            current = reduple_module._python_reduplicate_words(
                current,
                rate=operation["reduplication_rate"],
                rng=rng,
            )
        elif op_type == "delete":
            current = rushmore_module._python_delete_random_words(
                current,
                rate=operation["max_deletion_rate"],
                rng=rng,
            )
        elif op_type == "redact":
            current = redactyl_module._python_redact_words(
                current,
                replacement_char=operation["replacement_char"],
                rate=operation["redaction_rate"],
                merge_adjacent=operation["merge_adjacent"],
                rng=rng,
            )
        elif op_type == "ocr":
            current = scannequin_module._python_ocr_artifacts(
                current,
                rate=operation["error_rate"],
                rng=rng,
            )
        else:  # pragma: no cover - defensive guard
            raise AssertionError(f"Unsupported operation type: {op_type!r}")
    return current


def test_compose_glitchlings_matches_python_pipeline():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    raw_descriptors = [
        {"name": "Reduple", "operation": {"type": "reduplicate", "reduplication_rate": 0.4, "unweighted": False}},
        {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.5, "unweighted": False}},
        {
            "name": "Redactyl",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_module.FULL_BLOCK,
                "redaction_rate": 0.6,
                "merge_adjacent": True,
                "unweighted": False,
            },
        },
        {"name": "Scannequin", "operation": {"type": "ocr", "error_rate": 0.25}},
    ]
    text = "Guard the vault at midnight"
    master_seed = 404
    descriptors = _with_descriptor_seeds(raw_descriptors, master_seed)
    expected = _run_python_sequence(text, descriptors, master_seed)
    result = zoo_rust.compose_glitchlings(text, descriptors, master_seed)
    assert result == expected


def test_compose_glitchlings_is_deterministic():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    raw_descriptors = [
        {"name": "Reduple", "operation": {"type": "reduplicate", "reduplication_rate": 0.4, "unweighted": False}},
        {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.3, "unweighted": False}},
        {
            "name": "Redactyl",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_module.FULL_BLOCK,
                "redaction_rate": 0.6,
                "merge_adjacent": True,
                "unweighted": False,
            },
        },
    ]
    descriptors = _with_descriptor_seeds(raw_descriptors, 777)
    text = "Guard the vault at midnight"
    first = zoo_rust.compose_glitchlings(text, descriptors, 777)
    second = zoo_rust.compose_glitchlings(text, descriptors, 777)
    assert first == second == _run_python_sequence(text, descriptors, 777)


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
                    "redaction_rate": 1.0,
                    "merge_adjacent": False,
                    "unweighted": False,
                },
            }
        ],
        master_seed,
    )
    with pytest.raises(ValueError, match="contains no redactable words"):
        zoo_rust.compose_glitchlings("   \t", descriptors, master_seed)


def test_gaggle_prefers_rust_pipeline(monkeypatch):
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    original_compose = zoo_rust.compose_glitchlings
    calls: list[tuple[str, list[dict[str, object]], int]] = []

    def spy(text: str, descriptors: list[dict[str, object]], master_seed: int) -> str:
        calls.append((text, descriptors, master_seed))
        return original_compose(text, descriptors, master_seed)

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")
    monkeypatch.setattr(zoo_rust, "compose_glitchlings", spy)
    monkeypatch.setattr(core_module, "_compose_glitchlings_rust", spy, raising=False)

    def _fail(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("Python fallback invoked")

    monkeypatch.setattr(reduple_module, "reduplicate_words", _fail)
    monkeypatch.setattr(rushmore_module, "delete_random_words", _fail)
    monkeypatch.setattr(redactyl_module, "redact_words", _fail)
    monkeypatch.setattr(scannequin_module, "ocr_artifacts", _fail)

    gaggle_glitchlings = [
        scannequin_module.Scannequin(rate=0.2),
        reduple_module.Reduple(rate=0.4),
        rushmore_module.Rushmore(rate=0.3),
        redactyl_module.Redactyl(rate=0.5, merge_adjacent=True),
    ]
    gaggle = core_module.Gaggle(gaggle_glitchlings, seed=777)

    text = "Safeguard the archive tonight"
    result = gaggle(text)
    assert calls, "Expected the Rust pipeline to be invoked"
    descriptors = calls[0][1]
    apply_names = [glitch.name for glitch in gaggle.apply_order]
    original_names = [glitch.name for glitch in gaggle_glitchlings]
    assert apply_names != original_names, "Expected Gaggle to reorder glitchlings"
    expected_seeds = {
        glitch.name: core_module.Gaggle.derive_seed(777, glitch.name, index)
        for index, glitch in enumerate(gaggle_glitchlings)
    }
    assert [descriptor["seed"] for descriptor in descriptors] == [
        expected_seeds[descriptor["name"]]
        for descriptor in descriptors
    ]
    expected = _run_python_sequence(text, descriptors, 777)
    assert result == expected


def test_gaggle_python_fallback_when_pipeline_disabled(monkeypatch):
    pytest.importorskip("glitchlings._zoo_rust")

    def _fail(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("Rust pipeline should not run when feature flag is disabled")

    monkeypatch.delenv("GLITCHLINGS_RUST_PIPELINE", raising=False)
    monkeypatch.setattr(core_module, "_compose_glitchlings_rust", _fail, raising=False)

    gaggle = core_module.Gaggle(
        [
            reduple_module.Reduple(rate=0.4),
            rushmore_module.Rushmore(rate=0.3),
        ],
        seed=2024,
    )

    text = "Hold the door"
    result = gaggle(text)
    raw_descriptors = [
        {"name": "Reduple", "operation": {"type": "reduplicate", "reduplication_rate": 0.4, "unweighted": False}},
        {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.3, "unweighted": False}},
    ]
    descriptors = _with_descriptor_seeds(raw_descriptors, 2024)
    expected = _run_python_sequence(text, descriptors, 2024)
    assert result == expected


def test_pipeline_falls_back_for_unsupported_glitchling(monkeypatch):
    master_seed = 1122
    text = "Synchronize thrusters before ascent"

    def _make_glitchlings() -> list[core_module.Glitchling]:
        typo = typogre_module.Typogre(rate=0.02, seed=5)
        redup = reduple_module.Reduple(rate=0.2, seed=7)
        return [typo, redup]

    python_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    expected = python_gaggle(text)

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")

    def _fail(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("Rust pipeline should not run on unsupported glitchlings")

    monkeypatch.setattr(core_module, "_compose_glitchlings_rust", _fail, raising=False)
    pipeline_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)

    assert pipeline_gaggle._pipeline_descriptors() is None
    assert pipeline_gaggle(text) == expected


def test_pipeline_falls_back_for_incomplete_operation(monkeypatch):
    master_seed = 909
    text = "Route traffic through the backup relay"

    def _make_glitchlings() -> list[core_module.Glitchling]:
        red = redactyl_module.Redactyl(rate=0.5, merge_adjacent=False, seed=11)
        red.set_param("merge_adjacent", None)
        rush = rushmore_module.Rushmore(rate=0.25, seed=13)
        return [red, rush]

    python_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    expected = python_gaggle(text)

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")

    def _fail(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("Rust pipeline should not run with incomplete operations")

    monkeypatch.setattr(core_module, "_compose_glitchlings_rust", _fail, raising=False)
    pipeline_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)

    assert pipeline_gaggle._pipeline_descriptors() is None
    assert pipeline_gaggle(text) == expected


def test_rust_pipeline_feature_flag_introspection(monkeypatch):
    monkeypatch.delenv("GLITCHLINGS_RUST_PIPELINE", raising=False)
    assert not core_module._pipeline_feature_flag_enabled()
    assert core_module.Gaggle.rust_pipeline_supported() is (
        core_module._compose_glitchlings_rust is not None
    )
    assert not core_module.Gaggle.rust_pipeline_enabled()

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")
    if core_module.Gaggle.rust_pipeline_supported():
        assert core_module.Gaggle.rust_pipeline_enabled()
    else:
        assert not core_module.Gaggle.rust_pipeline_enabled()

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "false")
    assert not core_module._pipeline_feature_flag_enabled()
    assert not core_module.Gaggle.rust_pipeline_enabled()







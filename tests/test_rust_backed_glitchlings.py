import importlib
import random

import pytest

reduple_module = importlib.import_module("glitchlings.zoo.reduple")
rushmore_module = importlib.import_module("glitchlings.zoo.rushmore")
scannequin_module = importlib.import_module("glitchlings.zoo.scannequin")
redactyl_module = importlib.import_module("glitchlings.zoo.redactyl")
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
        reduplication_rate=0.5,
        rng=random.Random(123),
    )
    result = reduple_module.reduplicate_words(text, reduplication_rate=0.5, seed=123)
    assert (
        result
        == expected
        == "The The quick quick brown brown fox fox jumps over over the lazy lazy dog."
    )


def test_reduple_respects_explicit_rng():
    text = "Repeat me"
    expected = reduple_module._python_reduplicate_words(
        text,
        reduplication_rate=1.0,
        rng=random.Random(99),
    )
    result = reduple_module.reduplicate_words(
        text,
        reduplication_rate=1.0,
        rng=random.Random(99),
    )
    assert result == expected == "Repeat Repeat me me"


def test_rushmore_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = rushmore_module._python_delete_random_words(
        text,
        max_deletion_rate=0.5,
        rng=random.Random(123),
    )
    result = rushmore_module.delete_random_words(
        text, max_deletion_rate=0.5, seed=123
    )
    assert result == expected == "The over the lazy dog."


def test_scannequin_matches_python_fallback():
    text = "The m rn"
    expected = scannequin_module._python_ocr_artifacts(
        text,
        error_rate=1.0,
        rng=random.Random(1),
    )
    result = scannequin_module.ocr_artifacts(text, error_rate=1.0, seed=1)
    assert result == expected == "Tlie rn m"


def test_redactyl_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = redactyl_module._python_redact_words(
        text,
        replacement_char=redactyl_module.FULL_BLOCK,
        redaction_rate=0.5,
        merge_adjacent=False,
        rng=random.Random(123),
    )
    result = redactyl_module.redact_words(text, redaction_rate=0.5, seed=123)
    assert (
        result
        == expected
        == "███ quick brown ███ █████ over the lazy ███."
    )


def test_redactyl_merge_adjacent_blocks():
    text = "redact these words"
    expected = redactyl_module._python_redact_words(
        text,
        replacement_char=redactyl_module.FULL_BLOCK,
        redaction_rate=1.0,
        merge_adjacent=True,
        rng=random.Random(7),
    )
    result = redactyl_module.redact_words(
        text,
        redaction_rate=1.0,
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
                reduplication_rate=operation["reduplication_rate"],
                rng=rng,
            )
        elif op_type == "delete":
            current = rushmore_module._python_delete_random_words(
                current,
                max_deletion_rate=operation["max_deletion_rate"],
                rng=rng,
            )
        elif op_type == "redact":
            current = redactyl_module._python_redact_words(
                current,
                replacement_char=operation["replacement_char"],
                redaction_rate=operation["redaction_rate"],
                merge_adjacent=operation["merge_adjacent"],
                rng=rng,
            )
        elif op_type == "ocr":
            current = scannequin_module._python_ocr_artifacts(
                current,
                error_rate=operation["error_rate"],
                rng=rng,
            )
        else:  # pragma: no cover - defensive guard
            raise AssertionError(f"Unsupported operation type: {op_type!r}")
    return current


def test_compose_glitchlings_matches_python_pipeline():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    raw_descriptors = [
        {"name": "Reduple", "operation": {"type": "reduplicate", "reduplication_rate": 0.4}},
        {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.5}},
        {
            "name": "Redactyl",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_module.FULL_BLOCK,
                "redaction_rate": 0.6,
                "merge_adjacent": True,
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
        {"name": "Reduple", "operation": {"type": "reduplicate", "reduplication_rate": 0.4}},
        {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.3}},
        {
            "name": "Redactyl",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_module.FULL_BLOCK,
                "redaction_rate": 0.6,
                "merge_adjacent": True,
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
        scannequin_module.Scannequin(error_rate=0.2),
        reduple_module.Reduple(reduplication_rate=0.4),
        rushmore_module.Rushmore(max_deletion_rate=0.3),
        redactyl_module.Redactyl(redaction_rate=0.5, merge_adjacent=True),
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
            reduple_module.Reduple(reduplication_rate=0.4),
            rushmore_module.Rushmore(max_deletion_rate=0.3),
        ],
        seed=2024,
    )

    text = "Hold the door"
    result = gaggle(text)
    raw_descriptors = [
        {"name": "Reduple", "operation": {"type": "reduplicate", "reduplication_rate": 0.4}},
        {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.3}},
    ]
    descriptors = _with_descriptor_seeds(raw_descriptors, 2024)
    expected = _run_python_sequence(text, descriptors, 2024)
    assert result == expected


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

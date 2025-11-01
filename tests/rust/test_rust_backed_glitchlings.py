import importlib
import importlib.util
import random
import sys
from pathlib import Path

import pytest

COLEMAK_SERIALIZED_LAYOUT = {
    "'": ["[", "]", "\\", "o", ".", "/"],
    ",": ["e", "i", "o", "m", "."],
    "-": ["0", "=", ";", "[", "]"],
    ".": ["i", "o", "'", ",", "/"],
    "/": ["o", "'", "."],
    "0": ["9", "-", "y", ";", "["],
    "1": ["`", "2", "q", "w"],
    "2": ["1", "3", "q", "w", "f"],
    "3": ["2", "4", "w", "f", "p"],
    "4": ["3", "5", "f", "p", "g"],
    "5": ["4", "6", "p", "g", "j"],
    "6": ["5", "7", "g", "j", "l"],
    "7": ["6", "8", "j", "l", "u"],
    "8": ["7", "9", "l", "u", "y"],
    "9": ["8", "0", "u", "y", ";"],
    ";": ["9", "0", "-", "y", "[", "e", "i", "o"],
    "=": ["-", "[", "]", "\\"],
    "[": ["0", "-", "=", ";", "]", "i", "o", "'"],
    "\\": ["=", "]", "'"],
    "]": ["-", "=", "[", "\\", "o", "'"],
    "`": ["1", "q"],
    "a": ["q", "w", "f", "r", "z"],
    "b": ["d", "h", "n", "v", "k"],
    "c": ["s", "t", "d", "x", "v"],
    "d": ["g", "j", "l", "t", "h", "c", "v", "b"],
    "e": ["u", "y", ";", "n", "i", "k", "m", ","],
    "f": ["2", "3", "4", "w", "p", "a", "r", "s"],
    "g": ["4", "5", "6", "p", "j", "s", "t", "d"],
    "h": ["j", "l", "u", "d", "n", "v", "b", "k"],
    "i": ["y", ";", "[", "e", "o", "m", ",", "."],
    "j": ["5", "6", "7", "g", "l", "t", "d", "h"],
    "k": ["h", "n", "e", "b", "m"],
    "l": ["6", "7", "8", "j", "u", "d", "h", "n"],
    "m": ["n", "e", "i", "k", ","],
    "n": ["l", "u", "y", "h", "e", "b", "k", "m"],
    "o": [";", "[", "]", "i", "'", ",", ".", "/"],
    "p": ["3", "4", "5", "f", "g", "r", "s", "t"],
    "q": ["`", "1", "2", "w", "a"],
    "r": ["w", "f", "p", "a", "s", "z", "x"],
    "s": ["f", "p", "g", "r", "t", "z", "x", "c"],
    "t": ["p", "g", "j", "s", "d", "x", "c", "v"],
    "u": ["7", "8", "9", "l", "y", "h", "n", "e"],
    "v": ["t", "d", "h", "c", "b"],
    "w": ["1", "2", "3", "q", "f", "a", "r"],
    "x": ["r", "s", "t", "z", "c"],
    "y": ["8", "9", "0", "u", ";", "n", "e", "i"],
    "z": ["a", "r", "s", "x"],
}

CURATOR_QWERTY_SERIALIZED_LAYOUT = {
    "a": ["q", "w", "s", "z"],
    "b": ["v", "g", "h", "n", " ", " "],
    "c": ["x", "d", "f", "v", " ", " "],
    "d": ["s", "e", "r", "f", "c", "x"],
    "e": ["w", "s", "d", "r", "f", "3", "4"],
    "f": ["d", "r", "t", "g", "v", "c"],
    "g": ["f", "t", "y", "h", "b", "v"],
    "h": ["g", "y", "u", "j", "n", "b"],
    "i": ["u", "j", "k", "o", "8", "9"],
    "j": ["h", "u", "i", "k", "m", "n"],
    "k": ["j", "i", "l", "o", "m", ","],
    "l": ["k", "o", "p", ";", ".", ","],
    "m": ["n", "j", "k", ",", " ", " "],
    "n": ["b", "h", "j", "m", " ", " "],
    "o": ["i", "k", "l", "p", "9", "0"],
    "p": ["o", "0", "-", "[", ";", "l"],
    "q": ["w", "a", "s", " ", "1", "2"],
    "r": ["e", "d", "f", "t", "4", "5"],
    "s": ["a", "w", "e", "d", "x", "z"],
    "t": ["r", "5", "6", "y", "g", "f"],
    "u": ["y", "7", "8", "i", "j", "h"],
    "v": ["c", "f", "g", "b", " ", " "],
    "w": ["q", "2", "3", "e", "s", "a"],
    "x": ["z", "s", "d", "c", " ", " "],
    "y": ["t", "6", "7", "u", "h", "g"],
    "z": ["a", "s", "x"],
}

DEFAULT_ZWJ_CHARACTERS = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]



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
            # Continue to try other artifacts or fall back to Python implementation
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
try:
    apostrofae_module = importlib.import_module("glitchlings.zoo.apostrofae")
except ModuleNotFoundError:
    apostrofae_module = None
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


def _require_apostrofae_module():
    if apostrofae_module is None:
        pytest.skip("Apostrofae glitchling not implemented yet")
    return apostrofae_module


def test_orchestration_plan_matches_python_reference():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    master_seed = 24680
    specs = [
        {
            "name": "Rushmore",
            "scope": int(core_module.AttackWave.WORD),
            "order": int(core_module.AttackOrder.EARLY),
        },
        {
            "name": "Reduple",
            "scope": int(core_module.AttackWave.WORD),
            "order": int(core_module.AttackOrder.NORMAL),
        },
        {
            "name": "Typogre",
            "scope": int(core_module.AttackWave.CHARACTER),
            "order": int(core_module.AttackOrder.NORMAL),
        },
    ]

    plan_fn = getattr(zoo_rust, "plan_glitchlings", None)
    if plan_fn is None:
        pytest.skip("plan_glitchlings not available in compiled extension")

    try:
        rust_plan = plan_fn(specs, master_seed)
    except AttributeError:
        pytest.skip("plan_glitchlings requires a rebuilt Rust extension")
    python_plan = core_module._plan_glitchlings_python(specs, master_seed)
    assert rust_plan == python_plan


def test_ekkokin_matches_python_fallback():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    rust_fn = getattr(zoo_rust, "ekkokin_homophones", None)
    if rust_fn is None:
        pytest.skip("ekkokin_homophones operation requires a rebuilt Rust extension")

    text = "Allowed writers write about the heir."
    rate = 0.5
    weighting = "flat"
    seed = 404

    expected = ekkokin_module._python_substitute_homophones(
        text,
        rate=rate,
        weighting=weighting,
        rng=random.Random(seed),
    )

    clamped_rate = max(0.0, min(1.0, rate))
    result = rust_fn(text, clamped_rate, weighting, random.Random(seed))

    assert result == expected


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


def test_adjax_matches_python_fallback():
    text = "Signal integrity matters greatly"
    seed = 23
    rate = 0.8
    expected = adjax_module._python_swap_adjacent_words(
        text,
        rate=rate,
        rng=random.Random(seed),
    )
    result = adjax_module.swap_adjacent_words(
        text,
        rate=rate,
        seed=seed,
    )
    assert result == expected


def test_adjax_respects_explicit_rng():
    text = "Keep the formatting intact"
    rate = 0.6
    rng_expected = random.Random(13)
    expected = adjax_module._python_swap_adjacent_words(
        text,
        rate=rate,
        rng=rng_expected,
    )
    rng_actual = random.Random(13)
    result = adjax_module.swap_adjacent_words(
        text,
        rate=rate,
        rng=rng_actual,
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



def test_redactyl_zero_rate_is_noop(monkeypatch):
    text = "alpha beta gamma"
    monkeypatch.setattr(redactyl_module, "_redact_words_rust", None, raising=False)

    result = redactyl_module.redact_words(text, rate=0.0, seed=42)
    assert result == text

    python_result = redactyl_module._python_redact_words(
        text,
        replacement_char=redactyl_module.FULL_BLOCK,
        rate=0.0,
        merge_adjacent=False,
        rng=random.Random(42),
    )
    assert python_result == text

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
                rate=operation["rate"],
                rng=rng,
            )
        elif op_type == "delete":
            current = rushmore_module._python_delete_random_words(
                current,
                rate=operation["rate"],
                rng=rng,
            )
        elif op_type == "swap_adjacent":
            current = adjax_module._python_swap_adjacent_words(
                current,
                rate=operation["rate"],
                rng=rng,
            )
        elif op_type == "redact":
            current = redactyl_module._python_redact_words(
                current,
                replacement_char=operation["replacement_char"],
                rate=operation["rate"],
                merge_adjacent=operation["merge_adjacent"],
                rng=rng,
            )
        elif op_type == "ocr":
            current = scannequin_module._python_ocr_artifacts(
                current,
                rate=operation["rate"],
                rng=rng,
            )
        elif op_type == "zwj":
            characters = operation.get("characters")
            if characters is None:
                characters = zeedub_module._DEFAULT_ZERO_WIDTH_CHARACTERS
            else:
                characters = tuple(characters)
            current = zeedub_module._python_insert_zero_widths(
                current,
                rate=operation["rate"],
                rng=rng,
                characters=characters,
            )
        elif op_type == "typo":
            keyboard = operation.get("keyboard", "CURATOR_QWERTY")
            layout_override = operation.get("layout")
            if layout_override is None:
                layout = getattr(typogre_module.KEYNEIGHBORS, keyboard)
            else:
                layout = {
                    key: list(value) for key, value in layout_override.items()
                }
            current = typogre_module._fatfinger_python(
                current,
                rate=operation["rate"],
                rng=rng,
                layout=layout,
            )
        else:  # pragma: no cover - defensive guard
            raise AssertionError(f"Unsupported operation type: {op_type!r}")
    return current


def test_compose_glitchlings_matches_python_pipeline():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    if not hasattr(zoo_rust, "swap_adjacent_words"):
        pytest.skip("swap_adjacent support not available in rust extension")
    raw_descriptors = [
        {
            "name": "Reduple",
            "operation": {
                "type": "reduplicate",
                "rate": 0.4,
                "unweighted": False,
            },
        },
        {
            "name": "Rushmore",
            "operation": {
                "type": "delete",
                "rate": 0.5,
                "unweighted": False,
            },
        },
        {
            "name": "Adjax",
            "operation": {"type": "swap_adjacent", "rate": 0.6},
        },
        {
            "name": "Redactyl",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_module.FULL_BLOCK,
                "rate": 0.6,
                "merge_adjacent": True,
                "unweighted": False,
            },
        },
        {"name": "Scannequin", "operation": {"type": "ocr", "rate": 0.25}},
    ]
    text = "Guard the vault at midnight"
    master_seed = 404
    descriptors = _with_descriptor_seeds(raw_descriptors, master_seed)
    expected = _run_python_sequence(text, descriptors, master_seed)
    result = zoo_rust.compose_glitchlings(text, descriptors, master_seed)
    assert result == expected




def test_compose_glitchlings_supports_typo_and_zwj():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    layout = {key: list(value) for key, value in typogre_module.KEYNEIGHBORS.CURATOR_QWERTY.items()}
    raw_descriptors = [
        {
            "name": "Typogre",
            "operation": {
                "type": "typo",
                "rate": 0.02,
                "keyboard": "CURATOR_QWERTY",
                "layout": layout,
            },
        },
        {
            "name": "Zeedub",
            "operation": {
                "type": "zwj",
                "rate": 0.015,
                "characters": ["\u200b", "\u2060"],
            },
        },
    ]
    master_seed = 515
    descriptors = _with_descriptor_seeds(raw_descriptors, master_seed)
    text_case = "Stealth glyphs haunt the interface"
    expected = _run_python_sequence(text_case, descriptors, master_seed)
    result = zoo_rust.compose_glitchlings(text_case, descriptors, master_seed)
    assert result == expected

def test_compose_glitchlings_is_deterministic():
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    if not hasattr(zoo_rust, "swap_adjacent_words"):
        pytest.skip("swap_adjacent support not available in rust extension")
    raw_descriptors = [
        {
            "name": "Reduple",
            "operation": {
                "type": "reduplicate",
                "rate": 0.4,
                "unweighted": False,
            },
        },
        {
            "name": "Rushmore",
            "operation": {
                "type": "delete",
                "rate": 0.3,
                "unweighted": False,
            },
        },
        {
            "name": "Adjax",
            "operation": {"type": "swap_adjacent", "rate": 0.4},
        },
        {
            "name": "Redactyl",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_module.FULL_BLOCK,
                "rate": 0.6,
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


def test_apostrofae_rust_pipeline_matches_python(monkeypatch):
    module = _require_apostrofae_module()
    if not hasattr(module, "Apostrofae"):
        pytest.skip("Apostrofae class not exposed yet")

    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")

    apostrofae_cls = getattr(module, "Apostrofae")
    master_seed = 4242
    text = 'He said "hello", muttered \"hmm\", and typed `print("ok")`.'

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "0")
    glitch = apostrofae_cls(seed=master_seed)
    glitch.reset_rng(master_seed)
    python_expected = glitch(text)

    descriptor = glitch.pipeline_operation()
    if descriptor is None:
        pytest.skip("Apostrofae does not publish a pipeline descriptor yet")
    assert descriptor["type"] == "apostrofae"

    entry = {
        "name": glitch.name,
        "operation": descriptor,
        "seed": core_module.Gaggle.derive_seed(master_seed, glitch.name, 0),
    }

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")
    rust_result = zoo_rust.compose_glitchlings(text, [entry], master_seed)

    assert rust_result == python_expected


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
        raise AssertionError("Rust pipeline should not run when explicitly disabled")

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "0")
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
        {
            "name": "Reduple",
            "operation": {
                "type": "reduplicate",
                "rate": 0.4,
                "unweighted": False,
            },
        },
        {
            "name": "Rushmore",
            "operation": {
                "type": "delete",
                "rate": 0.3,
                "unweighted": False,
            },
        },
    ]
    descriptors = _with_descriptor_seeds(raw_descriptors, 2024)
    expected = _run_python_sequence(text, descriptors, 2024)
    assert result == expected


def test_pipeline_handles_typogre_and_zeedub(monkeypatch):
    zoo_rust = pytest.importorskip("glitchlings._zoo_rust")
    master_seed = 1122
    text = "Synchronize thrusters before ascent"

    def _make_glitchlings() -> list[core_module.Glitchling]:
        typo = typogre_module.Typogre(rate=0.02, seed=5)
        typo.set_param("keyboard", "COLEMAK")
        zwj = zeedub_module.Zeedub(rate=0.03, seed=11)
        zwj.set_param("characters", ["\u200b", "\u2060"])
        redup = reduple_module.Reduple(rate=0.2, seed=7)
        return [typo, redup, zwj]

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "0")
    python_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    python_expected = python_gaggle(text)

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")
    gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    descriptors = gaggle._pipeline_descriptors()
    assert descriptors == [
        {
            "name": "Reduple",
            "operation": {
                "type": "reduplicate",
                "rate": 0.2,
                "unweighted": False,
            },
            "seed": core_module.Gaggle.derive_seed(master_seed, "Reduple", 1),
        },
        {
            "name": "Typogre",
            "operation": {
                "type": "typo",
                "rate": 0.02,
                "keyboard": "COLEMAK",
                "layout": dict(COLEMAK_SERIALIZED_LAYOUT),
            },
            "seed": core_module.Gaggle.derive_seed(master_seed, "Typogre", 0),
        },
        {
            "name": "Zeedub",
            "operation": {
                "type": "zwj",
                "rate": 0.03,
                "characters": ["\u200b", "\u2060"],
            },
            "seed": core_module.Gaggle.derive_seed(master_seed, "Zeedub", 2),
        },
    ]

    rust_expected = zoo_rust.compose_glitchlings(text, descriptors, master_seed)

    invoked: dict[str, bool] = {}

    def spy(src_text: str, ops: list[dict[str, object]], seed: int) -> str:
        invoked["called"] = True
        return zoo_rust.compose_glitchlings(src_text, ops, seed)

    monkeypatch.setattr(core_module, "_compose_glitchlings_rust", spy, raising=False)

    result = gaggle(text)
    assert invoked.get("called") is True
    assert result == python_expected == rust_expected


def test_gaggle_python_and_rust_paths_share_plan(monkeypatch):
    pytest.importorskip("glitchlings._zoo_rust")
    master_seed = 1777
    text = "Verify resonance before launch"

    base_glitchlings = [
        typogre_module.Typogre(rate=0.02, seed=5),
        reduple_module.Reduple(rate=0.2, seed=7),
        zeedub_module.Zeedub(rate=0.03, seed=11),
    ]

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")
    rust_gaggle = core_module.Gaggle(
        [glitch.clone() for glitch in base_glitchlings],
        seed=master_seed,
    )
    rust_result = rust_gaggle(text)
    rust_plan = rust_gaggle._plan

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "0")
    python_gaggle = core_module.Gaggle(
        [glitch.clone() for glitch in base_glitchlings],
        seed=master_seed,
    )
    python_result = python_gaggle(text)
    python_plan = python_gaggle._plan

    assert rust_result == python_result
    assert rust_plan == python_plan

    specs = [
        {
            "name": glitch.name,
            "scope": int(glitch.level),
            "order": int(glitch.order),
        }
        for glitch in base_glitchlings
    ]
    python_reference = core_module._plan_glitchlings_python(specs, master_seed)
    assert python_plan == python_reference == rust_plan


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


def test_pipeline_falls_back_when_compose_raises(monkeypatch):
    _ = pytest.importorskip("glitchlings._zoo_rust")
    master_seed = 5150
    text = "Stabilise the uplink before the storm hits"

    def _make_glitchlings() -> list[core_module.Glitchling]:
        return [
            typogre_module.Typogre(rate=0.04, seed=3),
            reduple_module.Reduple(rate=0.25, seed=5),
            zeedub_module.Zeedub(rate=0.02, seed=7),
        ]

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "0")
    python_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    python_expected = python_gaggle(text)

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")
    fail_calls: dict[str, bool] = {}

    def _fail(*_args: object, **_kwargs: object) -> str:
        fail_calls["invoked"] = True
        raise RuntimeError("simulated rust pipeline failure")

    monkeypatch.setattr(core_module, "_compose_glitchlings_rust", _fail, raising=False)

    gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    descriptors = gaggle._pipeline_descriptors()
    assert descriptors == [
        {
            "name": "Reduple",
            "operation": {
                "type": "reduplicate",
                "rate": 0.25,
                "unweighted": False,
            },
            "seed": core_module.Gaggle.derive_seed(master_seed, "Reduple", 1),
        },
        {
            "name": "Typogre",
            "operation": {
                "type": "typo",
                "rate": 0.04,
                "keyboard": "CURATOR_QWERTY",
                "layout": dict(CURATOR_QWERTY_SERIALIZED_LAYOUT),
            },
            "seed": core_module.Gaggle.derive_seed(master_seed, "Typogre", 0),
        },
        {
            "name": "Zeedub",
            "operation": {
                "type": "zwj",
                "rate": 0.02,
                "characters": list(DEFAULT_ZWJ_CHARACTERS),
            },
            "seed": core_module.Gaggle.derive_seed(master_seed, "Zeedub", 2),
        },
    ]

    result = gaggle(text)
    assert fail_calls.get("invoked") is True
    assert result == python_expected


def test_rust_pipeline_feature_flag_introspection(monkeypatch):
    monkeypatch.delenv("GLITCHLINGS_RUST_PIPELINE", raising=False)
    assert core_module.pipeline_feature_flag_enabled()
    assert core_module.is_rust_pipeline_supported() is (
        core_module._compose_glitchlings_rust is not None
    )
    assert core_module.Gaggle.rust_pipeline_supported() is core_module.is_rust_pipeline_supported()
    assert core_module.is_rust_pipeline_enabled() is core_module.Gaggle.rust_pipeline_enabled()

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "0")
    assert not core_module.pipeline_feature_flag_enabled()
    assert not core_module.is_rust_pipeline_enabled()
    assert not core_module.Gaggle.rust_pipeline_enabled()

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "1")
    if core_module.Gaggle.rust_pipeline_supported():
        assert core_module.is_rust_pipeline_enabled()
        assert core_module.Gaggle.rust_pipeline_enabled()
    else:
        assert not core_module.is_rust_pipeline_enabled()
        assert not core_module.Gaggle.rust_pipeline_enabled()

    monkeypatch.setenv("GLITCHLINGS_RUST_PIPELINE", "false")
    assert not core_module.pipeline_feature_flag_enabled()
    assert not core_module.is_rust_pipeline_enabled()
    assert not core_module.Gaggle.rust_pipeline_enabled()







def test_zeedub_matches_python_fallback():
    pytest.importorskip("glitchlings._zoo_rust")

    text = "Invisible glyphs whisper between words"
    rate = 0.3
    seed = 404

    expected = zeedub_module._python_insert_zero_widths(
        text,
        rate=rate,
        rng=random.Random(seed),
        characters=zeedub_module._DEFAULT_ZERO_WIDTH_CHARACTERS,
    )

    result = zeedub_module.insert_zero_widths(text, rate=rate, seed=seed)
    assert result == expected


def test_zeedub_respects_explicit_rng():
    text = "Devices hide things in the margin"
    rate = 0.45
    rng_expected = random.Random(99)
    expected = zeedub_module._python_insert_zero_widths(
        text,
        rate=rate,
        rng=rng_expected,
        characters=zeedub_module._DEFAULT_ZERO_WIDTH_CHARACTERS,
    )

    rng_actual = random.Random(99)
    result = zeedub_module.insert_zero_widths(text, rate=rate, rng=rng_actual)
    assert result == expected


hokey_module = importlib.import_module("glitchlings.zoo.hokey")


def test_hokey_matches_python_fallback():
    pytest.importorskip("glitchlings._zoo_rust")

    text = "cool code is so fun and neat"
    rate = 0.5
    seed = 42

    expected = hokey_module._python_extend_vowels(
        text,
        rate=rate,
        extension_min=2,
        extension_max=5,
        word_length_threshold=6,
        base_p=0.45,
        rng=random.Random(seed),
    )

    result = hokey_module.extend_vowels(
        text,
        rate=rate,
        extension_min=2,
        extension_max=5,
        word_length_threshold=6,
        seed=seed,
    )
    assert result == expected


def test_hokey_respects_explicit_rng():
    text = "wow this is cool"
    rate = 0.8
    rng_expected = random.Random(555)
    expected = hokey_module._python_extend_vowels(
        text,
        rate=rate,
        extension_min=2,
        extension_max=5,
        word_length_threshold=6,
        base_p=0.45,
        rng=rng_expected,
    )

    rng_actual = random.Random(555)
    result = hokey_module.extend_vowels(
        text,
        rate=rate,
        extension_min=2,
        extension_max=5,
        word_length_threshold=6,
        rng=rng_actual,
    )
    assert result == expected


def test_hokey_in_gaggle_rust_pipeline():
    pytest.importorskip("glitchlings._zoo_rust")
    master_seed = 9999
    text = "this is so cool and fun"

    def _make_glitchlings() -> list[core_module.Glitchling]:
        hokey = hokey_module.Hokey(rate=0.6, extension_min=3, extension_max=6, seed=42)
        redup = reduple_module.Reduple(rate=0.2, seed=7)
        return [hokey, redup]

    import os
    os.environ["GLITCHLINGS_RUST_PIPELINE"] = "0"
    python_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    python_expected = python_gaggle(text)

    os.environ["GLITCHLINGS_RUST_PIPELINE"] = "1"
    rust_gaggle = core_module.Gaggle(_make_glitchlings(), seed=master_seed)
    rust_result = rust_gaggle(text)

    assert rust_result == python_expected


def test_hokey_utf8_parity():
    """Test that Rust and Python implementations handle UTF-8 correctly."""
    pytest.importorskip("glitchlings._zoo_rust")

    # Test with various UTF-8 characters
    text = "café naïve résumé"
    rate = 1.0
    seed = 777

    expected = hokey_module._python_extend_vowels(
        text,
        rate=rate,
        extension_min=2,
        extension_max=4,
        word_length_threshold=6,
        base_p=0.45,
        rng=random.Random(seed),
    )

    result = hokey_module.extend_vowels(
        text,
        rate=rate,
        extension_min=2,
        extension_max=4,
        word_length_threshold=6,
        seed=seed,
    )

    # Both should modify the text
    assert result != text
    assert expected != text
    # And they should match each other
    assert result == expected

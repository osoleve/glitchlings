import inspect
from unittest.mock import patch

import pytest

import glitchlings.zoo.core as core_module
from glitchlings.zoo.core import AttackWave, Glitchling
from glitchlings.zoo.rushmore import Rushmore
from glitchlings.zoo.typogre import Typogre


def test_typogre_clone_preserves_configuration_and_seed_behavior() -> None:
    original = Typogre(rate=0.05, keyboard="AZERTY", seed=111)

    clone = original.clone(seed=222)

    assert isinstance(clone, Typogre)
    assert clone.rate == original.rate
    assert clone.keyboard == original.keyboard

    sample_text = "The quick brown fox jumps over the lazy dog."

    original.reset_rng()
    original_result = original(sample_text)

    clone.reset_rng()
    clone_result_first = clone(sample_text)
    clone.reset_rng()
    clone_result_second = clone(sample_text)

    assert clone_result_first == clone_result_second
    assert clone_result_first != original_result

def test_glitchling_signature_introspection_is_cached() -> None:
    call_count = 0
    original_signature = inspect.signature

    def tracking_signature(func: object) -> inspect.Signature:
        nonlocal call_count
        call_count += 1
        return original_signature(func)

    def corruption(text: str, *, rng: object) -> str:
        assert rng is not None
        return text.upper()

    glitchling = Glitchling("CacheTester", corruption, AttackWave.DOCUMENT)

    with patch("glitchlings.zoo.core.inspect.signature", side_effect=tracking_signature):
        glitchling.corrupt("hello")
        glitchling.corrupt("world")

    assert call_count == 1

def test_glitchling_pipeline_operation_factory_survives_clone() -> None:
    def descriptor(glitchling: Glitchling) -> dict[str, object]:
        return {"type": "custom", "value": glitchling.kwargs.get("value")}

    glitch = Glitchling(
        "Factory",
        lambda text, **_: text,
        AttackWave.WORD,
        pipeline_operation=descriptor,
        value=7,
    )

    assert glitch.pipeline_operation() == {"type": "custom", "value": 7}

    clone = glitch.clone()
    assert clone.pipeline_operation() == {"type": "custom", "value": 7}


def test_plan_glitchlings_accepts_instances() -> None:
    master_seed = 777
    glitchlings = [
        Typogre(rate=0.05),
        Rushmore(rate=0.2, attack_mode="duplicate"),
        Typogre(rate=0.07, seed=910),
    ]

    plan = core_module.plan_glitchlings(glitchlings, master_seed, prefer_rust=False)

    specs = [
        {
            "name": glitchling.name,
            "scope": int(glitchling.level),
            "order": int(glitchling.order),
        }
        for glitchling in glitchlings
    ]
    expected = core_module._plan_glitchlings_python(specs, master_seed)

    assert plan == expected


def test_plan_glitchling_specs_accepts_mappings() -> None:
    master_seed = 31415
    specs = [
        {
            "name": "Rushmore",
            "scope": core_module.AttackWave.WORD,
            "order": core_module.AttackOrder.EARLY,
        },
        {
            "name": "Adjax",
            "scope": core_module.AttackWave.WORD,
            "order": core_module.AttackOrder.NORMAL,
        },
        {
            "name": "Typogre",
            "scope": core_module.AttackWave.CHARACTER,
            "order": core_module.AttackOrder.LATE,
        },
    ]

    plan = core_module.plan_glitchling_specs(specs, master_seed, prefer_rust=False)
    normalized_specs = [
        {
            "name": spec["name"],
            "scope": int(spec["scope"]),
            "order": int(spec["order"]),
        }
        for spec in specs
    ]
    expected = core_module._plan_glitchlings_python(normalized_specs, master_seed)

    assert plan == expected


def test_plan_glitchling_specs_prefers_rust_when_available(monkeypatch) -> None:
    master_seed = 2024
    specs = [
        {"name": "Adjax", "scope": 3, "order": 0},
        {"name": "Typogre", "scope": 4, "order": 1},
    ]

    expected_specs = [
        {"name": spec["name"], "scope": int(spec["scope"]), "order": int(spec["order"])}
        for spec in specs
    ]
    expected_plan = [(1, 9999)]
    rust_calls: dict[str, object] = {}

    def fake_rust(specs_arg, seed_arg):
        rust_calls["specs"] = specs_arg
        rust_calls["seed"] = seed_arg
        return expected_plan

    monkeypatch.setattr(core_module, "_plan_glitchlings_rust", fake_rust, raising=False)

    plan = core_module.plan_glitchling_specs(specs, master_seed, prefer_rust=True)

    assert plan == expected_plan
    assert rust_calls.get("seed") == master_seed
    assert rust_calls.get("specs") == expected_specs


def test_plan_glitchling_specs_respects_prefer_rust_flag(monkeypatch) -> None:
    master_seed = 8080
    specs = [
        {"name": "Zeedub", "scope": 4, "order": 0},
        {"name": "Typogre", "scope": 4, "order": 1},
    ]

    def boom(*_args, **_kwargs):
        raise AssertionError("Rust planner should not be invoked when prefer_rust=False")

    monkeypatch.setattr(core_module, "_plan_glitchlings_rust", boom, raising=False)

    plan = core_module.plan_glitchling_specs(specs, master_seed, prefer_rust=False)
    expected = core_module._plan_glitchlings_python(
        [
            {"name": spec["name"], "scope": int(spec["scope"]), "order": int(spec["order"])}
            for spec in specs
        ],
        master_seed,
    )

    assert plan == expected


def test_plan_glitchlings_requires_seed() -> None:
    with pytest.raises(ValueError, match="master seed"):
        core_module.plan_glitchlings([], master_seed=None)


def test_plan_glitchlings_with_rust_matches_python(monkeypatch) -> None:
    master_seed = 1357
    specs = [
        {"name": "Rushmore", "scope": 3, "order": 1},
        {"name": "Typogre", "scope": 4, "order": 0},
    ]

    python_plan = core_module._plan_glitchlings_python(specs, master_seed)

    monkeypatch.setattr(
        core_module,
        "_plan_glitchlings_rust",
        lambda *_args, **_kwargs: python_plan,
        raising=False,
    )

    rust_plan = core_module._plan_glitchlings_with_rust(specs, master_seed)
    assert rust_plan == python_plan


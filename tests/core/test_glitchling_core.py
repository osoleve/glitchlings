import pytest

import glitchlings.zoo.core as core_module
from glitchlings.zoo.core import AttackWave, Glitchling
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


def test_plan_operations_requires_seed() -> None:
    with pytest.raises(ValueError, match="master seed"):
        core_module.plan_operations([], master_seed=None)

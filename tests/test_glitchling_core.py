import inspect
from unittest.mock import patch

from glitchlings.zoo.core import AttackWave, Glitchling
from glitchlings.zoo.typogre import Typogre


def test_typogre_clone_preserves_configuration_and_seed_behavior() -> None:
    original = Typogre(rate=0.05, keyboard="AZERTY", seed=111)

    clone = original.clone(seed=222)

    assert isinstance(clone, Typogre)
    assert clone.rate == original.rate
    assert clone.max_change_rate == original.rate
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


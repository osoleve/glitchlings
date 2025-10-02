from glitchlings.zoo.typogre import Typogre


def test_typogre_clone_preserves_configuration_and_seed_behavior() -> None:
    original = Typogre(max_change_rate=0.05, keyboard="AZERTY", seed=111)

    clone = original.clone(seed=222)

    assert isinstance(clone, Typogre)
    assert clone.max_change_rate == original.max_change_rate
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

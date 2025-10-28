import random

import pytest

from glitchlings.zoo._sampling import weighted_sample_without_replacement


def test_weighted_sample_without_replacement_validates_arguments() -> None:
    rng = random.Random(0)

    with pytest.raises(ValueError, match="Sample size cannot be negative"):
        weighted_sample_without_replacement([0, 1], [0.5, 0.5], k=-1, rng=rng)

    with pytest.raises(ValueError, match="must be the same length"):
        weighted_sample_without_replacement([0, 1], [0.5], k=1, rng=rng)

    with pytest.raises(ValueError, match="Sample larger than population"):
        weighted_sample_without_replacement([0, 1], [0.5, 0.5], k=3, rng=rng)


def test_weighted_sample_without_replacement_prefers_heavier_candidates() -> None:
    rng = random.Random(0)
    population = [0, 1, 2, 3]
    weights = [0.1, 0.1, 0.4, 0.4]

    result = weighted_sample_without_replacement(population, weights, k=2, rng=rng)

    assert result == [3, 2]
    assert len(result) == len(set(result))


def test_weighted_sample_without_replacement_uniform_when_weights_zero() -> None:
    rng = random.Random(1)
    population = [0, 1, 2]
    weights = [0.0, 0.0, 0.0]

    result = weighted_sample_without_replacement(population, weights, k=2, rng=rng)

    assert result == [0, 1]
    assert len(result) == len(set(result))

import pytest

from glitchlings.zoo.adjax import Adjax
from glitchlings.zoo.redactyl import Redactyl
from glitchlings.zoo.reduple import Reduple
from glitchlings.zoo.rushmore import Rushmore
from glitchlings.zoo.scannequin import Scannequin


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (
            lambda: Redactyl(
                replacement_char="#",
                rate=0.5,
                merge_adjacent=True,
                unweighted=True,
            ),
            {
                "type": "redact",
                "replacement_char": "#",
                "redaction_rate": 0.5,
                "merge_adjacent": True,
                "unweighted": True,
            },
        ),
        (
            lambda: Rushmore(rate=0.33, unweighted=True),
            {
                "type": "delete",
                "max_deletion_rate": 0.33,
                "unweighted": True,
            },
        ),
        (
            lambda: Reduple(rate=0.25),
            {
                "type": "reduplicate",
                "reduplication_rate": 0.25,
                "unweighted": False,
            },
        ),
        (
            lambda: Scannequin(rate=0.12),
            {
                "type": "ocr",
                "error_rate": 0.12,
            },
        ),
        (
            lambda: Adjax(rate=0.6),
            {
                "type": "swap_adjacent",
                "swap_rate": 0.6,
            },
        ),
    ],
)
def test_pipeline_operations_emit_expected_descriptors(factory, expected):
    glitchling = factory()
    operation = glitchling.pipeline_operation()
    assert operation == expected


@pytest.mark.parametrize(
    ("factory", "knockout"),
    [
        (
            lambda: Redactyl(replacement_char="#", rate=0.5, merge_adjacent=True),
            lambda glitch: glitch.set_param("merge_adjacent", None),
        ),
        (
            lambda: Rushmore(rate=0.3),
            lambda glitch: glitch.set_param("rate", None),
        ),
        (
            lambda: Reduple(rate=0.2),
            lambda glitch: glitch.set_param("rate", None),
        ),
        (
            lambda: Scannequin(rate=0.18),
            lambda glitch: glitch.set_param("rate", None),
        ),
        (
            lambda: Adjax(rate=0.4),
            lambda glitch: glitch.set_param("rate", None),
        ),
    ],
)
def test_pipeline_operations_require_complete_parameters(factory, knockout):
    glitchling = factory()
    knockout(glitchling)
    assert glitchling.pipeline_operation() is None


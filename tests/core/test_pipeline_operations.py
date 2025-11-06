import pytest

from glitchlings.zoo.redactyl import Redactyl
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
                "rate": 0.5,
                "merge_adjacent": True,
                "unweighted": True,
            },
        ),
        (
            lambda: Rushmore(rate=0.33, unweighted=True),
            {
                "type": "delete",
                "rate": 0.33,
                "unweighted": True,
            },
        ),
        (
            lambda: Rushmore(modes="duplicate", duplicate_rate=0.25),
            {
                "type": "reduplicate",
                "rate": 0.25,
                "unweighted": False,
            },
        ),
        (
            lambda: Rushmore(
                modes=("delete", "swap"),
                delete_rate=0.2,
                swap_rate=0.6,
                unweighted=True,
            ),
            {
                "type": "rushmore_combo",
                "modes": ["delete", "swap"],
                "delete": {"rate": 0.2, "unweighted": True},
                "swap": {"rate": 0.6},
            },
        ),
        (
            lambda: Scannequin(rate=0.12),
            {
                "type": "ocr",
                "rate": 0.12,
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
            lambda glitch: (
                glitch.set_param("rate", None),
                glitch.set_param("delete_rate", None),
            ),
        ),
        (
            lambda: Scannequin(rate=0.18),
            lambda glitch: glitch.set_param("rate", None),
        ),
    ],
)
def test_pipeline_operations_require_complete_parameters(factory, knockout):
    glitchling = factory()
    knockout(glitchling)
    assert glitchling.pipeline_operation() is None


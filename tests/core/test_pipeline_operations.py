import pytest

from glitchlings import (
    ekkokin,
    hokey,
    mim1c,
    redactyl,
    rushmore,
    scannequin,
    typogre,
    zeedub,
)
from glitchlings.zoo.redactyl import Redactyl
from glitchlings.zoo.rushmore import Rushmore
from glitchlings.zoo.scannequin import Scannequin


# Systematic test ensuring all pipeline-capable glitchlings emit pipeline descriptors
# Note: Jargoyle is excluded as it relies on external lexicon dependencies
# and does not implement pipeline_operation() (intentionally non-Rust-accelerated)
@pytest.mark.parametrize(
    ("glitchling", "required_field"),
    [
        pytest.param(typogre, "type", id="typogre"),
        pytest.param(mim1c, "type", id="mim1c"),
        pytest.param(rushmore, "type", id="rushmore"),
        pytest.param(redactyl, "type", id="redactyl"),
        pytest.param(scannequin, "type", id="scannequin"),
        pytest.param(zeedub, "type", id="zeedub"),
        pytest.param(hokey, "type", id="hokey"),
        pytest.param(ekkokin, "type", id="ekkokin"),
    ],
)
def test_all_glitchlings_emit_pipeline_descriptors(glitchling, required_field):
    """Verify all glitchlings emit valid pipeline operation descriptors."""
    glitch = glitchling.clone()
    glitch.set_param("seed", 42)
    glitch.set_param("rate", 0.1)
    descriptor = glitch.pipeline_operation()
    assert descriptor is not None, f"{glitchling.name} should emit a pipeline descriptor"
    assert required_field in descriptor, f"{glitchling.name} descriptor missing '{required_field}'"
    assert isinstance(descriptor, dict), f"{glitchling.name} descriptor should be a dict"


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

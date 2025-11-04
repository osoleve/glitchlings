import importlib

import pytest

core_module = importlib.import_module("glitchlings.zoo.core")
ekkokin_module = importlib.import_module("glitchlings.zoo.ekkokin")
hokey_module = importlib.import_module("glitchlings.zoo.hokey")
mim1c_module = importlib.import_module("glitchlings.zoo.mim1c")
redactyl_module = importlib.import_module("glitchlings.zoo.redactyl")
scannequin_module = importlib.import_module("glitchlings.zoo.scannequin")
typogre_module = importlib.import_module("glitchlings.zoo.typogre")
zeedub_module = importlib.import_module("glitchlings.zoo.zeedub")
zoo_rust = importlib.import_module("glitchlings._zoo_rust")


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


def test_redactyl_empty_text_raises_value_error():
    message = "contains no redactable words"
    with pytest.raises(ValueError, match=message):
        redactyl_module.redact_words("", seed=1)


def test_redactyl_whitespace_only_text_raises_value_error():
    message = "contains no redactable words"
    with pytest.raises(ValueError, match=message):
        redactyl_module.redact_words("   \t\n  ", seed=2)

def test_compose_glitchlings_propagates_glitch_errors():
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


@pytest.mark.parametrize(
    ("glitch_cls", "expected_rate"),
    [
        (typogre_module.Typogre, 0.02),
        (mim1c_module.Mim1c, 0.02),
        (scannequin_module.Scannequin, 0.02),
        (zeedub_module.Zeedub, 0.02),
        (ekkokin_module.Ekkokin, 0.02),
        (hokey_module.Hokey, 0.3),
    ],
)
def test_pipeline_descriptor_restores_default_rate(glitch_cls, expected_rate):
    glitch = glitch_cls()
    glitch.set_param("rate", None)

    descriptor = glitch.pipeline_operation()

    assert descriptor is not None
    assert descriptor["rate"] == pytest.approx(expected_rate)


def test_redactyl_pipeline_resets_optional_parameters():
    glitch = redactyl_module.Redactyl(
        replacement_char="*",
        rate=0.5,
        merge_adjacent=True,
    )

    glitch.set_param("replacement_char", None)
    glitch.set_param("merge_adjacent", None)
    glitch.set_param("rate", None)

    descriptor = glitch.pipeline_operation()

    assert descriptor is not None
    assert descriptor["replacement_char"] == redactyl_module.FULL_BLOCK
    assert descriptor["merge_adjacent"] is False
    assert descriptor["rate"] == pytest.approx(0.025)


def test_zeedub_pipeline_defaults_to_curated_characters():
    glitch = zeedub_module.Zeedub(characters=("\u200b",))
    glitch.set_param("characters", None)

    descriptor = glitch.pipeline_operation()

    assert descriptor is not None
    assert descriptor["characters"]

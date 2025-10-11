import textwrap

import pytest

from glitchlings import build_gaggle, load_attack_config
from glitchlings.config import DEFAULT_ATTACK_SEED, parse_attack_config
from glitchlings.zoo import Typogre


def test_load_attack_config_supports_mixed_entries(tmp_path):
    config_path = tmp_path / "attack.yml"
    config_path.write_text(
        textwrap.dedent(
            """
            seed: 99
            glitchlings:
              - name: Typogre
                rate: 0.04
              - Rushmore(rate=0.2)
            """
        ),
        encoding="utf-8",
    )

    config = load_attack_config(config_path)

    assert len(config.glitchlings) == 2
    assert isinstance(config.glitchlings[0], Typogre)
    assert pytest.approx(config.glitchlings[0].kwargs["rate"], rel=1e-6) == 0.04
    assert config.glitchlings[1].name == "Rushmore"
    assert config.seed == 99

    gaggle = build_gaggle(config)
    assert gaggle.seed == 99


def test_build_gaggle_uses_override_and_default_seed():
    config = parse_attack_config({"glitchlings": ["Typogre"]})

    defaulted = build_gaggle(config)
    assert defaulted.seed == DEFAULT_ATTACK_SEED

    override = build_gaggle(config, seed_override=7)
    assert override.seed == 7


@pytest.mark.parametrize(
    "payload, message",
    [
        (None, "empty"),
        ("Typogre", "mapping"),
        ({"seed": 5}, "glitchlings"),
        ({"glitchlings": "Typogre"}, "sequence"),
    ],
)
def test_parse_attack_config_rejects_invalid_payload(payload, message):
    with pytest.raises(ValueError) as excinfo:
        parse_attack_config(payload, source="test")
    assert message in str(excinfo.value)

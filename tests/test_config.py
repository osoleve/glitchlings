import io
import textwrap
from pathlib import Path

import pytest

from glitchlings import build_gaggle, load_attack_config
from glitchlings.config import (
    CONFIG_ENV_VAR,
    DEFAULT_ATTACK_SEED,
    LexiconConfig,
    RuntimeConfig,
    get_config,
    parse_attack_config,
    reload_config,
    reset_config,
)
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


def test_get_config_caches_and_reload_invalidate(monkeypatch, tmp_path):
    calls = 0

    def _fake_loader():
        nonlocal calls
        calls += 1
        return RuntimeConfig(lexicon=LexiconConfig(), path=Path(tmp_path / "config.toml"))

    monkeypatch.setattr("glitchlings.config._load_runtime_config", _fake_loader)
    reset_config()

    config_one = get_config()
    config_two = get_config()
    assert config_one is config_two
    assert calls == 1

    reload_config()
    get_config()
    assert calls == 2


def test_get_config_honours_env_override_and_resolves_relative_paths(monkeypatch, tmp_path):
    config_path = tmp_path / "custom.toml"
    config_path.write_text(
        "[lexicon]\npriority = [\"vector\"]\nvector_cache = \"vector.json\"\n"
        "graph_cache = \"graph.json\"\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_ENV_VAR, str(config_path))
    reset_config()
    try:
        config = get_config()
    finally:
        reset_config()
        monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)

    assert config.path == config_path
    assert config.lexicon.vector_cache == (config_path.parent / "vector.json").resolve()
    assert config.lexicon.graph_cache == (config_path.parent / "graph.json").resolve()


def test_get_config_rejects_non_sequence_priority(monkeypatch, tmp_path):
    config_path = tmp_path / "bad_priority.toml"
    config_path.write_text(
        "[lexicon]\npriority = \"vector\"\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_ENV_VAR, str(config_path))
    reset_config()
    try:
        with pytest.raises(ValueError, match="priority must be a sequence"):
            get_config()
    finally:
        reset_config()
        monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)


def test_load_attack_config_errors_for_missing_file(tmp_path):
    missing = tmp_path / "nope.yaml"
    with pytest.raises(ValueError, match="was not found"):
        load_attack_config(missing)


def test_load_attack_config_surfaces_yaml_errors(tmp_path):
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text("glitchlings: [Typogre", encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to parse"):
        load_attack_config(bad_path)


def test_load_attack_config_requires_integer_seed(tmp_path):
    bad_seed = tmp_path / "bad-seed.yaml"
    bad_seed.write_text(
        "seed: not_an_int\nglitchlings:\n  - Typogre\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Seed in"):
        load_attack_config(bad_seed)


def test_load_attack_config_supports_parameters_section() -> None:
    yaml_stream = io.StringIO(
        textwrap.dedent(
            """
            seed: 11
            glitchlings:
              - name: Typogre
                parameters:
                  rate: 0.05
                  keyboard: COLEMAK
              - type: Rushmore
                parameters:
                  max_deletion_rate: 0.15
                  unweighted: true
            """
        )
    )
    config = load_attack_config(yaml_stream)

    assert config.seed == 11
    assert len(config.glitchlings) == 2

    first, second = config.glitchlings
    assert isinstance(first, Typogre)
    assert pytest.approx(first.kwargs["rate"], rel=1e-6) == 0.05
    assert first.kwargs["keyboard"] == "COLEMAK"

    assert second.name == "Rushmore"
    assert pytest.approx(second.kwargs["rate"], rel=1e-6) == 0.15
    assert second.kwargs["unweighted"] is True


def test_load_attack_config_parameters_must_be_mapping() -> None:
    yaml_stream = io.StringIO(
        textwrap.dedent(
            """
            glitchlings:
              - name: Typogre
                parameters: 1
            """
        )
    )
    with pytest.raises(ValueError, match="parameters must be a mapping"):
        load_attack_config(yaml_stream)

from __future__ import annotations

import runpy
import subprocess
from types import SimpleNamespace

import pytest


def load_module() -> dict[str, object]:
    return runpy.run_path("docs/build_cli_reference.py")


def test_run_cli_propagates_missing_command(monkeypatch):
    module = load_module()
    run_cli = module["run_cli"]

    def fake_run(argv, *, stdout, stderr, text, check, env=None):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FileNotFoundError):
        run_cli(["glitchlings", "--help"])


def test_run_cli_sets_columns_when_command_available(monkeypatch):
    module = load_module()
    run_cli = module["run_cli"]

    recorded_envs: list[dict[str, str] | None] = []

    def fake_run(argv, *, stdout, stderr, text, check, env=None):  # type: ignore[no-untyped-def]
        recorded_envs.append(env)
        return SimpleNamespace(stdout="ready\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_cli(["glitchlings", "--help"])

    assert result == "ready"
    assert recorded_envs and recorded_envs[0] is not None
    assert recorded_envs[0]["COLUMNS"] == "80"

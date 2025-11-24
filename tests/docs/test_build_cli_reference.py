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


def test_build_cli_reference_includes_truncated_help(monkeypatch):
    module = load_module()

    recorded_commands: list[list[str]] = []

    def fake_run_cli(command: list[str]) -> str:
        recorded_commands.append(command)
        if command[-1] == "--list":
            return "typogre\nmim1c"
        return "usage: __main__.py\nfirst line\nsecond line\nthird line"

    globals_namespace = module["build_cli_reference"].__globals__
    globals_namespace["run_cli"] = fake_run_cli
    globals_namespace["HELP_PREVIEW_LINES"] = 2

    result = module["build_cli_reference"]()

    assert recorded_commands == [["glitchlings", "--list"], ["glitchlings", "--help"]]
    assert "typogre" in result
    assert "usage: glitchlings" in result
    assert "first line" in result
    assert "second line" not in result
    assert "..." in result

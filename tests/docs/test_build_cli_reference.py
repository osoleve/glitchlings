from __future__ import annotations

import os
import runpy
import subprocess
import sys
from types import SimpleNamespace


def load_module() -> dict[str, object]:
    return runpy.run_path("docs/build_cli_reference.py")


def test_run_cli_falls_back_to_module_invocation(monkeypatch):
    module = load_module()
    run_cli = module["run_cli"]

    calls: list[list[str]] = []
    envs: list[dict[str, str] | None] = []

    def fake_run(argv, *, stdout, stderr, text, check, env=None):  # type: ignore[no-untyped-def]
        calls.append(argv)
        envs.append(env)
        if len(calls) == 1:
            raise FileNotFoundError
        assert argv[0] == sys.executable
        assert argv[1:3] == ["-m", "glitchlings"]
        return SimpleNamespace(stdout="payload\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_cli(["glitchlings", "--list"])

    assert result == "payload"
    assert calls == [
        ["glitchlings", "--list"],
        [sys.executable, "-m", "glitchlings", "--list"],
    ]
    assert envs and all(env is not None for env in envs)
    assert {env["COLUMNS"] for env in envs if env} == {"80"}


def test_run_cli_fallback_adds_src_to_pythonpath(monkeypatch):
    module = load_module()
    run_cli = module["run_cli"]

    envs: list[dict[str, str] | None] = []

    def fake_run(argv, *, stdout, stderr, text, check, env=None):  # type: ignore[no-untyped-def]
        if argv[0] == "glitchlings":
            raise FileNotFoundError
        envs.append(env)
        return SimpleNamespace(stdout="ok\n")

    monkeypatch.setenv("PYTHONPATH", "/custom")
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_cli(["glitchlings", "--help"])

    assert result == "ok"
    assert envs and envs[0] is not None
    fallback_env = envs[0]
    src_path = str(module["ROOT"] / "src")
    pieces = fallback_env["PYTHONPATH"].split(os.pathsep)
    assert pieces[0] == src_path
    assert "/custom" in pieces[1:]
    assert fallback_env["COLUMNS"] == "80"


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

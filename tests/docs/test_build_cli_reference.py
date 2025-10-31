from __future__ import annotations

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

    def fake_run(argv, *, stdout, stderr, text, check):  # type: ignore[no-untyped-def]
        calls.append(argv)
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

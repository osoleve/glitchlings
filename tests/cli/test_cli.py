from __future__ import annotations

import argparse
import difflib
import json

import pytest
import yaml

from glitchlings import SAMPLE_TEXT, Typogre, summon
from glitchlings.conf import DEFAULT_ATTACK_SEED, build_gaggle, load_attack_config
from glitchlings.main import (
    BUILTIN_GLITCHLINGS,
    DEFAULT_GLITCHLING_NAMES,
    MAX_NAME_WIDTH,
    build_parser,
    read_text,
    run_cli,
)


def invoke_cli(arguments: list[str]):
    parser = build_parser()
    args = parser.parse_args(arguments)
    exit_code = run_cli(args, parser)
    return exit_code


def _effective_seed(args: argparse.Namespace) -> int:
    return args.seed if args.seed is not None else DEFAULT_ATTACK_SEED


def render_expected_list_output() -> str:
    lines = []
    for key in DEFAULT_GLITCHLING_NAMES:
        glitchling = BUILTIN_GLITCHLINGS[key]
        scope = glitchling.level.name.title()
        order = glitchling.order.name.lower()
        lines.append(f"{glitchling.name:>{MAX_NAME_WIDTH}} — scope: {scope}, order: {order}")
    return "\n".join(lines) + "\n"


def render_expected_corruption(text: str, seed: int = 151) -> str:
    gaggle = summon(DEFAULT_GLITCHLING_NAMES, seed=seed)
    return gaggle(text)


def test_run_cli_lists_glitchlings(capsys):
    exit_code = invoke_cli(["--list"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == render_expected_list_output()
    assert captured.err == ""


def test_run_cli_outputs_corrupted_sample_text(monkeypatch, capsys):
    class DummyStdin:
        def isatty(self):
            return True

        def read(self):
            raise AssertionError("stdin should not be read when running with --sample")

    monkeypatch.setattr("sys.stdin", DummyStdin())

    parser = build_parser()
    args = parser.parse_args(["--sample"])
    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()
    assert exit_code == 0
    expected = render_expected_corruption(SAMPLE_TEXT, seed=_effective_seed(args))
    assert captured.out == expected + "\n"
    assert captured.err == ""


def test_run_cli_diff_mode(capsys):
    parser = build_parser()
    args = parser.parse_args(["--diff", "Hello, world!"])
    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()
    assert exit_code == 0
    original = "Hello, world!"
    corrupted = render_expected_corruption(original, seed=_effective_seed(args))
    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            corrupted.splitlines(keepends=True),
            fromfile="original",
            tofile="corrupted",
            lineterm="",
        )
    )
    if diff_lines:
        expected = "".join(f"{line}\n" for line in diff_lines)
    else:
        expected = "No changes detected.\n"
    assert captured.out == expected
    assert captured.err == ""


def test_run_cli_reads_text_from_file(tmp_path, capsys):
    input_text = "Corrupt me, glitchlings!"
    file_path = tmp_path / "input.txt"
    file_path.write_text(input_text, encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(["--input-file", str(file_path)])
    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()
    assert exit_code == 0
    expected = render_expected_corruption(input_text, seed=_effective_seed(args))
    assert captured.out == expected + "\n"
    assert captured.err == ""


def test_read_text_reports_missing_file(tmp_path, capsys):
    parser = build_parser()
    missing = tmp_path / "missing.txt"
    args = parser.parse_args(["--input-file", str(missing)])
    with pytest.raises(SystemExit):
        read_text(args, parser)
    captured = capsys.readouterr()
    assert "No such file or directory" in captured.err
    assert str(missing) in captured.err


def test_read_text_requires_input(monkeypatch, capsys):
    parser = build_parser()
    args = parser.parse_args([])

    class DummyStdin:
        def isatty(self):
            return True

        def read(self):
            raise AssertionError("read should not be called when stdin is a tty")

    monkeypatch.setattr("sys.stdin", DummyStdin())

    with pytest.raises(SystemExit):
        read_text(args, parser)
    captured = capsys.readouterr()
    assert "No input text provided" in captured.err


def test_read_text_consumes_stdin(monkeypatch):
    parser = build_parser()
    args = parser.parse_args([])

    sentinel = "stdin payload"

    class DummyStdin:
        def isatty(self):
            return False

        def read(self):
            return sentinel

    monkeypatch.setattr("sys.stdin", DummyStdin())

    assert read_text(args, parser) == sentinel


def test_run_cli_configured_glitchling_matches_library(capsys):
    parser = build_parser()
    args = parser.parse_args(["-g", "Typogre(rate=0.2)", "Hello there"])

    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()

    configured = Typogre(rate=0.2)
    expected = summon([configured], seed=_effective_seed(args))("Hello there")

    assert exit_code == 0
    assert captured.out == expected + "\n"
    assert captured.err == ""


def test_run_cli_rejects_positional_glitchling_arguments(capsys):
    parser = build_parser()
    args = parser.parse_args(["-g", "Typogre(0.2)", "payload"])

    with pytest.raises(SystemExit):
        run_cli(args, parser)

    captured = capsys.readouterr()
    assert "keyword arguments" in captured.err


def test_run_cli_uses_yaml_config(tmp_path, capsys):
    config_path = tmp_path / "attack.yaml"
    config_path.write_text(
        "seed: 12\nglitchlings:\n  - name: Typogre\n    rate: 0.02\n",
        encoding="utf-8",
    )
    parser = build_parser()
    args = parser.parse_args(["--config", str(config_path), "Hello there"])

    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()

    config = load_attack_config(config_path)
    expected = build_gaggle(config)("Hello there")

    assert exit_code == 0
    assert captured.out == expected + "\n"
    assert captured.err == ""


def test_run_cli_seed_overrides_config(tmp_path, capsys):
    config_path = tmp_path / "attack.yaml"
    config_path.write_text(
        "seed: 3\nglitchlings:\n  - name: Typogre\n    rate: 0.02\n",
        encoding="utf-8",
    )
    parser = build_parser()
    args = parser.parse_args(["--config", str(config_path), "--seed", "9", "Hello there"])

    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()

    config = load_attack_config(config_path)
    expected = build_gaggle(config, seed_override=9)("Hello there")

    assert exit_code == 0
    assert captured.out == expected + "\n"
    assert captured.err == ""


def test_run_cli_rejects_mixed_config_and_glitchling(tmp_path, capsys):
    config_path = tmp_path / "attack.yaml"
    config_path.write_text("glitchlings:\n  - Typogre\n", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(["--config", str(config_path), "--glitchling", "Typogre", "payload"])

    with pytest.raises(SystemExit):
        run_cli(args, parser)

    captured = capsys.readouterr()
    assert "Cannot combine --config with --glitchling" in captured.err


def test_run_cli_report_outputs_json(monkeypatch, capsys):
    class DummyStdin:
        def isatty(self):
            return True

        def read(self):
            raise AssertionError("stdin should not be read when running with --sample")

    monkeypatch.setattr("sys.stdin", DummyStdin())

    exit_code = invoke_cli(["--report", "--format", "json", "--sample"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["tokenizer"]
    assert payload["metrics"]
    assert payload["token_counts"]["input"]["total"] >= 0
    assert payload["token_counts"]["output"]["total"] >= 0
    assert "summary" not in payload  # summary should not be included


def test_run_cli_report_outputs_yaml(monkeypatch, capsys):
    class DummyStdin:
        def isatty(self):
            return True

        def read(self):
            raise AssertionError("stdin should not be read when running with --sample")

    monkeypatch.setattr("sys.stdin", DummyStdin())

    exit_code = invoke_cli(["--report", "--format", "yaml", "--sample"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = yaml.safe_load(captured.out)
    assert "metrics" in payload
    assert "summary" not in payload  # summary should not be included
    assert payload["token_counts"]["input"]["per_sample"]


def test_run_cli_rejects_report_with_diff(capsys):
    parser = build_parser()
    args = parser.parse_args(["--diff", "--report", "payload"])

    with pytest.raises(SystemExit):
        run_cli(args, parser)

    captured = capsys.readouterr()
    assert "--report/--attack" in captured.err


def test_run_cli_attack_with_tokenizer(monkeypatch, capsys):
    # Skip if tiktoken is not installed
    tiktoken = pytest.importorskip("tiktoken")

    class DummyStdin:
        def isatty(self):
            return True

        def read(self):
            raise AssertionError("stdin should not be read when running with --sample")

    monkeypatch.setattr("sys.stdin", DummyStdin())

    exit_code = invoke_cli(["--attack", "--tokenizer", "cl100k_base", "--sample"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert "cl100k_base" in payload["tokenizer"]
    assert payload["metrics"]


def test_run_cli_output_file(tmp_path, capsys):
    output_path = tmp_path / "output.txt"
    parser = build_parser()
    args = parser.parse_args(["--output-file", str(output_path), "Hello world"])
    exit_code = run_cli(args, parser)

    assert exit_code == 0
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert content  # Should have some content
    captured = capsys.readouterr()
    assert captured.out == ""  # Nothing should be printed to stdout


def test_run_cli_tokenizer_requires_attack_or_report(capsys):
    parser = build_parser()
    args = parser.parse_args(["--tokenizer", "cl100k_base", "Hello"])

    with pytest.raises(SystemExit):
        run_cli(args, parser)

    captured = capsys.readouterr()
    assert "--tokenizer requires --attack or --report" in captured.err


def test_run_cli_format_requires_attack_or_report(capsys):
    parser = build_parser()
    args = parser.parse_args(["--format", "yaml", "Hello"])

    with pytest.raises(SystemExit):
        run_cli(args, parser)

    captured = capsys.readouterr()
    assert "--format requires --attack or --report" in captured.err


def test_run_cli_diff_cannot_combine_with_output_file(tmp_path, capsys):
    output_path = tmp_path / "output.txt"
    parser = build_parser()
    args = parser.parse_args(["--diff", "--output-file", str(output_path), "Hello"])

    with pytest.raises(SystemExit):
        run_cli(args, parser)

    captured = capsys.readouterr()
    assert "--diff cannot be combined with --output-file" in captured.err

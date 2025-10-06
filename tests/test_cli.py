import difflib

import pytest

from glitchlings import SAMPLE_TEXT, Typogre, summon
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
    expected = render_expected_corruption(SAMPLE_TEXT, seed=args.seed)
    assert captured.out == expected + "\n"
    assert captured.err == ""


def test_run_cli_diff_mode(capsys):
    parser = build_parser()
    args = parser.parse_args(["--diff", "Hello, world!"])
    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()
    assert exit_code == 0
    original = "Hello, world!"
    corrupted = render_expected_corruption(original, seed=args.seed)
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
    args = parser.parse_args(["--file", str(file_path)])
    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()
    assert exit_code == 0
    expected = render_expected_corruption(input_text, seed=args.seed)
    assert captured.out == expected + "\n"
    assert captured.err == ""


def test_read_text_reports_missing_file(tmp_path, capsys):
    parser = build_parser()
    missing = tmp_path / "missing.txt"
    args = parser.parse_args(["--file", str(missing)])
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
    args = parser.parse_args(
        ["-g", "Typogre(max_change_rate=0.2)", "Hello there"]
    )

    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()

    configured = Typogre(max_change_rate=0.2)
    expected = summon([configured], seed=args.seed)("Hello there")

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

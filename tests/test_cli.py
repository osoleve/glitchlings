import argparse
import difflib
import importlib

import pytest

from glitchlings import SAMPLE_TEXT, Typogre, summon
from glitchlings.config import build_gaggle, load_attack_config
from glitchlings.lexicon import Lexicon
from glitchlings.main import (
    BUILTIN_GLITCHLINGS,
    DEFAULT_GLITCHLING_NAMES,
    MAX_NAME_WIDTH,
    build_lexicon_parser,
    build_parser,
    read_text,
    run_build_lexicon,
    run_cli,
    main as cli_main,
)


def invoke_cli(arguments: list[str]):
    parser = build_parser()
    args = parser.parse_args(arguments)
    exit_code = run_cli(args, parser)
    return exit_code


def _effective_seed(args: argparse.Namespace) -> int:
    return args.seed if args.seed is not None else 151


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


def test_cli_build_lexicon_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr("glitchlings.lexicon.vector.main", fake_main)

    exit_code = cli_main(
        [
            "build-lexicon",
            "--source",
            "spacy:en_core_web_md",
            "--output",
            "cache.json",
            "--max-neighbors",
            "20",
            "--min-similarity",
            "0.1",
            "--normalizer",
            "identity",
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert captured["argv"] == [
        "--source",
        "spacy:en_core_web_md",
        "--output",
        "cache.json",
        "--max-neighbors",
        "20",
        "--min-similarity",
        "0.1",
        "--normalizer",
        "identity",
        "--overwrite",
    ]


def test_run_build_lexicon_passes_optional_arguments(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr("glitchlings.lexicon.vector.main", fake_main)

    builder = build_lexicon_parser()
    tokens_path = tmp_path / "tokens.txt"
    tokens_path.write_text("alpha\n", encoding="utf-8")
    output_path = tmp_path / "cache.json"

    args = builder.parse_args(
        [
            "--source",
            "vectors.kv",
            "--output",
            str(output_path),
            "--tokens",
            str(tokens_path),
            "--max-neighbors",
            "25",
            "--min-similarity",
            "0.3",
            "--seed",
            "7",
            "--case-sensitive",
            "--normalizer",
            "identity",
            "--limit",
            "123",
            "--overwrite",
        ]
    )

    exit_code = run_build_lexicon(args)
    assert exit_code == 0
    assert captured["argv"] == [
        "--source",
        "vectors.kv",
        "--output",
        str(output_path),
        "--max-neighbors",
        "25",
        "--min-similarity",
        "0.3",
        "--normalizer",
        "identity",
        "--tokens",
        str(tokens_path),
        "--seed",
        "7",
        "--case-sensitive",
        "--limit",
        "123",
        "--overwrite",
    ]


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
    args = parser.parse_args(["--file", str(file_path)])
    exit_code = run_cli(args, parser)
    captured = capsys.readouterr()
    assert exit_code == 0
    expected = render_expected_corruption(input_text, seed=_effective_seed(args))
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
        ["-g", "Typogre(rate=0.2)", "Hello there"]
    )

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


def test_default_roster_includes_jargoyle_without_wordnet(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("glitchlings.zoo.jargoyle")

    class DummyLexicon(Lexicon):
        def __init__(self) -> None:
            super().__init__()

        def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
            return []

    monkeypatch.setattr(module, "_lexicon_dependencies_available", lambda: False)
    monkeypatch.setattr(module, "WordNetLexicon", None)
    monkeypatch.setattr(module, "get_default_lexicon", lambda seed=None: DummyLexicon())

    zoo_module = importlib.import_module("glitchlings.zoo")
    try:
        reloaded = importlib.reload(zoo_module)
        assert "jargoyle" in reloaded.DEFAULT_GLITCHLING_NAMES
    finally:
        monkeypatch.undo()
        importlib.reload(zoo_module)
        importlib.reload(importlib.import_module("glitchlings"))


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

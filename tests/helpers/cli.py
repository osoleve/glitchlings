"""CLI testing helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path


def invoke_cli(args: list[str], expect_success: bool = True) -> tuple[int, str, str]:
    """Invoke the glitchlings CLI and return (exit_code, stdout, stderr).

    Args:
        args: Command-line arguments to pass to the CLI
        expect_success: If True, assert that exit code is 0

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Raises:
        AssertionError: If expect_success=True and CLI fails

    Example:
        >>> code, out, err = invoke_cli(["--help"])
        >>> assert "usage:" in out.lower()
    """
    result = subprocess.run(
        ["python", "-m", "glitchlings"] + args,
        capture_output=True,
        text=True,
    )

    if expect_success:
        assert result.returncode == 0, (
            f"CLI failed with exit code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    return result.returncode, result.stdout, result.stderr


def cli_with_temp_config(
    config_content: str,
    tmp_path: Path,
    extra_args: list[str],
) -> tuple[int, str, str]:
    """Helper for testing CLI with temporary config files.

    Creates a temporary config file and invokes the CLI with it.

    Args:
        config_content: YAML content to write to config file
        tmp_path: pytest tmp_path fixture or temporary directory
        extra_args: Additional CLI arguments

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Example:
        >>> config = '''
        ... glitchlings:
        ...   - name: typogre
        ...     rate: 0.05
        ... '''
        >>> code, out, err = cli_with_temp_config(config, tmp_path, ["test.txt"])
    """
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content, encoding="utf-8")
    return invoke_cli(["--config", str(config_path)] + extra_args)


def invoke_cli_stdin(
    args: list[str],
    stdin_text: str,
    expect_success: bool = True,
) -> tuple[int, str, str]:
    """Invoke CLI with text on stdin.

    Args:
        args: Command-line arguments
        stdin_text: Text to pass to stdin
        expect_success: If True, assert that exit code is 0

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Example:
        >>> code, out, err = invoke_cli_stdin(["corrupt"], "hello world")
        >>> assert out != "hello world"  # Should be corrupted
    """
    result = subprocess.run(
        ["python", "-m", "glitchlings"] + args,
        input=stdin_text,
        capture_output=True,
        text=True,
    )

    if expect_success:
        assert result.returncode == 0, (
            f"CLI failed with exit code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    return result.returncode, result.stdout, result.stderr

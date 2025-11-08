"""Shared test helpers for the glitchlings test suite."""
from __future__ import annotations

from tests.helpers.assertions import (
    assert_deterministic,
    assert_preserves_length,
    assert_preserves_whitespace_positions,
    assert_rate_bounded,
    assert_text_similarity,
)
from tests.helpers.cli import cli_with_temp_config, invoke_cli, invoke_cli_stdin

__all__ = [
    # Assertion helpers
    "assert_deterministic",
    "assert_rate_bounded",
    "assert_text_similarity",
    "assert_preserves_length",
    "assert_preserves_whitespace_positions",
    # CLI helpers
    "invoke_cli",
    "cli_with_temp_config",
    "invoke_cli_stdin",
]

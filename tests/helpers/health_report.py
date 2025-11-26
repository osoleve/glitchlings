#!/usr/bin/env python
"""Test suite health report generator.

This script analyzes the test suite and produces metrics to maintain test quality.

Usage:
    python -m tests.helpers.health_report
    python tests/helpers/health_report.py

Output includes:
    1. Test count per module
    2. Tests without docstrings
    3. Tests with weak assertions
    4. Fixture usage statistics
    5. Coverage per glitchling
"""

from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TestInfo:
    """Information about a single test function."""

    name: str
    file_path: str
    has_docstring: bool
    assertion_count: int
    uses_fixtures: list[str]
    line_number: int


@dataclass
class HealthReport:
    """Complete health report for the test suite."""

    total_tests: int = 0
    tests_by_module: dict[str, int] = field(default_factory=dict)
    tests_without_docstrings: list[TestInfo] = field(default_factory=list)
    tests_with_weak_assertions: list[TestInfo] = field(default_factory=list)
    fixture_usage: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    glitchling_coverage: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


class TestAnalyzer(ast.NodeVisitor):
    """AST visitor that extracts test information from Python files."""

    # Known pytest fixtures from conftest and fixtures module
    KNOWN_FIXTURES = frozenset(
        {
            "tmp_path",
            "capsys",
            "monkeypatch",
            "sample_text",
            "fresh_glitchling",
            "toy_embeddings",
            "shared_vector_embeddings",
            "torch_stub",
            "mock_spacy_language",
            "mock_gensim_vectors",
            "mock_sentence_transformers",
        }
    )

    # Glitchling names to track coverage for
    GLITCHLINGS = frozenset(
        {
            "typogre",
            "mim1c",
            "rushmore",
            "redactyl",
            "jargoyle",
            "scannequin",
            "zeedub",
            "ekkokin",
            "hokey",
            "spectroll",
            "pedant",
            "apostrofae",
            "aetheria",
        }
    )

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.tests: list[TestInfo] = []
        self.glitchling_mentions: set[str] = set()
        self._current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context for test methods."""
        if node.name.startswith("Test"):
            old_class = self._current_class
            self._current_class = node.name
            self.generic_visit(node)
            self._current_class = old_class
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze test functions."""
        if not node.name.startswith("test_"):
            self.generic_visit(node)
            return

        # Get docstring
        has_docstring = ast.get_docstring(node) is not None

        # Count assertions
        assertion_count = self._count_assertions(node)

        # Get fixture parameters
        fixtures = self._get_fixture_params(node)

        # Check for glitchling mentions in function body
        self._scan_for_glitchlings(node)

        test_name = node.name
        if self._current_class:
            test_name = f"{self._current_class}::{test_name}"

        self.tests.append(
            TestInfo(
                name=test_name,
                file_path=self.file_path,
                has_docstring=has_docstring,
                assertion_count=assertion_count,
                uses_fixtures=fixtures,
                line_number=node.lineno,
            )
        )

        self.generic_visit(node)

    def _count_assertions(self, node: ast.FunctionDef) -> int:
        """Count assertion statements in a function."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                count += 1
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    # pytest.raises, pytest.warns, etc.
                    if child.func.attr in ("raises", "warns", "deprecated_call"):
                        count += 1
                elif isinstance(child.func, ast.Name):
                    # assert_* helpers
                    if child.func.id.startswith("assert"):
                        count += 1
        return count

    def _get_fixture_params(self, node: ast.FunctionDef) -> list[str]:
        """Extract fixture parameters from function signature."""
        fixtures = []
        for arg in node.args.args:
            name = arg.arg
            if name == "self":
                continue
            if name in self.KNOWN_FIXTURES:
                fixtures.append(name)
        return fixtures

    def _scan_for_glitchlings(self, node: ast.FunctionDef) -> None:
        """Scan function body for glitchling references."""
        source = ast.unparse(node)
        source_lower = source.lower()
        for name in self.GLITCHLINGS:
            if name in source_lower:
                self.glitchling_mentions.add(name)


def analyze_test_file(file_path: Path) -> tuple[list[TestInfo], set[str]]:
    """Analyze a single test file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return [], set()

    analyzer = TestAnalyzer(str(file_path))
    analyzer.visit(tree)
    return analyzer.tests, analyzer.glitchling_mentions


def get_module_name(file_path: Path, tests_root: Path) -> str:
    """Extract module name from file path relative to tests root."""
    relative = file_path.relative_to(tests_root)
    parts = list(relative.parts[:-1])  # Remove filename
    if not parts:
        return "root"
    return "/".join(parts)


def generate_report(tests_root: Path) -> HealthReport:
    """Generate a health report for all tests."""
    report = HealthReport()

    test_files = list(tests_root.rglob("test_*.py"))

    for file_path in test_files:
        tests, glitchling_mentions = analyze_test_file(file_path)
        module_name = get_module_name(file_path, tests_root)

        for test in tests:
            report.total_tests += 1

            # Count by module
            report.tests_by_module[module_name] = report.tests_by_module.get(module_name, 0) + 1

            # Track tests without docstrings
            if not test.has_docstring:
                report.tests_without_docstrings.append(test)

            # Track tests with weak assertions (0 or 1)
            if test.assertion_count <= 1:
                report.tests_with_weak_assertions.append(test)

            # Track fixture usage
            for fixture in test.uses_fixtures:
                report.fixture_usage[fixture] += 1

        # Track glitchling coverage
        for glitchling in glitchling_mentions:
            report.glitchling_coverage[glitchling].append(str(file_path))

    return report


def print_report(report: HealthReport, verbose: bool = False) -> None:
    """Print the health report to stdout."""
    print("=" * 70)
    print("GLITCHLINGS TEST SUITE HEALTH REPORT")
    print("=" * 70)
    print()

    # Summary
    print(f"Total tests: {report.total_tests}")
    print(f"Tests without docstrings: {len(report.tests_without_docstrings)}")
    print(f"Tests with weak assertions (<=1): {len(report.tests_with_weak_assertions)}")
    print()

    # Tests by module
    print("-" * 70)
    print("TESTS BY MODULE")
    print("-" * 70)
    for module, count in sorted(report.tests_by_module.items(), key=lambda x: -x[1]):
        print(f"  {module:30} {count:4}")
    print()

    # Fixture usage
    print("-" * 70)
    print("FIXTURE USAGE")
    print("-" * 70)
    for fixture, count in sorted(report.fixture_usage.items(), key=lambda x: -x[1]):
        print(f"  {fixture:30} {count:4} tests")
    print()

    # Glitchling coverage
    print("-" * 70)
    print("GLITCHLING TEST COVERAGE")
    print("-" * 70)
    for glitchling in sorted(TestAnalyzer.GLITCHLINGS):
        files = report.glitchling_coverage.get(glitchling, [])
        count = len(files)
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {glitchling:20} {count:3} files")
    print()

    # Tests without docstrings (summary)
    if report.tests_without_docstrings and verbose:
        print("-" * 70)
        print("TESTS WITHOUT DOCSTRINGS (showing first 20)")
        print("-" * 70)
        for test in report.tests_without_docstrings[:20]:
            rel_path = Path(test.file_path).name
            print(f"  {rel_path}:{test.line_number} {test.name}")
        if len(report.tests_without_docstrings) > 20:
            print(f"  ... and {len(report.tests_without_docstrings) - 20} more")
        print()

    # Tests with weak assertions (summary)
    if report.tests_with_weak_assertions and verbose:
        print("-" * 70)
        print("TESTS WITH WEAK ASSERTIONS (<=1, showing first 20)")
        print("-" * 70)
        for test in report.tests_with_weak_assertions[:20]:
            rel_path = Path(test.file_path).name
            print(
                f"  {rel_path}:{test.line_number} {test.name} ({test.assertion_count} assertions)"
            )
        if len(report.tests_with_weak_assertions) > 20:
            print(f"  ... and {len(report.tests_with_weak_assertions) - 20} more")
        print()

    # Quality score
    print("-" * 70)
    print("QUALITY METRICS")
    print("-" * 70)
    docstring_pct = (
        (report.total_tests - len(report.tests_without_docstrings)) / report.total_tests * 100
        if report.total_tests
        else 0
    )
    strong_assertion_pct = (
        (report.total_tests - len(report.tests_with_weak_assertions)) / report.total_tests * 100
        if report.total_tests
        else 0
    )
    glitchling_coverage_pct = len(report.glitchling_coverage) / len(TestAnalyzer.GLITCHLINGS) * 100

    print(f"  Tests with docstrings:       {docstring_pct:5.1f}%")
    print(f"  Tests with strong assertions: {strong_assertion_pct:5.1f}%")
    print(f"  Glitchling coverage:          {glitchling_coverage_pct:5.1f}%")
    print()


def export_json(report: HealthReport, output_path: Path) -> None:
    """Export report as JSON for CI integration."""
    data: dict[str, Any] = {
        "total_tests": report.total_tests,
        "tests_by_module": report.tests_by_module,
        "tests_without_docstrings_count": len(report.tests_without_docstrings),
        "tests_with_weak_assertions_count": len(report.tests_with_weak_assertions),
        "fixture_usage": dict(report.fixture_usage),
        "glitchling_coverage": {k: len(v) for k, v in report.glitchling_coverage.items()},
        "quality_metrics": {
            "docstring_percentage": (
                (report.total_tests - len(report.tests_without_docstrings))
                / report.total_tests
                * 100
                if report.total_tests
                else 0
            ),
            "strong_assertion_percentage": (
                (report.total_tests - len(report.tests_with_weak_assertions))
                / report.total_tests
                * 100
                if report.total_tests
                else 0
            ),
            "glitchling_coverage_percentage": (
                len(report.glitchling_coverage) / len(TestAnalyzer.GLITCHLINGS) * 100
            ),
        },
    }
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"JSON report written to: {output_path}")


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate test suite health report")
    parser.add_argument(
        "--json",
        type=Path,
        help="Export report as JSON to the specified path",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed lists of tests without docstrings and weak assertions",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=None,
        help="Path to tests directory (default: auto-detect)",
    )
    args = parser.parse_args()

    # Find tests directory
    if args.tests_dir:
        tests_root = args.tests_dir
    else:
        # Try to find tests directory relative to script location or cwd
        script_dir = Path(__file__).parent
        if (script_dir.parent / "conftest.py").exists():
            tests_root = script_dir.parent
        elif (Path.cwd() / "tests").exists():
            tests_root = Path.cwd() / "tests"
        else:
            print("Error: Could not find tests directory", file=sys.stderr)
            return 1

    if not tests_root.exists():
        print(f"Error: Tests directory not found: {tests_root}", file=sys.stderr)
        return 1

    report = generate_report(tests_root)
    print_report(report, verbose=args.verbose)

    if args.json:
        export_json(report, args.json)

    return 0


if __name__ == "__main__":
    sys.exit(main())

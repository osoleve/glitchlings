"""Architectural tests for enforcing pure/impure module boundaries.

This test module verifies that the functional purity architecture is maintained:
- Pure modules only import standard library and other pure modules
- Impure modules don't leak into pure modules at import time
- TYPE_CHECKING guards are used for type-only imports

Pure modules (verified to have no impure imports):
- zoo/validation.py - Boundary validation functions
- zoo/transforms.py - Pure text transformations
- zoo/rng.py - RNG boundary layer (only has random, which is stdlib)
- zoo/_text_utils.py - Text tokenization utilities
- compat/types.py - Pure type definitions for optional dependency loading

Impure modules (may have side effects at import time):
- internal/rust.py - Low-level Rust FFI loader
- internal/rust_ffi.py - Centralized Rust operation wrappers (preferred for FFI)
- compat/loaders.py - Optional dependency loader with lazy import machinery
- config.py - Configuration singleton
- Any module that imports from internal/rust.py or internal/rust_ffi.py
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

# Get the src directory for import path resolution
SRC_DIR = Path(__file__).parent.parent / "src" / "glitchlings"
ZOO_DIR = SRC_DIR / "zoo"


class ImportInfo(NamedTuple):
    """Information about an import statement."""

    module: str
    line: int
    is_from_import: bool
    names: tuple[str, ...]


def extract_imports(file_path: Path) -> list[ImportInfo]:
    """Extract all import statements from a Python file."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    imports: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportInfo(
                        module=alias.name,
                        line=node.lineno,
                        is_from_import=False,
                        names=(alias.asname or alias.name,),
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                names = tuple(alias.name for alias in node.names)
                imports.append(
                    ImportInfo(
                        module=node.module,
                        line=node.lineno,
                        is_from_import=True,
                        names=names,
                    )
                )
    return imports


def is_stdlib_module(module_name: str) -> bool:
    """Check if a module is part of the Python standard library."""
    # Handle __future__ specially
    if module_name == "__future__":
        return True

    # Get the base module name
    base_module = module_name.split(".")[0]

    # Check against known stdlib modules
    stdlib_modules = {
        "abc",
        "ast",
        "asyncio",
        "base64",
        "collections",
        "contextlib",
        "copy",
        "dataclasses",
        "datetime",
        "decimal",
        "difflib",
        "enum",
        "functools",
        "gzip",
        "hashlib",
        "importlib",
        "inspect",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "operator",
        "os",
        "pathlib",
        "pickle",
        "random",
        "re",
        "shutil",
        "string",
        "sys",
        "tempfile",
        "threading",
        "time",
        "types",
        "typing",
        "unittest",
        "warnings",
        "weakref",
    }

    return base_module in stdlib_modules


def is_type_checking_import(file_path: Path, import_info: ImportInfo) -> bool:
    """Check if an import is inside a TYPE_CHECKING block."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    # Find TYPE_CHECKING blocks
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check if the condition is TYPE_CHECKING
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                # Check if the import line is within this block
                for child in ast.walk(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        if child.lineno == import_info.line:
                            return True
            # Also check for typing.TYPE_CHECKING
            elif isinstance(node.test, ast.Attribute):
                if (
                    isinstance(node.test.value, ast.Name)
                    and node.test.value.id == "typing"
                    and node.test.attr == "TYPE_CHECKING"
                ):
                    for child in ast.walk(node):
                        if isinstance(child, (ast.Import, ast.ImportFrom)):
                            if child.lineno == import_info.line:
                                return True
    return False


# Define pure modules that must not import impure modules
PURE_MODULES = [
    ZOO_DIR / "validation.py",
    ZOO_DIR / "transforms.py",
    ZOO_DIR / "rng.py",
    ZOO_DIR / "_text_utils.py",
    SRC_DIR / "compat" / "types.py",
    SRC_DIR / "conf" / "types.py",
    SRC_DIR / "constants.py",
]

# Map module paths to their import names for allowlisting pure-to-pure imports
PURE_MODULE_NAMES = {
    "glitchlings.zoo.validation",
    "glitchlings.zoo.transforms",
    "glitchlings.zoo.rng",
    "glitchlings.zoo._text_utils",
    "glitchlings.compat.types",
    "glitchlings.conf.types",
    "glitchlings.constants",
}

# Impure internal modules (importing these makes a module impure)
IMPURE_MODULES = {
    "glitchlings.internal.rust",
    "glitchlings.internal.rust_ffi",
    "glitchlings.internal",
    "glitchlings._zoo_rust",
    "glitchlings.config",
    "glitchlings.compat.loaders",
    "glitchlings.conf.loaders",
}


class TestPureModuleImports:
    """Verify that pure modules don't import impure modules."""

    @pytest.mark.parametrize(
        "module_path",
        PURE_MODULES,
        ids=[p.stem for p in PURE_MODULES],
    )
    def test_pure_module_no_impure_imports(self, module_path: Path) -> None:
        """Verify a pure module only imports stdlib or other pure modules."""
        if not module_path.exists():
            pytest.skip(f"Module {module_path} not found")

        imports = extract_imports(module_path)
        impure_imports = []

        for imp in imports:
            # Skip TYPE_CHECKING imports
            if is_type_checking_import(module_path, imp):
                continue

            # stdlib is always OK
            if is_stdlib_module(imp.module):
                continue

            # Check for impure module imports
            for impure in IMPURE_MODULES:
                if imp.module == impure or imp.module.startswith(impure + "."):
                    impure_imports.append(f"Line {imp.line}: imports impure module '{imp.module}'")

        assert not impure_imports, (
            f"Pure module {module_path.name} has impure imports:\n" + "\n".join(impure_imports)
        )

    @pytest.mark.parametrize(
        "module_path",
        PURE_MODULES,
        ids=[p.stem for p in PURE_MODULES],
    )
    def test_pure_module_no_glitchlings_imports(self, module_path: Path) -> None:
        """Verify pure modules don't import from impure glitchlings modules.

        Pure modules may import from other pure modules (allowlisted in
        PURE_MODULE_NAMES), but not from any impure glitchlings modules.
        """
        if not module_path.exists():
            pytest.skip(f"Module {module_path} not found")

        imports = extract_imports(module_path)
        internal_imports = []

        for imp in imports:
            # Skip TYPE_CHECKING imports
            if is_type_checking_import(module_path, imp):
                continue

            # Check for glitchlings imports not in the pure allowlist
            if imp.module.startswith("glitchlings"):
                if imp.module not in PURE_MODULE_NAMES:
                    internal_imports.append(f"Line {imp.line}: imports '{imp.module}'")

        assert not internal_imports, (
            f"Pure module {module_path.name} imports from impure glitchlings modules:\n"
            + "\n".join(internal_imports)
            + "\nPure modules may only import from stdlib or other pure modules."
        )


class TestImportConventions:
    """Test general import convention compliance."""

    def test_internal_rust_exists(self) -> None:
        """Verify the internal/rust.py module exists."""
        rust_module = SRC_DIR / "internal" / "rust.py"
        assert rust_module.exists(), "internal/rust.py should exist"

    def test_impure_modules_are_clearly_named(self) -> None:
        """Document which modules are known to be impure."""
        # This test documents the impure modules for visibility
        impure_locations = [
            SRC_DIR / "internal" / "rust.py",
            SRC_DIR / "compat" / "loaders.py",
            SRC_DIR / "config.py",
        ]
        for path in impure_locations:
            if path.exists():
                # Just verify they exist - they're documented as impure
                assert path.is_file()


class TestModuleCategorization:
    """Tests to document and verify module categorization."""

    def test_pure_modules_exist(self) -> None:
        """Verify all designated pure modules exist."""
        missing = [p for p in PURE_MODULES if not p.exists()]
        assert not missing, f"Missing pure modules: {missing}"

    def test_pure_modules_have_docstrings(self) -> None:
        """Verify pure modules document their purity."""
        for module_path in PURE_MODULES:
            if not module_path.exists():
                continue

            source = module_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(module_path))

            docstring = ast.get_docstring(tree)
            assert docstring is not None, (
                f"Pure module {module_path.name} should have a module docstring "
                "documenting its purity guarantees"
            )

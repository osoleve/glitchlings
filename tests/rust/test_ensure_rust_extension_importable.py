"""Test that _ensure_rust_extension_importable handles import failures gracefully."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_ensure_rust_extension_handles_import_error():
    """Test that _ensure_rust_extension_importable catches ImportError."""
    # Import the test module to access the function
    test_module_path = Path(__file__).parent / "test_rust_backed_glitchlings.py"
    spec = importlib.util.spec_from_file_location("test_module", test_module_path)
    if spec is None or spec.loader is None:
        pytest.skip("Could not load test module")
    
    test_module = importlib.util.module_from_spec(spec)
    
    # Create a mock loader that raises ImportError
    mock_loader = MagicMock()
    mock_loader.exec_module.side_effect = ImportError("Simulated ABI mismatch")
    
    mock_spec = MagicMock()
    mock_spec.loader = mock_loader
    
    # Create a mock artifact
    mock_artifact = MagicMock()
    mock_artifact.parent = Path("/fake/path")
    mock_artifact.stat.return_value.st_mtime = 1000
    
    with patch.object(importlib.util, "find_spec", return_value=None):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=[mock_artifact]):
                with patch.object(
                    importlib.util, "spec_from_file_location", return_value=mock_spec
                ):
                    with patch.object(importlib, "import_module"):
                        with patch.object(
                            importlib.util, "module_from_spec", return_value=MagicMock()
                        ):
                            # This should not raise an exception
                            try:
                                spec.loader.exec_module(test_module)
                                # Call the function
                                test_module._ensure_rust_extension_importable()
                            except ImportError as e:
                                # Should catch ImportError
                                msg = f"_ensure_rust_extension_importable raised: {e}"
                                pytest.fail(msg)


def test_ensure_rust_extension_handles_module_not_found_error():
    """Test that _ensure_rust_extension_importable catches ModuleNotFoundError."""
    # Import the test module to access the function
    test_module_path = Path(__file__).parent / "test_rust_backed_glitchlings.py"
    spec = importlib.util.spec_from_file_location("test_module", test_module_path)
    if spec is None or spec.loader is None:
        pytest.skip("Could not load test module")
    
    test_module = importlib.util.module_from_spec(spec)
    
    # Create a mock loader that raises ModuleNotFoundError
    mock_loader = MagicMock()
    mock_loader.exec_module.side_effect = ModuleNotFoundError("Missing dependency")
    
    mock_spec = MagicMock()
    mock_spec.loader = mock_loader
    
    # Create a mock artifact
    mock_artifact = MagicMock()
    mock_artifact.parent = Path("/fake/path")
    mock_artifact.stat.return_value.st_mtime = 1000
    
    with patch.object(importlib.util, "find_spec", return_value=None):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=[mock_artifact]):
                with patch.object(
                    importlib.util, "spec_from_file_location", return_value=mock_spec
                ):
                    with patch.object(importlib, "import_module"):
                        with patch.object(
                            importlib.util, "module_from_spec", return_value=MagicMock()
                        ):
                            # This should not raise an exception
                            try:
                                spec.loader.exec_module(test_module)
                                # Call the function
                                test_module._ensure_rust_extension_importable()
                            except ModuleNotFoundError as e:
                                # Should catch ModuleNotFoundError
                                msg = f"_ensure_rust_extension_importable raised: {e}"
                                pytest.fail(msg)


def test_glitchlings_importable_without_rust_extension():
    """Test that glitchlings can be imported even when Rust extension is unavailable."""
    # Remove the Rust extension from sys.modules if it exists
    if "glitchlings._zoo_rust" in sys.modules:
        del sys.modules["glitchlings._zoo_rust"]
    
    # This should not raise an exception
    try:
        import glitchlings
        # Verify that basic functionality works
        assert hasattr(glitchlings, "Typogre")
        assert hasattr(glitchlings, "Mim1c")
    except ImportError as e:
        pytest.fail(f"Failed to import glitchlings without Rust extension: {e}")

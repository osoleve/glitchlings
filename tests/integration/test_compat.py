from __future__ import annotations

import sys
from importlib import import_module, metadata
from types import SimpleNamespace

import pytest

from glitchlings import compat


def _force_missing(monkeypatch: pytest.MonkeyPatch, module_name: str) -> None:
    """Simulate a missing dependency regardless of the local environment."""
    monkeypatch.delitem(sys.modules, module_name, raising=False)

    original_import = import_module

    def _raising_import(name: str, *args, **kwargs):
        if name == module_name:
            raise ModuleNotFoundError(f"{module_name} unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(compat, "import_module", _raising_import)


def test_require_datasets_reports_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    compat.reset_optional_dependencies()
    _force_missing(monkeypatch, "datasets")

    with pytest.raises(ModuleNotFoundError, match="datasets is not installed"):
        compat.require_datasets()
    compat.reset_optional_dependencies()


def test_require_verifiers_reports_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    compat.reset_optional_dependencies()
    _force_missing(monkeypatch, "verifiers")

    with pytest.raises(ModuleNotFoundError, match="verifiers is not installed"):
        compat.require_verifiers()
    compat.reset_optional_dependencies()


def test_require_jellyfish_reports_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    compat.reset_optional_dependencies()
    _force_missing(monkeypatch, "jellyfish")

    with pytest.raises(ModuleNotFoundError, match="jellyfish is not installed"):
        compat.require_jellyfish()
    compat.reset_optional_dependencies()


def test_optional_nltk_handles_absence(monkeypatch: pytest.MonkeyPatch) -> None:
    compat.reset_optional_dependencies()
    _force_missing(monkeypatch, "nltk")

    assert compat.nltk.get() is None
    with pytest.raises(ModuleNotFoundError, match="nltk is not installed"):
        compat.nltk.require("nltk is not installed")
    compat.reset_optional_dependencies()


def test_get_installed_extras_reflects_available_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extras = {"prime", "vectors", "dev"}
    requires = [
        'verifiers>=0.1.3.post0; extra == "prime"',
        'jellyfish>=1.2.0; extra == "prime"',
        'numpy>=1.24,<=2.0; extra == "vectors"',
        'spacy>=3.7.2; python_version < "3.14" and extra == "vectors"',
        'gensim>=4.3.2; extra == "vectors"',
        'pytest>=8.0.0; extra == "dev"',
        'hypothesis>=6.140.0; extra == "dev"',
    ]

    available_distributions = {"verifiers", "jellyfish"}

    class _FakeDist:
        def __init__(self, requires: list[str], extras: set[str]) -> None:
            self.requires = requires
            self.metadata = SimpleNamespace(
                get_all=lambda key: list(extras) if key == "Provides-Extra" else []
            )

    def fake_distribution(name: str):
        if name == "glitchlings":
            return _FakeDist(requires, extras)
        if name in available_distributions:
            return object()
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "distribution", fake_distribution)

    result = compat.get_installed_extras(["prime", "vectors", "dev"])
    assert result == {"prime": True, "vectors": False, "dev": False}
    compat.reset_optional_dependencies()

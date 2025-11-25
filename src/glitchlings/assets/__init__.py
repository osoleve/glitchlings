"""Shared asset helpers for Python and Rust consumers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from hashlib import blake2b
from importlib import resources
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Literal, TextIO, cast

try:
    from importlib.resources.abc import Traversable  # Python 3.11+
except ImportError:  # pragma: no cover - Python <3.11
    from importlib_resources.abc import Traversable

AssetKind = Literal["copy", "compressed"]

_DEFAULT_DIGEST_SIZE = 32
_PIPELINE_MANIFEST_NAME = "pipeline_assets.json"


@dataclass(frozen=True)
class PipelineAsset:
    """Descriptor for an asset staged into the Rust build."""

    name: str
    kind: AssetKind = "copy"
    output: str | None = None

    @property
    def staged_name(self) -> str:
        return self.output if self.output is not None else self.name


def _iter_asset_roots() -> Iterable[Traversable]:
    """Yield candidate locations for the shared glitchling asset bundle."""

    package_root: Traversable | None
    try:
        package_root = resources.files(__name__)
    except ModuleNotFoundError:  # pragma: no cover - defensive guard for install issues
        package_root = None
    if package_root is not None and package_root.is_dir():
        yield package_root

    repo_root = Path(__file__).resolve().parents[3] / "assets"
    if repo_root.is_dir():
        yield cast(Traversable, repo_root)


def _asset(name: str) -> Traversable:
    asset_roots = list(_iter_asset_roots())
    for root in asset_roots:
        candidate = root.joinpath(name)
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(root.joinpath(name)) for root in asset_roots) or "<unavailable>"
    raise FileNotFoundError(f"Asset '{name}' not found in: {searched}")


def read_text(name: str, *, encoding: str = "utf-8") -> str:
    """Return the decoded contents of a bundled text asset."""

    return cast(str, _asset(name).read_text(encoding=encoding))


def open_text(name: str, *, encoding: str = "utf-8") -> TextIO:
    """Open a bundled text asset for reading."""

    return cast(TextIO, _asset(name).open("r", encoding=encoding))


def open_binary(name: str) -> BinaryIO:
    """Open a bundled binary asset for reading."""

    return cast(BinaryIO, _asset(name).open("rb"))


def load_json(name: str, *, encoding: str = "utf-8") -> Any:
    """Deserialize a JSON asset using the shared loader helpers."""

    with open_text(name, encoding=encoding) as handle:
        return json.load(handle)


def hash_asset(name: str) -> str:
    """Return a BLAKE2b digest for the bundled asset ``name``."""

    digest = blake2b(digest_size=_DEFAULT_DIGEST_SIZE)
    with open_binary(name) as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


@cache
def load_homophone_groups(name: str = "ekkokin_homophones.json") -> tuple[tuple[str, ...], ...]:
    """Return the curated homophone sets bundled for the Ekkokin glitchling."""

    data: list[list[str]] = load_json(name)
    return tuple(tuple(group) for group in data)


def _parse_pipeline_manifest(raw: Any) -> tuple[PipelineAsset, ...]:
    if not isinstance(raw, dict) or "pipeline_assets" not in raw:
        raise ValueError("pipeline_assets manifest must be a mapping with a 'pipeline_assets' list")

    entries = raw["pipeline_assets"]
    if not isinstance(entries, list):
        raise ValueError("pipeline_assets manifest must contain a list of entries")

    specs: list[PipelineAsset] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("pipeline_assets entries must be objects with a name field")

        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("pipeline_assets entries must supply a non-empty name")

        kind = cast(AssetKind, entry.get("kind", "copy"))
        if kind not in ("copy", "compressed"):
            raise ValueError(f"unsupported asset kind '{kind}' in pipeline manifest")

        output = entry.get("output")
        if output is not None and not isinstance(output, str):
            raise ValueError("pipeline_assets output names must be strings when provided")

        specs.append(PipelineAsset(name=name, kind=kind, output=output))

    return tuple(specs)


@cache
def _load_pipeline_asset_specs() -> tuple[PipelineAsset, ...]:
    manifest = load_json(_PIPELINE_MANIFEST_NAME)
    return _parse_pipeline_manifest(manifest)


PIPELINE_ASSET_SPECS = _load_pipeline_asset_specs()
PIPELINE_ASSETS = frozenset(spec.name for spec in PIPELINE_ASSET_SPECS)


__all__ = [
    "AssetKind",
    "PipelineAsset",
    "PIPELINE_ASSETS",
    "PIPELINE_ASSET_SPECS",
    "read_text",
    "open_text",
    "open_binary",
    "load_json",
    "hash_asset",
    "load_homophone_groups",
]

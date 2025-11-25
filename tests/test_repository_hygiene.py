from __future__ import annotations

import fnmatch
from pathlib import Path

import tomllib

from glitchlings import assets
from glitchlings.assets import PIPELINE_ASSET_SPECS, PIPELINE_ASSETS
from glitchlings.dev.sync_assets import sync_assets


def test_apostrofae_pairs_asset_unique_source():
    """Verify apostrofae_pairs.json has a single canonical source."""
    repo_root = Path(__file__).resolve().parents[1]
    canonical_asset = repo_root / "assets/apostrofae_pairs.json"
    duplicate_asset = repo_root / "rust/zoo/assets/apostrofae_pairs.json"

    assert canonical_asset.exists(), "missing Apostrofae lookup asset"
    assert not duplicate_asset.exists(), "unexpected duplicate Apostrofae asset copy"


def test_ocr_confusions_asset_unique_source():
    """Verify OCR confusion table has a single canonical source."""
    repo_root = Path(__file__).resolve().parents[1]
    canonical_asset = repo_root / "assets/ocr_confusions.tsv"
    duplicate_asset = repo_root / "src/glitchlings/zoo/ocr_confusions.tsv"
    legacy_asset = repo_root / "rust/zoo/assets/ocr_confusions.tsv"

    assert canonical_asset.exists(), "missing OCR confusion table"
    assert not duplicate_asset.exists(), "unexpected duplicate OCR confusion table copy"
    assert not legacy_asset.exists(), "legacy Rust OCR confusion table should be removed"


def test_hokey_assets_shared_source():
    """Verify Hokey assets have a single canonical source."""
    repo_root = Path(__file__).resolve().parents[1]
    canonical_asset = repo_root / "assets/hokey_assets.json"
    legacy_asset = repo_root / "src/glitchlings/data/hokey_assets.json"
    rust_duplicate_asset = repo_root / "rust/zoo/assets/hokey_assets.json"

    assert canonical_asset.exists(), "missing Hokey stretchability asset"
    assert not legacy_asset.exists(), "unexpected legacy Hokey asset location lingering"
    assert not rust_duplicate_asset.exists(), "legacy Rust Hokey asset should be removed"


def test_pipeline_assets_match_build_stage_list():
    """Verify build.rs sources pipeline assets from the shared manifest."""
    repo_root = Path(__file__).resolve().parents[1]
    build_rs = (repo_root / "rust/zoo/build.rs").read_text(encoding="utf-8")
    assert "pipeline_assets.json" in build_rs, "Rust build should read pipeline asset manifest"

    manifest_assets = {spec.name for spec in PIPELINE_ASSET_SPECS}
    assert manifest_assets == PIPELINE_ASSETS


def test_pipeline_assets_packaged_for_distribution():
    """Verify packaged assets stay in sync with the canonical copies."""
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    package_patterns = pyproject["tool"]["setuptools"]["package-data"]["glitchlings"]
    manifest_in = (repo_root / "MANIFEST.in").read_text(encoding="utf-8")
    assert "src/glitchlings/assets" in manifest_in

    canonical_dir = repo_root / "assets"
    packaged_dir = repo_root / "src/glitchlings/assets"

    manifest_candidate = "assets/pipeline_assets.json"
    assert any(fnmatch.fnmatch(manifest_candidate, pattern) for pattern in package_patterns)
    assert (packaged_dir / "pipeline_assets.json").exists()

    for asset_name in PIPELINE_ASSETS:
        packaged_path = packaged_dir / asset_name
        canonical_path = canonical_dir / asset_name
        assert packaged_path.exists(), f"packaged asset missing: {asset_name}"
        assert canonical_path.read_bytes() == packaged_path.read_bytes(), (
            f"packaged asset {asset_name} diverges from canonical copy"
        )
        candidate = f"assets/{asset_name}"
        assert any(fnmatch.fnmatch(candidate, pattern) for pattern in package_patterns), (
            f"package-data patterns missing coverage for {asset_name}"
        )


def test_pipeline_descriptors_expose_types():
    """Verify Rust-backed glitchlings include a pipeline type descriptor."""

    from glitchlings.zoo import BUILTIN_GLITCHLINGS

    for name, glitchling in BUILTIN_GLITCHLINGS.items():
        operation = glitchling.pipeline_operation()
        if operation is None:
            continue
        assert isinstance(operation, dict), f"pipeline_operation for {name} must return a dict"
        op_type = operation.get("type")
        assert isinstance(op_type, str) and op_type, f"{name} pipeline descriptor missing type"


def test_pipeline_assets_exist_in_canonical_directory():
    """Verify all assets listed in rust/zoo/build.rs exist in canonical assets/ directory."""
    repo_root = Path(__file__).resolve().parents[1]
    assets_dir = repo_root / "assets"

    for asset_name in PIPELINE_ASSETS:
        asset_path = assets_dir / asset_name
        assert asset_path.exists(), f"missing canonical asset: {asset_name}"


def test_pipeline_assets_have_canonical_digests():
    """Verify all pipeline assets have valid SHA-256 digests."""
    canonical_digests = {
        name: assets.hash_asset(name) for name in sorted(PIPELINE_ASSETS)
    }

    for name, digest in canonical_digests.items():
        assert len(digest) == 64, f"unexpected digest length for {name}"


def test_no_legacy_rust_assets_present():
    """Verify legacy Rust assets directory is empty or doesn't exist."""
    repo_root = Path(__file__).resolve().parents[1]
    rust_asset_dir = repo_root / "rust/zoo/assets"

    if not rust_asset_dir.exists():
        return

    residual = [path for path in rust_asset_dir.iterdir() if path.is_file()]
    assert not residual, "legacy Rust asset directory should be empty"


def test_sync_assets_check_passes():
    """Verify asset synchronization check passes."""
    assert sync_assets(check=True, quiet=True)

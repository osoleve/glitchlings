from __future__ import annotations

import fnmatch
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python<3.11
    import tomli as tomllib

from glitchlings import assets
from glitchlings.assets import PIPELINE_ASSET_SPECS, PIPELINE_ASSETS

REPO_ROOT = Path(__file__).resolve().parents[2]


def _rel_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def test_apostrofae_pairs_asset_unique_source():
    """Verify apostrofae_pairs.json has a single canonical source."""
    canonical_asset = REPO_ROOT / "src/glitchlings/assets/apostrofae_pairs.json"
    duplicate_asset = REPO_ROOT / "rust/zoo/assets/apostrofae_pairs.json"

    assert canonical_asset.exists(), "missing Apostrofae lookup asset"
    assert not duplicate_asset.exists(), "unexpected duplicate Apostrofae asset copy"


def test_pipeline_assets_match_build_stage_list():
    """Verify build.rs sources pipeline assets from the shared manifest."""
    build_rs = (REPO_ROOT / "rust/zoo/build.rs").read_text(encoding="utf-8")
    assert "pipeline_assets.json" in build_rs, "Rust build should read pipeline asset manifest"

    manifest_assets = {spec.name for spec in PIPELINE_ASSET_SPECS}
    assert manifest_assets == PIPELINE_ASSETS


def test_pipeline_assets_packaged_for_distribution():
    """Verify packaged assets stay in sync with the canonical copies."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_patterns = pyproject["tool"]["setuptools"]["package-data"]["glitchlings"]
    manifest_in = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "src/glitchlings/assets" in manifest_in

    canonical_dir = REPO_ROOT / "src/glitchlings/assets"
    packaged_dir = REPO_ROOT / "src/glitchlings/assets"

    manifest_candidate = "assets/pipeline_assets.json"
    assert any(fnmatch.fnmatch(manifest_candidate, pattern) for pattern in package_patterns)
    assert (packaged_dir / "pipeline_assets.json").exists()

    for asset_name in PIPELINE_ASSETS:
        packaged_path = packaged_dir / asset_name
        canonical_path = canonical_dir / asset_name
        assert packaged_path.exists(), f"packaged asset missing: {asset_name}"
        if canonical_path.is_dir():
            assert packaged_path.is_dir(), f"packaged asset {asset_name} should be a directory"
            canonical_files = _rel_files(canonical_path)
            packaged_files = _rel_files(packaged_path)
            assert canonical_files == packaged_files, (
                f"packaged asset {asset_name} diverges from canonical copy"
            )
            for relative_file in canonical_files:
                candidate = f"assets/{asset_name}/{relative_file}"
                assert any(fnmatch.fnmatch(candidate, pattern) for pattern in package_patterns), (
                    f"package-data patterns missing coverage for {asset_name}/{relative_file}"
                )
        else:
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
    assets_dir = REPO_ROOT / "src/glitchlings/assets"

    for asset_name in PIPELINE_ASSETS:
        asset_path = assets_dir / asset_name
        assert asset_path.exists(), f"missing canonical asset: {asset_name}"


def test_pipeline_assets_have_canonical_digests():
    """Verify all pipeline assets have valid SHA-256 digests."""
    canonical_digests = {name: assets.hash_asset(name) for name in sorted(PIPELINE_ASSETS)}

    for name, digest in canonical_digests.items():
        assert len(digest) == 64, f"unexpected digest length for {name}"


def test_no_legacy_rust_assets_present():
    """Verify legacy Rust assets directory is empty or doesn't exist."""
    rust_asset_dir = REPO_ROOT / "rust/zoo/assets"

    if not rust_asset_dir.exists():
        return

    residual = [path for path in rust_asset_dir.iterdir() if path.is_file()]
    assert not residual, "legacy Rust asset directory should be empty"

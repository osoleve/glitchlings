from __future__ import annotations

from pathlib import Path

import re

from glitchlings.dev.sync_assets import PIPELINE_ASSETS, sync_assets
from glitchlings.zoo import assets


def _load_apostrofae_pairs() -> dict[str, list[list[str]]]:
    return assets.load_json("apostrofae_pairs.json")


def test_apostrofae_pairs_asset_structure():
    data = _load_apostrofae_pairs()

    assert set(data) == {'"', "'", "`"}

    for straight, pairs in data.items():
        assert isinstance(pairs, list), f"expected list for {straight!r} entries"
        assert pairs, f"expected at least one replacement pair for {straight!r}"
        for replacement in pairs:
            assert len(replacement) == 2, f"replacement for {straight!r} must contain two glyphs"
            assert all(isinstance(glyph, str) and glyph for glyph in replacement), (
                "replacement glyphs must be non-empty strings"
            )


def test_apostrofae_pairs_asset_unique_source():
    repo_root = Path(__file__).resolve().parents[2]
    canonical_asset = repo_root / "assets/apostrofae_pairs.json"
    duplicate_asset = repo_root / "rust/zoo/assets/apostrofae_pairs.json"

    assert canonical_asset.exists(), "missing Apostrofae lookup asset"
    assert not duplicate_asset.exists(), "unexpected duplicate Apostrofae asset copy"


def test_ocr_confusions_asset_unique_source():
    repo_root = Path(__file__).resolve().parents[2]
    canonical_asset = repo_root / "assets/ocr_confusions.tsv"
    duplicate_asset = repo_root / "src/glitchlings/zoo/ocr_confusions.tsv"
    legacy_asset = repo_root / "rust/zoo/assets/ocr_confusions.tsv"

    assert canonical_asset.exists(), "missing OCR confusion table"
    assert not duplicate_asset.exists(), "unexpected duplicate OCR confusion table copy"
    assert not legacy_asset.exists(), "legacy Rust OCR confusion table should be removed"


def test_hokey_assets_shared_source():
    repo_root = Path(__file__).resolve().parents[2]
    canonical_asset = repo_root / "assets/hokey_assets.json"
    legacy_asset = repo_root / "src/glitchlings/data/hokey_assets.json"
    rust_duplicate_asset = repo_root / "rust/zoo/assets/hokey_assets.json"

    assert canonical_asset.exists(), "missing Hokey stretchability asset"
    assert not legacy_asset.exists(), "unexpected legacy Hokey asset location lingering"
    assert not rust_duplicate_asset.exists(), "legacy Rust Hokey asset should be removed"


def test_pipeline_assets_match_build_stage_list():
    repo_root = Path(__file__).resolve().parents[2]
    build_rs = (repo_root / "rust/zoo/build.rs").read_text(encoding="utf-8")
    staged_assets = set(re.findall(r'stage_asset\("([^"]+)"\)', build_rs))
    assert staged_assets == PIPELINE_ASSETS


def test_pipeline_assets_have_canonical_digests():
    canonical_digests = {
        name: assets.hash_asset(name) for name in sorted(PIPELINE_ASSETS)
    }

    for name, digest in canonical_digests.items():
        assert len(digest) == 64, f"unexpected digest length for {name}"


def test_no_legacy_rust_assets_present():
    repo_root = Path(__file__).resolve().parents[2]
    rust_asset_dir = repo_root / "rust/zoo/assets"

    if not rust_asset_dir.exists():
        return

    residual = [path for path in rust_asset_dir.iterdir() if path.is_file()]
    assert not residual, "legacy Rust asset directory should be empty"


def test_sync_assets_check_passes():
    assert sync_assets(check=True, quiet=True)

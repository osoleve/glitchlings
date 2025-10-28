from __future__ import annotations

import hashlib
from pathlib import Path

from glitchlings.dev.sync_assets import RUST_VENDORED_ASSETS, sync_assets
from glitchlings.zoo import assets


def _load_apostrofae_pairs() -> dict[str, list[list[str]]]:
    return assets.load_json("apostrofae_pairs.json")


def _hash_path(path: Path) -> str:
    digest = hashlib.blake2b(digest_size=32)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    canonical_asset = repo_root / "src/glitchlings/zoo/assets/apostrofae_pairs.json"
    duplicate_asset = repo_root / "rust/zoo/assets/apostrofae_pairs.json"

    assert canonical_asset.exists(), "missing Apostrofae lookup asset"
    assert not duplicate_asset.exists(), "unexpected duplicate Apostrofae asset copy"


def test_ocr_confusions_asset_unique_source():
    repo_root = Path(__file__).resolve().parents[2]
    canonical_asset = repo_root / "src/glitchlings/zoo/assets/ocr_confusions.tsv"
    duplicate_asset = repo_root / "src/glitchlings/zoo/ocr_confusions.tsv"
    rust_packaged_asset = repo_root / "rust/zoo/assets/ocr_confusions.tsv"

    assert canonical_asset.exists(), "missing OCR confusion table"
    assert not duplicate_asset.exists(), "unexpected duplicate OCR confusion table copy"
    assert rust_packaged_asset.exists(), "missing staged OCR confusion table for Rust"
    canonical_digest = assets.hash_asset("ocr_confusions.tsv")
    assert canonical_digest == _hash_path(rust_packaged_asset), (
        "Rust packaged OCR confusion table diverges from canonical asset",
    )


def test_hokey_assets_shared_source():
    repo_root = Path(__file__).resolve().parents[2]
    canonical_asset = repo_root / "src/glitchlings/zoo/assets/hokey_assets.json"
    legacy_asset = repo_root / "src/glitchlings/data/hokey_assets.json"
    rust_packaged_asset = repo_root / "rust/zoo/assets/hokey_assets.json"

    assert canonical_asset.exists(), "missing Hokey stretchability asset"
    assert not legacy_asset.exists(), "unexpected legacy Hokey asset location lingering"
    assert rust_packaged_asset.exists(), "missing staged Hokey asset for Rust"
    canonical_digest = assets.hash_asset("hokey_assets.json")
    assert canonical_digest == _hash_path(rust_packaged_asset), (
        "Rust packaged Hokey asset diverges from canonical asset",
    )


def test_vendored_assets_match_canonical_digests():
    repo_root = Path(__file__).resolve().parents[2]
    rust_asset_dir = repo_root / "rust/zoo/assets"

    canonical_digests = {
        name: assets.hash_asset(name)
        for name in sorted(RUST_VENDORED_ASSETS)
    }

    for name, canonical_digest in canonical_digests.items():
        staged_path = rust_asset_dir / name
        assert staged_path.exists(), f"missing staged asset {name}"
        assert canonical_digest == _hash_path(staged_path), (
            f"vendored asset {name} diverges from canonical digest",
        )


def test_sync_assets_check_passes():
    assert sync_assets(check=True, quiet=True)

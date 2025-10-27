from __future__ import annotations

import json
from pathlib import Path

from glitchlings.zoo import assets


def _load_apostrofae_pairs() -> dict[str, list[list[str]]]:
    with assets.open_text("apostrofae_pairs.json") as handle:
        return json.load(handle)


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
    assert canonical_asset.read_text(encoding="utf-8") == rust_packaged_asset.read_text(encoding="utf-8"), (
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
    assert canonical_asset.read_text(encoding="utf-8") == rust_packaged_asset.read_text(encoding="utf-8"), (
        "Rust packaged Hokey asset diverges from canonical asset",
    )

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path


def _load_apostrofae_pairs() -> dict[str, list[list[str]]]:
    resource = resources.files("glitchlings.zoo.assets").joinpath("apostrofae_pairs.json")
    with resource.open("r", encoding="utf-8") as handle:
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

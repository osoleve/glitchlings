from __future__ import annotations

from glitchlings.zoo import assets


def _load_apostrofae_pairs() -> dict[str, list[list[str]]]:
    return assets.load_json("apostrofae_pairs.json")


def test_apostrofae_pairs_asset_structure():
    """Test the structure and content of apostrofae_pairs.json."""
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

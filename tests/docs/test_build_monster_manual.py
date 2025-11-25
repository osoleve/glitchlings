from __future__ import annotations

import runpy


def load_module() -> dict[str, object]:
    return runpy.run_path("docs/build_monster_manual.py")


def test_build_monster_manual_includes_flavor_and_params():
    module = load_module()
    build_manual = module["build_monster_manual"]

    result = build_manual()  # type: ignore[operator]

    assert "## Typogre" in result
    assert "## Pedant" in result
    assert "Scope:" in result
    assert "rate` (float" in result
    assert '*"Resurrects archaic ligatures and diacritics."*' in result

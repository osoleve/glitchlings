"""Synchronise canonical glitchling assets with the vendored Rust copies."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable, Sequence

RUST_VENDORED_ASSETS: frozenset[str] = frozenset({
    "hokey_assets.json",
    "ocr_confusions.tsv",
})


def _project_root(default: Path | None = None) -> Path:
    if default is not None:
        return default
    return Path(__file__).resolve().parents[3]


def _canonical_asset_dir(project_root: Path) -> Path:
    canonical = project_root / "src" / "glitchlings" / "zoo" / "assets"
    if not canonical.is_dir():
        raise RuntimeError(
            "expected canonical assets under 'src/glitchlings/zoo/assets'; "
            "run this command from the repository root"
        )
    return canonical


def _rust_asset_dir(project_root: Path) -> Path:
    return project_root / "rust" / "zoo" / "assets"


def _iter_extraneous_assets(rust_dir: Path) -> Iterable[Path]:
    if not rust_dir.exists():
        return ()
    for path in rust_dir.iterdir():
        if path.is_file() and path.name not in RUST_VENDORED_ASSETS:
            yield path


def sync_assets(
    project_root: Path | None = None,
    *,
    check: bool = False,
    quiet: bool = False,
) -> bool:
    """Synchronise the vendored Rust asset copies with the canonical sources."""

    root = _project_root(project_root)
    canonical_dir = _canonical_asset_dir(root)
    rust_dir = _rust_asset_dir(root)

    missing_sources = [name for name in RUST_VENDORED_ASSETS if not (canonical_dir / name).is_file()]
    if missing_sources:
        missing_list = ", ".join(sorted(missing_sources))
        raise RuntimeError(f"missing canonical assets: {missing_list}")

    extraneous = list(_iter_extraneous_assets(rust_dir))

    mismatched: list[tuple[str, str]] = []
    for name in sorted(RUST_VENDORED_ASSETS):
        source = canonical_dir / name
        target = rust_dir / name
        if not target.exists():
            mismatched.append((name, "missing"))
            continue
        if source.read_bytes() != target.read_bytes():
            mismatched.append((name, "outdated"))

    if check:
        if mismatched or extraneous:
            if not quiet:
                for name, reason in mismatched:
                    target = rust_dir / name
                    print(
                        f"{target.relative_to(root)} is {reason}; run sync_assets to refresh it",
                        file=sys.stderr,
                    )
                for extra in extraneous:
                    print(
                        f"unexpected vendored asset {extra.relative_to(root)}; run sync_assets to prune it",
                        file=sys.stderr,
                    )
            return False
        if not quiet:
            print("Rust asset bundle is up to date.")
        return True

    rust_dir.mkdir(parents=True, exist_ok=True)

    for name, reason in mismatched:
        source = canonical_dir / name
        target = rust_dir / name
        shutil.copy2(source, target)
        if not quiet:
            verb = "Copied" if reason == "missing" else "Updated"
            print(
                f"{verb} {source.relative_to(root)} -> {target.relative_to(root)}",
            )

    for extra in extraneous:
        extra.unlink()
        if not quiet:
            print(f"Removed extraneous vendored asset {extra.relative_to(root)}")

    if not mismatched and not extraneous and not quiet:
        print("Rust asset bundle already aligned with canonical copies.")

    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Synchronise canonical glitchling assets with the vendored Rust copies.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with a non-zero status when vendored assets diverge",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress status output",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="override the detected project root (useful for testing)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ok = sync_assets(project_root=args.project_root, check=args.check, quiet=args.quiet)
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

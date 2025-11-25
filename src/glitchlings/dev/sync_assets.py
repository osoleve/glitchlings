"""Maintain the canonical glitchling asset bundle shared by Python and Rust."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterator, Sequence

from glitchlings.assets import PIPELINE_ASSETS


def _project_root(default: Path | None = None) -> Path:
    if default is not None:
        return default
    return Path(__file__).resolve().parents[3]


def _canonical_asset_dir(project_root: Path) -> Path:
    canonical = project_root / "assets"
    if not canonical.is_dir():
        raise RuntimeError(
            "expected canonical assets under 'assets'; run this command from the repository root"
        )
    return canonical


def _package_asset_dir(project_root: Path) -> Path:
    return project_root / "src" / "glitchlings" / "assets"


def _legacy_rust_asset_dir(project_root: Path) -> Path:
    return project_root / "rust" / "zoo" / "assets"


def _iter_legacy_assets(rust_dir: Path) -> Iterator[Path]:
    if not rust_dir.exists():
        return
    for path in rust_dir.iterdir():
        if path.is_file():
            yield path


def _asset_copy_in_sync(source: Path, target: Path) -> bool:
    return target.is_file() and source.read_bytes() == target.read_bytes()


def sync_assets(
    project_root: Path | None = None,
    *,
    check: bool = False,
    quiet: bool = False,
) -> bool:
    """Ensure pipeline assets exist only at their canonical location."""

    root = _project_root(project_root)
    canonical_dir = _canonical_asset_dir(root)
    package_dir = _package_asset_dir(root)
    rust_dir = _legacy_rust_asset_dir(root)

    missing_sources = [name for name in PIPELINE_ASSETS if not (canonical_dir / name).is_file()]
    if missing_sources:
        missing_list = ", ".join(sorted(missing_sources))
        raise RuntimeError(f"missing canonical assets: {missing_list}")

    if not check:
        package_dir.mkdir(parents=True, exist_ok=True)

    legacy_assets = list(_iter_legacy_assets(rust_dir))
    stale_package_assets = [
        name
        for name in PIPELINE_ASSETS
        if not _asset_copy_in_sync(canonical_dir / name, package_dir / name)
    ]

    if check:
        issues_found = False
        if legacy_assets:
            issues_found = True
            if not quiet:
                for duplicate in legacy_assets:
                    message = (
                        "legacy vendored asset "
                        f"{duplicate.relative_to(root)} still exists; "
                        "run sync_assets to remove it"
                    )
                    print(message, file=sys.stderr)
        if stale_package_assets:
            issues_found = True
            if not quiet:
                for name in stale_package_assets:
                    message = (
                        f"packaged asset copy {name} is missing or stale; "
                        "run sync_assets to refresh src/glitchlings/assets"
                    )
                    print(message, file=sys.stderr)
        if not issues_found and not quiet:
            print("No legacy Rust asset copies detected.")
            print("Packaged asset copies are up to date.")
        return not issues_found

    removed_any = False
    for duplicate in legacy_assets:
        duplicate.unlink()
        removed_any = True
        if not quiet:
            print(f"Removed legacy vendored asset {duplicate.relative_to(root)}")

    if removed_any:
        try:
            rust_dir.rmdir()
        except OSError:
            pass
    elif not quiet:
        print("No legacy Rust asset copies to remove.")

    updated_any = False
    for name in stale_package_assets:
        shutil.copy2(canonical_dir / name, package_dir / name)
        updated_any = True
        if not quiet:
            print(f"Refreshed packaged asset copy for {name}")

    if not updated_any and not quiet:
        print("Packaged asset copies already up to date.")

    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prune legacy vendored Rust assets so only canonical copies remain.",
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

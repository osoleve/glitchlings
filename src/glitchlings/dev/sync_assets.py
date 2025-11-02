"""Maintain the canonical glitchling asset bundle shared by Python and Rust."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path
from typing import Iterator, Sequence

PIPELINE_ASSETS: frozenset[str] = frozenset(
    {
        "apostrofae_pairs.json",
        "ekkokin_homophones.json",
        "hokey_assets.json",
        "ocr_confusions.tsv",
    }
)


def _project_root(default: Path | None = None) -> Path:
    if default is not None:
        return default
    return Path(__file__).resolve().parents[3]


def _canonical_asset_dir(project_root: Path) -> Path:
    canonical = project_root / "assets"
    if not canonical.is_dir():
        raise RuntimeError(
            "expected canonical assets under 'assets'; "
            "run this command from the repository root"
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


def sync_assets(
    project_root: Path | None = None,
    *,
    check: bool = False,
    quiet: bool = False,
) -> bool:
    """Ensure pipeline assets exist only at their canonical location."""

    root = _project_root(project_root)
    canonical_dir = _canonical_asset_dir(root)
    rust_dir = _legacy_rust_asset_dir(root)

    missing_sources = [name for name in PIPELINE_ASSETS if not (canonical_dir / name).is_file()]
    if missing_sources:
        missing_list = ", ".join(sorted(missing_sources))
        raise RuntimeError(f"missing canonical assets: {missing_list}")

    legacy_assets = list(_iter_legacy_assets(rust_dir))

    if check:
        package_ok = _check_package_assets(
            canonical_dir, _package_asset_dir(root), quiet=quiet
        )
        if legacy_assets:
            if not quiet:
                for duplicate in legacy_assets:
                    message = (
                        "legacy vendored asset "
                        f"{duplicate.relative_to(root)} still exists; "
                        "run sync_assets to remove it"
                    )
                    print(message, file=sys.stderr)
            return False
        if not quiet:
            print("No legacy Rust asset copies detected.")
        return package_ok

    _ensure_package_assets(canonical_dir, _package_asset_dir(root), quiet=quiet)
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

    return True


def _check_package_assets(
    canonical_dir: Path,
    package_dir: Path,
    *,
    quiet: bool,
) -> bool:
    if package_dir.is_symlink():
        try:
            if package_dir.resolve() == canonical_dir.resolve():
                if not quiet:
                    print("Package asset symlink points at canonical assets.")
                return True
        except OSError:
            pass
        if not quiet:
            message = (
                f"package asset symlink {package_dir} does not target canonical assets"
            )
            print(message, file=sys.stderr)
        return False

    if not package_dir.exists():
        if not quiet:
            print(
                f"package asset directory {package_dir} is missing; "
                "run sync_assets to populate it",
                file=sys.stderr,
            )
        return False

    missing = [
        name for name in PIPELINE_ASSETS if not (package_dir / name).is_file()
    ]
    mismatched = [
        name
        for name in PIPELINE_ASSETS
        if (package_dir / name).is_file()
        and not filecmp.cmp(canonical_dir / name, package_dir / name, shallow=False)
    ]
    extras = [
        path.name
        for path in package_dir.iterdir()
        if path.is_file() and path.name not in PIPELINE_ASSETS
    ]

    if missing and not quiet:
        print(
            "package asset copies are missing: "
            + ", ".join(sorted(missing)),
            file=sys.stderr,
        )
    if mismatched and not quiet:
        print(
            "package asset copies drifted from canonical versions: "
            + ", ".join(sorted(mismatched)),
            file=sys.stderr,
        )
    if extras and not quiet:
        print(
            "package asset directory includes unexpected files: "
            + ", ".join(sorted(extras)),
            file=sys.stderr,
        )

    return not missing and not mismatched and not extras


def _ensure_package_assets(
    canonical_dir: Path,
    package_dir: Path,
    *,
    quiet: bool,
) -> None:
    if package_dir.exists() or package_dir.is_symlink():
        if package_dir.is_symlink():
            try:
                if package_dir.resolve() == canonical_dir.resolve():
                    if not quiet:
                        print("Package asset symlink already up to date.")
                    return
            except OSError:
                pass
            package_dir.unlink()
        elif package_dir.is_dir():
            shutil.rmtree(package_dir)
        else:
            package_dir.unlink()

    try:
        package_dir.symlink_to(canonical_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        package_dir.mkdir(parents=True, exist_ok=True)
        for name in PIPELINE_ASSETS:
            shutil.copy2(canonical_dir / name, package_dir / name)
        if not quiet:
            print("Copied canonical assets into src/glitchlings/assets.")
    else:
        if not quiet:
            print("Linked src/glitchlings/assets to canonical asset directory.")


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

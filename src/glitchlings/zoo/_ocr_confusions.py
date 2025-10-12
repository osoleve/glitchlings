from __future__ import annotations

from importlib import resources

_CONFUSION_TABLE: list[tuple[str, list[str]]] | None = None


def load_confusion_table() -> list[tuple[str, list[str]]]:
    """Load the OCR confusion table shared by Python and Rust implementations."""
    global _CONFUSION_TABLE
    if _CONFUSION_TABLE is not None:
        return _CONFUSION_TABLE

    data = resources.files(__package__) / "ocr_confusions.tsv"
    text = data.read_text(encoding="utf-8")
    indexed_entries: list[tuple[int, tuple[str, list[str]]]] = []
    for line_number, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        source, *replacements = parts
        indexed_entries.append((line_number, (source, replacements)))

    # Sort longer patterns first to avoid overlapping matches, mirroring the
    # behaviour of the Rust `confusion_table` helper.
    indexed_entries.sort(key=lambda item: (-len(item[1][0]), item[0]))
    entries = [entry for _, entry in indexed_entries]
    _CONFUSION_TABLE = entries
    return entries

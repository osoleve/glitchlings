"""Shared constants and helpers for Glitchlings benchmark utilities."""

from __future__ import annotations

import importlib
import os
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List, Tuple
from urllib.parse import urlparse

import requests

from glitchlings.dlc.gutenberg import DEFAULT_GUTENDEX_URL, _get_gutenberg_api
from glitchlings.zoo import get_glitchling_class

Descriptor = Dict[str, object]
CorpusLike = Iterable[tuple[str, str]] | Callable[[], Iterable[tuple[str, str]]]

GUTENBERG_CACHE_DIR = Path(os.getenv("GUTENBERG_CACHE_DIR", ".cache/gutenberg")).expanduser()


@lru_cache(maxsize=None)
def _glitchling_module(name: str) -> ModuleType:
    """Return the module that defines the named glitchling."""
    module_path = get_glitchling_class(name).__module__
    return importlib.import_module(module_path)


def redactyl_full_block() -> str:
    """Expose the Redactyl full block character."""
    return getattr(_glitchling_module("Redactyl"), "FULL_BLOCK")


def zero_width_characters() -> List[str]:
    """Return the default zero-width characters used by Zeedub."""
    characters = getattr(_glitchling_module("Zeedub"), "_DEFAULT_ZERO_WIDTH_CHARACTERS")
    return list(characters)


def keyboard_layout(keyboard: str) -> Dict[str, List[str]]:
    """Return a mutable copy of a named keyboard layout for Typogre."""
    neighbors = getattr(_glitchling_module("Typogre"), "KEYNEIGHBORS")
    layout = getattr(neighbors, keyboard)
    return {key: list(value) for key, value in layout.items()}


def _resolve_book_text(book: Any) -> str:
    """Return the full text for a py-gutenberg Book."""
    book_id = getattr(book, "id", None)
    cache_path = None
    if isinstance(book_id, int) and book_id > 0:
        cache_path = GUTENBERG_CACHE_DIR / f"{book_id}.txt"
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8", errors="ignore")

    if hasattr(book, "get_text"):
        text = book.get_text()  # type: ignore[no-any-return]
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(str(text), encoding="utf-8")
        return text
    text_attr = getattr(book, "text", None)
    if isinstance(text_attr, str):
        return text_attr

    formats = getattr(book, "formats", {}) or {}
    # Prefer plain-text variants, then any text/*
    text_urls = [
        url
        for mime, url in formats.items()
        if isinstance(mime, str) and mime.lower().startswith("text/plain")
    ]
    if not text_urls:
        text_urls = [
            url
            for mime, url in formats.items()
            if isinstance(mime, str) and mime.startswith("text/")
        ]
    if not text_urls:
        raise AttributeError(
            "Project Gutenberg entries must include a text/plain format to download full text."
        )

    url = text_urls[0]
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    # Response may be bytes or text; ensure str.
    if not isinstance(response.text, str):
        parsed = urlparse(url)
        raise ValueError(f"Failed to decode Project Gutenberg text from {parsed.netloc}")

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(response.text, encoding="utf-8")
    return response.text


OPERATION_MODULES: Dict[str, str] = {
    "reduplicate": "Rushmore",
    "delete": "Rushmore",
    "redact": "Redactyl",
    "ocr": "Scannequin",
    "zwj": "Zeedub",
    "swap_adjacent": "Rushmore",
    "typo": "Typogre",
    "hokey": "Hokey",
    "pedant": "Pedant",
    "wherewolf": "Wherewolf",
    "rushmore_combo": "Rushmore",
    "homoglyph": "Mim1c",
    "synonym": "Jargoyle",
    "homophone": "Wherewolf",
}


PEDANT_STONES: Dict[str, str] = {
    "andi": "Hypercorrectite",
    "infinitoad": "Unsplittium",
    "aetheria": "Coeurite",
    "apostrofae": "Curlite",
    "commama": "Oxfordium",
}


def module_for_operation(op_type: str) -> ModuleType:
    """Return the module that backs a named pipeline operation."""
    try:
        glitchling_name = OPERATION_MODULES[op_type]
    except KeyError as error:  # pragma: no cover - defensive fallback
        raise KeyError(f"Unknown operation type: {op_type}") from error
    return _glitchling_module(glitchling_name)


BASE_DESCRIPTORS: List[Descriptor] = [
    {
        "name": "Rushmore-Duplicate",
        "operation": {"type": "reduplicate", "rate": 0.01},
    },
    {"name": "Rushmore", "operation": {"type": "delete", "rate": 0.01}},
    {
        "name": "Redactyl",
        "operation": {
            "type": "redact",
            "replacement_char": redactyl_full_block(),
            "rate": 0.05,
            "merge_adjacent": True,
        },
    },
    {"name": "Scannequin", "operation": {"type": "ocr", "rate": 0.02}},
    {
        "name": "Zeedub",
        "operation": {
            "type": "zwj",
            "rate": 0.02,
            "characters": zero_width_characters(),
        },
    },
    {
        "name": "Typogre",
        "operation": {
            "type": "typo",
            "rate": 0.02,
            "keyboard": "CURATOR_QWERTY",
            "layout": keyboard_layout("CURATOR_QWERTY"),
        },
    },
]


SHORT_TEXT = (
    "One morning, when Gregor Samsa woke from troubled dreams, he found himself "
    "transformed in his bed into a horrible vermin."
)
MEDIUM_TEXT = " ".join([SHORT_TEXT] * 32)
LONG_TEXT = " ".join([SHORT_TEXT] * 256)
VERY_LONG_TEXT = " ".join([SHORT_TEXT] * 2048)

DEFAULT_TEXTS: Tuple[Tuple[str, str], ...] = (
    ("short", SHORT_TEXT),
    ("medium", MEDIUM_TEXT),
    ("long", LONG_TEXT),
    ("very_long", VERY_LONG_TEXT),
)

# Full-text benchmarks keyed by Project Gutenberg book IDs.
PROJECT_GUTENBERG_BOOK_IDS: Tuple[Tuple[str, int], ...] = (
    ("the_canterbury_tales", 22120),
    ("middlemarch", 145),
    ("thus_spoke_zarathustra", 1998),
    ("symbolic_logic", 28696),
    ("war_and_peace", 2600),
    ("leaves_of_grass", 1322),
    ("the_importance_of_being_earnest", 844),
    ("on_the_origin_of_species", 1228),
    ("the_iliad", 6130),
    ("ulysses", 4300),
    ("beowulf_modern_english_prose", 50742),
)


def _read_gutenberg_books(api: Any) -> Tuple[Tuple[str, str], ...]:
    """Return full texts for configured Project Gutenberg book IDs."""
    corpus: list[tuple[str, str]] = []
    for label, book_id in PROJECT_GUTENBERG_BOOK_IDS:
        book = api.get_book(book_id)
        text = _resolve_book_text(book)
        corpus.append((label, text))
    return tuple(corpus)


@lru_cache(maxsize=None)
def _load_gutenberg_books(instance_url: str) -> Tuple[Tuple[str, str], ...]:
    """Fetch and cache full Project Gutenberg texts for benchmarking."""
    api = _get_gutenberg_api(instance_url)
    return _read_gutenberg_books(api)


def load_gutenberg_books(
    *,
    instance_url: str | None = None,
    api: Any | None = None,
) -> Tuple[Tuple[str, str], ...]:
    """Return the Project Gutenberg benchmark corpus using full book texts."""
    resolved_url = instance_url or os.getenv("GUTENDEX_URL", DEFAULT_GUTENDEX_URL)
    if api is not None:
        return _read_gutenberg_books(api)
    return _load_gutenberg_books(resolved_url)


def resolve_corpus(corpus: CorpusLike) -> Tuple[Tuple[str, str], ...]:
    """Materialize a corpus from either static text or a loader callable."""
    selected = corpus() if callable(corpus) else corpus
    return tuple(selected)


# Keep the legacy "gutenberg_titles" key as a CLI alias.
BENCHMARK_CORPORA: Dict[str, CorpusLike] = {
    "default": DEFAULT_TEXTS,
    "gutenberg": load_gutenberg_books,
    "gutenberg_titles": load_gutenberg_books,
}
DEFAULT_ITERATIONS = 25
MASTER_SEED = 151


SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "baseline": "Default six-glitch pipeline mirroring the public benchmark configuration.",
    "shuffle_mix": "Adds Rushmore's swap mode alongside deletion to stress mixed workloads.",
    "aggressive_cleanup": "Heavy redaction and deletion pass to emulate worst-case sanitisation.",
    "stealth_noise": "Lightweight typo and zero-width noise focused on subtle obfuscations.",
    # Individual glitchling scenarios
    "typogre_only": "Typogre-only benchmark for keyboard neighbor typo injection.",
    "rushmore_delete": "Rushmore delete-only benchmark for word deletion.",
    "rushmore_duplicate": "Rushmore duplicate-only benchmark for word reduplication.",
    "rushmore_swap": "Rushmore swap-only benchmark for adjacent word swapping.",
    "redactyl_only": "Redactyl-only benchmark for character redaction.",
    "scannequin_only": "Scannequin-only benchmark for OCR confusion injection.",
    "zeedub_only": "Zeedub-only benchmark for zero-width character injection.",
    "mim1c_only": "Mim1c-only benchmark for homoglyph substitution.",
    "wherewolf_only": "Wherewolf-only benchmark for homophone substitution.",
    "hokey_only": "Hokey-only benchmark for expressive lengthening.",
    "jargoyle_only": "Jargoyle-only benchmark for dictionary-based synonym substitution.",
    # Pedant evolution scenarios
    "pedant_andi": "Pedant Andi benchmark for coordinate pronoun hypercorrection.",
    "pedant_infinitoad": "Pedant Infinitoad benchmark for split infinitive correction.",
    "pedant_aetheria": "Pedant Aetheria benchmark for ligature and diaeresis restoration.",
    "pedant_apostrofae": "Pedant Apostrofae benchmark for curly quote normalization.",
    "pedant_commama": "Pedant Commama benchmark for Oxford comma insertion.",
}


__all__ = [
    "Descriptor",
    "OPERATION_MODULES",
    "PEDANT_STONES",
    "module_for_operation",
    "BASE_DESCRIPTORS",
    "DEFAULT_ITERATIONS",
    "DEFAULT_TEXTS",
    "PROJECT_GUTENBERG_BOOK_IDS",
    "BENCHMARK_CORPORA",
    "MASTER_SEED",
    "SCENARIO_DESCRIPTIONS",
    "SHORT_TEXT",
    "MEDIUM_TEXT",
    "LONG_TEXT",
    "VERY_LONG_TEXT",
    "load_gutenberg_books",
    "resolve_corpus",
    "redactyl_full_block",
    "zero_width_characters",
    "keyboard_layout",
]

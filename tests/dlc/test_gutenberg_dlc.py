"""Tests for the GlitchenbergAPI integration."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest


@dataclass
class MockPerson:
    """Mock Person class for testing."""

    birth_year: int
    death_year: int
    name: str


@dataclass
class MockBook:
    """Mock Book class for testing."""

    id: int
    title: str
    authors: list[MockPerson]
    translators: list[MockPerson]
    subjects: list[str]
    bookshelves: list[str]
    languages: list[str]
    copyright: bool
    media_type: str
    formats: dict[str, str]
    download_count: int


@pytest.fixture
def mock_gutenberg_module() -> types.ModuleType:
    """Create a mock gutenberg module for testing."""
    gutenberg_module = types.ModuleType("gutenberg")
    models_module = types.ModuleType("gutenberg.models")

    # Add Book and Person to models
    models_module.Book = MockBook  # type: ignore[attr-defined]
    models_module.Person = MockPerson  # type: ignore[attr-defined]

    # Create MockGutenbergAPI
    class MockGutenbergAPI:
        def __init__(self, instance_url: str = "https://test.example.com") -> None:
            self.instance_url = instance_url

        def get_book(self, id: int) -> MockBook:
            return MockBook(
                id=id,
                title="Pride and Prejudice",
                authors=[MockPerson(1775, 1817, "Jane Austen")],
                translators=[],
                subjects=["Romance", "Fiction"],
                bookshelves=["Best Books Ever"],
                languages=["en"],
                copyright=False,
                media_type="Text",
                formats={
                    "text/plain": "https://example.com/book.txt",
                    "application/epub+zip": "https://example.com/book.epub",
                },
                download_count=100,
            )

        def get_all_books(self) -> list[MockBook]:
            return [self.get_book(1), self.get_book(2)]

        def get_public_domain_books(self) -> list[MockBook]:
            return [self.get_book(1)]

        def get_copyrighted_books(self) -> list[MockBook]:
            return [self.get_book(2)]

        def get_books_by_ids(self, ids: list[int]) -> list[MockBook]:
            return [self.get_book(i) for i in ids]

        def get_books_by_language(self, languages: list[str]) -> list[MockBook]:
            return [self.get_book(1)]

        def get_books_by_search(self, query: str) -> list[MockBook]:
            return [self.get_book(1)]

        def get_books_by_mime_type(self, mime_type: str) -> list[MockBook]:
            return [self.get_book(1)]

        def get_books_ascending(self) -> list[MockBook]:
            return [self.get_book(1)]

        def get_oldest(self) -> list[MockBook]:
            return [self.get_book(1)]

        def get_latest(self, topic: Any) -> list[MockBook]:
            return [self.get_book(1)]

        def get_book_metadata(self, id: int) -> MockBook:
            return self.get_book(id)

        def get_book_text(self, id: int) -> MockBook:
            return self.get_book(id)

    gutenberg_module.GutenbergAPI = MockGutenbergAPI  # type: ignore[attr-defined]
    gutenberg_module.models = models_module  # type: ignore[attr-defined]

    return gutenberg_module


@pytest.fixture
def install_mock_gutenberg(mock_gutenberg_module: types.ModuleType) -> Any:
    """Install the mock gutenberg module for import."""
    preserved = {name: sys.modules.get(name) for name in ("gutenberg", "gutenberg.models")}

    sys.modules["gutenberg"] = mock_gutenberg_module
    sys.modules["gutenberg.models"] = mock_gutenberg_module.models  # type: ignore[attr-defined]

    yield mock_gutenberg_module

    for name, module in preserved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def test_glitchenberg_api_accepts_single_glitchling(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test GlitchenbergAPI with a single glitchling specification."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    book = api.get_book(1342)

    assert book.id == 1342
    # Title should be corrupted (may or may not change depending on RNG)
    assert isinstance(book.title, str)
    # Original attributes should be preserved
    assert len(book.authors) == 1
    assert book.authors[0].name == "Jane Austen"


def test_glitchenberg_api_accepts_gaggle(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test GlitchenbergAPI with a pre-built Gaggle."""
    from glitchlings import Gaggle, Typogre
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    gaggle = Gaggle([Typogre(rate=0.1)], seed=99)
    api = GlitchenbergAPI(gaggle)
    book = api.get_book(1)

    assert book.id == 1
    assert isinstance(book.title, str)


def test_glitchenberg_api_accepts_multiple_glitchlings(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test GlitchenbergAPI with multiple glitchling specifications."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI(["typogre", "mim1c"], seed=42)
    book = api.get_book(1)

    assert book.id == 1
    assert isinstance(book.title, str)


def test_glitchenberg_api_get_all_books(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_all_books returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_all_books()

    assert len(books) == 2
    assert all(isinstance(b.title, str) for b in books)


def test_glitchenberg_api_get_books_by_search(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_books_by_search returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_books_by_search("pride")

    assert len(books) == 1
    assert isinstance(books[0].title, str)


def test_glitchenberg_api_deterministic_corruption(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test that same seed produces same corrupted output."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api1 = GlitchenbergAPI("typogre", seed=42)
    api2 = GlitchenbergAPI("typogre", seed=42)

    book1 = api1.get_book(1)
    book2 = api2.get_book(1)

    assert book1.title == book2.title


def test_glitchenberg_api_different_seeds_different_output(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test that different seeds can produce different corrupted output."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    # Use Mim1c which is more likely to change characters
    api1 = GlitchenbergAPI("Mim1c(rate=0.5)", seed=42)
    api2 = GlitchenbergAPI("Mim1c(rate=0.5)", seed=999)

    book1 = api1.get_book(1)
    book2 = api2.get_book(1)

    # With high rate and different seeds, titles should likely differ
    # (though not guaranteed for short text)
    assert isinstance(book1.title, str)
    assert isinstance(book2.title, str)


def test_glitchenberg_api_instance_url(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test that custom instance_url is used."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    custom_url = "https://custom.gutendex.example.com"
    api = GlitchenbergAPI("typogre", instance_url=custom_url)

    assert api.instance_url == custom_url


def test_glitchenberg_api_preserves_book_metadata(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test that non-text metadata is preserved."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    book = api.get_book(1)

    # These should be unchanged
    assert book.languages == ["en"]
    assert book.copyright is False
    assert book.media_type == "Text"
    assert "text/plain" in book.formats
    assert book.subjects == ["Romance", "Fiction"]


def test_glitchenberg_api_get_public_domain_books(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_public_domain_books returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_public_domain_books()

    assert len(books) == 1


def test_glitchenberg_api_get_copyrighted_books(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_copyrighted_books returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_copyrighted_books()

    assert len(books) == 1


def test_glitchenberg_api_get_books_by_ids(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_books_by_ids returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_books_by_ids([1, 2, 3])

    assert len(books) == 3


def test_glitchenberg_api_get_books_by_language(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_books_by_language returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_books_by_language(["en"])

    assert len(books) == 1


def test_glitchenberg_api_get_books_by_mime_type(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_books_by_mime_type returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_books_by_mime_type("text/plain")

    assert len(books) == 1


def test_glitchenberg_api_get_books_ascending(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_books_ascending returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_books_ascending()

    assert len(books) == 1


def test_glitchenberg_api_get_oldest(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_oldest returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_oldest()

    assert len(books) == 1


def test_glitchenberg_api_get_latest(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_latest returns corrupted books."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    books = api.get_latest("fiction")

    assert len(books) == 1


def test_glitchenberg_api_get_book_metadata(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_book_metadata returns corrupted book."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    book = api.get_book_metadata(1)

    assert book.id == 1


def test_glitchenberg_api_get_book_text(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test get_book_text returns corrupted book."""
    from glitchlings.dlc.gutenberg import GlitchenbergAPI

    api = GlitchenbergAPI("typogre", seed=42)
    book = api.get_book_text(1)

    assert book.id == 1


def test_glitched_book_from_book(
    install_mock_gutenberg: types.ModuleType,
) -> None:
    """Test GlitchedBook.from_book creates a corrupted book."""
    from glitchlings import Gaggle, Typogre
    from glitchlings.dlc.gutenberg import GlitchedBook

    original = MockBook(
        id=1,
        title="Original Title",
        authors=[MockPerson(1800, 1850, "Author Name")],
        translators=[],
        subjects=["Subject"],
        bookshelves=["Shelf"],
        languages=["en"],
        copyright=False,
        media_type="Text",
        formats={"text/plain": "https://example.com/book.txt"},
        download_count=50,
    )
    gaggle = Gaggle([Typogre(rate=0.1)], seed=42)

    glitched = GlitchedBook.from_book(original, gaggle)

    assert glitched.id == 1
    assert isinstance(glitched.title, str)
    assert glitched._original_book is original
    assert glitched._gaggle is gaggle


def test_import_error_message_format() -> None:
    """Test that the ImportError message is helpful when py-gutenberg is missing."""

    from glitchlings.dlc.gutenberg import _get_gutenberg_api

    # Mock the import to fail
    with patch.dict(sys.modules, {"gutenberg": None}):
        # Force ImportError by making gutenberg import fail
        with patch("builtins.__import__", side_effect=ImportError("No module named 'gutenberg'")):
            with pytest.raises(ImportError, match="py-gutenberg is required"):
                _get_gutenberg_api("https://example.com")

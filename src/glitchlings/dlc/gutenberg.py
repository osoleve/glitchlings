"""Integration helpers for the py-gutenberg library.

This module provides a wrapper around the GutenbergAPI that applies
glitchlings to book text as it's fetched.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from ..util.adapters import coerce_gaggle
from ..zoo import Gaggle, Glitchling

if TYPE_CHECKING:  # pragma: no cover
    from gutenberg import GutenbergAPI
    from gutenberg.models import Book, Person


@dataclass
class GlitchedBook:
    """A Book wrapper that corrupts text content via glitchlings.

    This class wraps a py-gutenberg Book object but provides corrupted text
    when accessed. The original Book attributes are preserved.
    """

    id: int
    title: str
    authors: list[Person]
    translators: list[Person]
    subjects: list[str]
    bookshelves: list[str]
    languages: list[str]
    copyright: bool
    media_type: str
    formats: dict[str, str]
    download_count: int
    _original_book: Book
    _gaggle: Gaggle

    @classmethod
    def from_book(cls, book: Book, gaggle: Gaggle) -> GlitchedBook:
        """Create a GlitchedBook from a py-gutenberg Book.

        Args:
            book: The original Book object from py-gutenberg.
            gaggle: The gaggle of glitchlings to apply to text.

        Returns:
            A GlitchedBook that corrupts text with the provided gaggle.
        """
        return cls(
            id=book.id,
            title=cast(str, gaggle.corrupt(book.title)),
            authors=book.authors,
            translators=book.translators,
            subjects=book.subjects,
            bookshelves=book.bookshelves,
            languages=book.languages,
            copyright=book.copyright,
            media_type=book.media_type,
            formats=book.formats,
            download_count=book.download_count,
            _original_book=book,
            _gaggle=gaggle,
        )


class GlitchenbergAPI:
    """A wrapper around GutenbergAPI that corrupts book text with glitchlings.

    This class provides the same interface as GutenbergAPI but applies
    glitchlings to corrupt book text as it's fetched.

    Example:
        >>> from glitchlings.dlc.gutenberg import GlitchenbergAPI
        >>> from glitchlings import Typogre
        >>> api = GlitchenbergAPI(Typogre(rate=0.05), seed=42)
        >>> book = api.get_book(1342)  # Pride and Prejudice
        >>> print(book.title)  # Title will have typos applied
    """

    def __init__(
        self,
        glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
        *,
        seed: int = 151,
        instance_url: str = "https://gutendex.devbranch.co",
    ) -> None:
        """Initialize the GlitchenbergAPI.

        Args:
            glitchlings: A glitchling, gaggle, or specification of glitchlings to apply.
            seed: RNG seed for deterministic corruption (default: 151).
            instance_url: The Gutendex instance URL to use for API requests.
                Defaults to "https://gutendex.devbranch.co".
        """
        self._gaggle = coerce_gaggle(glitchlings, seed=seed)
        self._api = _get_gutenberg_api(instance_url)

    @property
    def instance_url(self) -> str:
        """Return the Gutendex instance URL."""
        return str(self._api.instance_url)

    def _corrupt_book(self, book: Book) -> GlitchedBook:
        """Apply glitchlings to a Book object."""
        return GlitchedBook.from_book(book, self._gaggle)

    def _corrupt_books(self, books: list[Book]) -> list[GlitchedBook]:
        """Apply glitchlings to a list of Book objects."""
        return [self._corrupt_book(book) for book in books]

    # Methods that return lists of books
    def get_all_books(self) -> list[GlitchedBook]:
        """Get all books with glitchling corruption applied."""
        return self._corrupt_books(self._api.get_all_books())

    def get_public_domain_books(self) -> list[GlitchedBook]:
        """Get public domain books with glitchling corruption applied."""
        return self._corrupt_books(self._api.get_public_domain_books())

    def get_copyrighted_books(self) -> list[GlitchedBook]:
        """Get copyrighted books with glitchling corruption applied."""
        return self._corrupt_books(self._api.get_copyrighted_books())

    def get_books_by_ids(self, ids: list[int]) -> list[GlitchedBook]:
        """Get books by IDs with glitchling corruption applied.

        Args:
            ids: List of Gutenberg book IDs to retrieve.

        Returns:
            List of GlitchedBook objects with corrupted text.
        """
        return self._corrupt_books(self._api.get_books_by_ids(ids))

    def get_books_by_language(self, languages: list[str]) -> list[GlitchedBook]:
        """Get books by language with glitchling corruption applied.

        Args:
            languages: List of language codes (e.g., ["en", "fr"]).

        Returns:
            List of GlitchedBook objects with corrupted text.
        """
        return self._corrupt_books(self._api.get_books_by_language(languages))

    def get_books_by_search(self, query: str) -> list[GlitchedBook]:
        """Search for books with glitchling corruption applied.

        Args:
            query: Search query string.

        Returns:
            List of GlitchedBook objects with corrupted text.
        """
        return self._corrupt_books(self._api.get_books_by_search(query))

    def get_books_by_mime_type(self, mime_type: str) -> list[GlitchedBook]:
        """Get books by MIME type with glitchling corruption applied.

        Args:
            mime_type: MIME type filter (e.g., "text/plain").

        Returns:
            List of GlitchedBook objects with corrupted text.
        """
        return self._corrupt_books(self._api.get_books_by_mime_type(mime_type))

    def get_books_ascending(self) -> list[GlitchedBook]:
        """Get books sorted ascending with glitchling corruption applied."""
        return self._corrupt_books(self._api.get_books_ascending())

    def get_oldest(self) -> list[GlitchedBook]:
        """Get oldest books with glitchling corruption applied."""
        return self._corrupt_books(self._api.get_oldest())

    def get_latest(self, topic: Any) -> list[GlitchedBook]:
        """Get latest books by topic with glitchling corruption applied.

        Args:
            topic: Topic to filter books by.

        Returns:
            List of GlitchedBook objects with corrupted text.
        """
        return self._corrupt_books(self._api.get_latest(topic))

    # Methods that return single books
    def get_book(self, id: int) -> GlitchedBook:
        """Get a book by ID with glitchling corruption applied.

        Args:
            id: Gutenberg book ID.

        Returns:
            GlitchedBook with corrupted text.
        """
        return self._corrupt_book(self._api.get_book(id))

    def get_book_metadata(self, id: int) -> GlitchedBook:
        """Get book metadata by ID with glitchling corruption applied.

        Args:
            id: Gutenberg book ID.

        Returns:
            GlitchedBook with corrupted metadata.
        """
        return self._corrupt_book(self._api.get_book_metadata(id))

    def get_book_text(self, id: int) -> GlitchedBook:
        """Get book text by ID with glitchling corruption applied.

        Args:
            id: Gutenberg book ID.

        Returns:
            GlitchedBook with corrupted text.
        """
        return self._corrupt_book(self._api.get_book_text(id))


def _get_gutenberg_api(instance_url: str) -> GutenbergAPI:
    """Import and return a GutenbergAPI instance.

    Raises:
        ImportError: If py-gutenberg is not installed.
    """
    try:
        from gutenberg import GutenbergAPI
    except ImportError as exc:
        raise ImportError(
            "py-gutenberg is required for the GlitchenbergAPI integration. "
            "Install it with: pip install py-gutenberg"
        ) from exc

    return GutenbergAPI(instance_url=instance_url)


__all__ = ["GlitchenbergAPI", "GlitchedBook"]

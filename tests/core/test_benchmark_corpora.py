"""Tests for benchmark corpus definitions."""

from benchmarks import constants

EXPECTED_GUTENBERG_LABELS = [
    "the_canterbury_tales",
    "middlemarch",
    "thus_spoke_zarathustra",
    "symbolic_logic",
    "war_and_peace",
    "leaves_of_grass",
    "the_importance_of_being_earnest",
    "on_the_origin_of_species",
    "the_iliad",
    "ulysses",
    "beowulf_modern_english_prose",
]
EXPECTED_GUTENBERG_IDS = [book_id for _, book_id in constants.PROJECT_GUTENBERG_BOOK_IDS]


def test_default_corpus_alias() -> None:
    """The default corpus should remain aliased for backwards compatibility."""

    assert constants.DEFAULT_TEXTS is constants.BENCHMARK_CORPORA["default"]


def test_gutenberg_corpus_aliases() -> None:
    """The Project Gutenberg corpus entries should route to the loader."""

    assert constants.BENCHMARK_CORPORA["gutenberg"] is constants.load_gutenberg_books


def test_gutenberg_corpus_loads_book_text() -> None:
    """The Project Gutenberg corpus should fetch book text, not snippets."""

    class FakeBook:
        def __init__(self, book_id: int) -> None:
            self.book_id = book_id

        def get_text(self) -> str:
            return f"full text for {self.book_id}"

    class FakeAPI:
        def __init__(self) -> None:
            self.requested: list[int] = []

        def get_book(self, book_id: int) -> FakeBook:
            self.requested.append(book_id)
            return FakeBook(book_id)

    api = FakeAPI()
    corpus = constants.load_gutenberg_books(api=api)

    assert api.requested == EXPECTED_GUTENBERG_IDS
    assert [label for label, _ in corpus] == EXPECTED_GUTENBERG_LABELS
    assert all(text.startswith("full text for") for _, text in corpus)


def test_resolve_corpus_invokes_loader() -> None:
    """Callable corpora should be materialised by resolve_corpus."""

    marker: list[str] = []

    def loader() -> tuple[tuple[str, str], ...]:
        marker.append("called")
        return (("label", "payload"),)

    resolved = constants.resolve_corpus(loader)

    assert marker == ["called"]
    assert resolved == (("label", "payload"),)

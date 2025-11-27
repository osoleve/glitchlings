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


def test_default_corpus_alias() -> None:
    """The default corpus should remain aliased for backwards compatibility."""

    assert constants.DEFAULT_TEXTS is constants.BENCHMARK_CORPORA["default"]


def test_gutenberg_titles_corpus_contents() -> None:
    """The Project Gutenberg corpus should expose the configured title snippets."""

    corpus = constants.BENCHMARK_CORPORA["gutenberg_titles"]
    assert len(corpus) == len(EXPECTED_GUTENBERG_LABELS)
    labels = [label for label, _ in corpus]
    assert labels == EXPECTED_GUTENBERG_LABELS
    assert all(text.strip() for _, text in corpus)

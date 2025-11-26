"""Lexicon test configuration.

This module provides lexicon-specific fixtures for testing lexicon backends
and related functionality.
"""

from __future__ import annotations

# Import shared fixtures from centralized locations
# MockLexicon, TrackingLexicon, toy_embeddings, shared_vector_embeddings
# are now in tests.fixtures.lexicon
from tests.fixtures.lexicon import (
    MockLexicon,
    TrackingLexicon,
    shared_vector_embeddings,
    toy_embeddings,
)

# Import mock helpers from tests.fixtures.mocks
from tests.fixtures.mocks import (
    mock_gensim_vectors,
    mock_sentence_transformers,
    mock_spacy_language,
)

# Re-export for backward compatibility with existing tests
__all__ = [
    "MockLexicon",
    "TrackingLexicon",
    "toy_embeddings",
    "shared_vector_embeddings",
    "mock_spacy_language",
    "mock_gensim_vectors",
    "mock_sentence_transformers",
]

"""Shared test fixtures for the glitchlings test suite."""

from __future__ import annotations

from tests.fixtures.glitchlings import fresh_glitchling, sample_text
from tests.fixtures.mocks import (
    _load_environment,
    _Rubric,
    _SingleTurnEnv,
    _VerifierEnvironment,
    mock_gensim_vectors,
    mock_module,
    mock_sentence_transformers,
    mock_spacy_language,
    torch_stub,
)

__all__ = [
    # Glitchling fixtures
    "fresh_glitchling",
    "sample_text",
    # Mock fixtures
    "mock_module",
    "torch_stub",
    "mock_spacy_language",
    "mock_gensim_vectors",
    "mock_sentence_transformers",
    # Verifiers stub classes (for DLC tests)
    "_Rubric",
    "_SingleTurnEnv",
    "_VerifierEnvironment",
    "_load_environment",
]

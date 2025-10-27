"""WordNet-backed lexicon implementation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Protocol, Sequence, cast

from ..compat import nltk as _nltk_dependency
from . import LexiconBackend
from ._cache import CacheSnapshot


class _LemmaProtocol(Protocol):
    def name(self) -> str: ...


class _SynsetProtocol(Protocol):
    def lemmas(self) -> Sequence[_LemmaProtocol]: ...


class _WordNetResource(Protocol):
    def synsets(self, word: str, pos: str | None = None) -> Sequence[_SynsetProtocol]: ...

    def ensure_loaded(self) -> None: ...


WordNetCorpusReaderFactory = Callable[[Any, Any], _WordNetResource]

nltk: ModuleType | None = _nltk_dependency.get()
_NLTK_IMPORT_ERROR: ModuleNotFoundError | None = _nltk_dependency.error

WordNetCorpusReader: WordNetCorpusReaderFactory | None = None
find: Callable[[str], Any] | None = None
_WORDNET_MODULE: _WordNetResource | None = None

if nltk is not None:  # pragma: no cover - guarded by import success
    try:
        corpus_reader_module = import_module("nltk.corpus.reader")
    except ModuleNotFoundError as exc:  # pragma: no cover - triggered when corpus missing
        if _NLTK_IMPORT_ERROR is None:
            _NLTK_IMPORT_ERROR = exc
    else:
        reader_candidate = getattr(corpus_reader_module, "WordNetCorpusReader", None)
        if reader_candidate is not None:
            WordNetCorpusReader = cast(WordNetCorpusReaderFactory, reader_candidate)

        try:
            data_module = import_module("nltk.data")
        except ModuleNotFoundError as exc:  # pragma: no cover - triggered when data missing
            if _NLTK_IMPORT_ERROR is None:
                _NLTK_IMPORT_ERROR = exc
        else:
            locator = getattr(data_module, "find", None)
            if callable(locator):
                find = cast(Callable[[str], Any], locator)

    try:
        module_candidate = import_module("nltk.corpus.wordnet")
    except ModuleNotFoundError:  # pragma: no cover - only hit on namespace packages
        _WORDNET_MODULE = None
    else:
        _WORDNET_MODULE = cast(_WordNetResource, module_candidate)
else:
    nltk = None
    find = None
    _WORDNET_MODULE = None

_WORDNET_HANDLE: _WordNetResource | None = _WORDNET_MODULE
_wordnet_ready = False

_VALID_POS: tuple[str, ...] = ("n", "v", "a", "r")


def _require_nltk() -> None:
    """Ensure the NLTK dependency is present before continuing."""
    if nltk is None or find is None:
        message = (
            "The NLTK package is required for WordNet-backed lexicons; install "
            "`nltk` and its WordNet corpus manually to enable this backend."
        )
        if "_NLTK_IMPORT_ERROR" in globals() and _NLTK_IMPORT_ERROR is not None:
            raise RuntimeError(message) from _NLTK_IMPORT_ERROR
        raise RuntimeError(message)


def dependencies_available() -> bool:
    """Return ``True`` when the runtime NLTK dependency is present."""
    return nltk is not None and find is not None


def _load_wordnet_reader() -> _WordNetResource:
    """Return a WordNet corpus reader from the downloaded corpus files."""
    _require_nltk()

    if WordNetCorpusReader is None:
        raise RuntimeError("The NLTK WordNet corpus reader is unavailable.")

    locator = find
    if locator is None:
        raise RuntimeError("The NLTK data locator is unavailable.")

    try:
        root = locator("corpora/wordnet")
    except LookupError:
        try:
            zip_root = locator("corpora/wordnet.zip")
        except LookupError as exc:
            raise RuntimeError(
                "The NLTK WordNet corpus is not installed; run `nltk.download('wordnet')`."
            ) from exc
        root = zip_root.join("wordnet/")

    return WordNetCorpusReader(root, None)


def _wordnet(force_refresh: bool = False) -> _WordNetResource:
    """Retrieve the active WordNet handle, rebuilding it on demand."""
    global _WORDNET_HANDLE

    if force_refresh:
        _WORDNET_HANDLE = _WORDNET_MODULE

    cached = _WORDNET_HANDLE
    if cached is not None:
        return cached

    resource = _load_wordnet_reader()
    _WORDNET_HANDLE = resource
    return resource


def ensure_wordnet() -> None:
    """Ensure the WordNet corpus is available before use."""
    global _wordnet_ready
    if _wordnet_ready:
        return

    _require_nltk()

    resource = _wordnet()
    nltk_module = nltk
    if nltk_module is None:
        raise RuntimeError("The NLTK dependency is unexpectedly unavailable.")

    try:
        resource.ensure_loaded()
    except LookupError:
        nltk_module.download("wordnet", quiet=True)
        try:
            resource = _wordnet(force_refresh=True)
            resource.ensure_loaded()
        except LookupError as exc:  # pragma: no cover - only triggered when download fails
            raise RuntimeError("Unable to load NLTK WordNet corpus for synonym lookups.") from exc

    _wordnet_ready = True


def _collect_synonyms(word: str, parts_of_speech: tuple[str, ...]) -> list[str]:
    """Gather deterministic synonym candidates for the supplied word."""
    normalized_word = word.lower()
    wordnet = _wordnet()
    synonyms: set[str] = set()
    for pos_tag in parts_of_speech:
        synsets = wordnet.synsets(word, pos=pos_tag)
        if not synsets:
            continue

        for synset in synsets:
            lemmas_list = [lemma.name() for lemma in synset.lemmas()]
            if not lemmas_list:
                continue

            filtered = []
            for lemma_str in lemmas_list:
                cleaned = lemma_str.replace("_", " ")
                if cleaned.lower() != normalized_word:
                    filtered.append(cleaned)

            if filtered:
                synonyms.update(filtered)
                break

        if synonyms:
            break

    return sorted(synonyms)


class WordNetLexicon(LexiconBackend):
    """Lexicon that retrieves synonyms from the NLTK WordNet corpus."""

    def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
        """Return up to ``n`` WordNet lemmas for ``word`` filtered by ``pos`` if provided."""
        ensure_wordnet()

        if pos is None:
            parts: tuple[str, ...] = _VALID_POS
        else:
            normalized_pos = pos.lower()
            if normalized_pos not in _VALID_POS:
                return []
            parts = (normalized_pos,)

        synonyms = _collect_synonyms(word, parts)
        return self._deterministic_sample(synonyms, limit=n, word=word, pos=pos)

    def supports_pos(self, pos: str | None) -> bool:
        """Return ``True`` when ``pos`` is unset or recognised by the WordNet corpus."""
        if pos is None:
            return True
        return pos.lower() in _VALID_POS

    @classmethod
    def load_cache(cls, path: str | Path) -> CacheSnapshot:
        """WordNet lexicons do not persist caches; raising keeps the contract explicit."""
        raise RuntimeError("WordNetLexicon does not persist or load caches.")

    def save_cache(self, path: str | Path | None = None) -> Path | None:
        """WordNet lexicons do not persist caches; raising keeps the contract explicit."""
        raise RuntimeError("WordNetLexicon does not persist or load caches.")

    def __repr__(self) -> str:  # pragma: no cover - trivial representation
        return f"WordNetLexicon(seed={self.seed!r})"


__all__ = ["WordNetLexicon", "dependencies_available", "ensure_wordnet"]

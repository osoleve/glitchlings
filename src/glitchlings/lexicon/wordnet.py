"""WordNet-backed lexicon implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - exercised when NLTK is available
    import nltk  # type: ignore[import]
except ModuleNotFoundError as exc:  # pragma: no cover - triggered when NLTK missing
    nltk = None  # type: ignore[assignment]
    find = None  # type: ignore[assignment]
    _NLTK_IMPORT_ERROR = exc
else:  # pragma: no cover - executed when NLTK is present
    from nltk.corpus.reader import WordNetCorpusReader as _WordNetCorpusReader  # type: ignore[import]
    from nltk.data import find as _nltk_find  # type: ignore[import]

    find = _nltk_find
    _NLTK_IMPORT_ERROR = None

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from nltk.corpus.reader import WordNetCorpusReader  # type: ignore[import]
else:  # pragma: no cover - runtime fallback to avoid hard dependency
    WordNetCorpusReader = Any

if nltk is not None:  # pragma: no cover - guarded by import success
    try:
        from nltk.corpus import wordnet as _WORDNET_MODULE  # type: ignore[import]
    except ModuleNotFoundError:  # pragma: no cover - only hit on namespace packages
        _WORDNET_MODULE = None
    else:
        WordNetCorpusReader = _WordNetCorpusReader  # type: ignore[assignment]
else:
    _WORDNET_MODULE = None

from . import Lexicon

_WORDNET_HANDLE: WordNetCorpusReader | Any | None = _WORDNET_MODULE
_wordnet_ready = False

_VALID_POS: tuple[str, ...] = ("n", "v", "a", "r")


def _require_nltk() -> None:
    """Ensure the NLTK dependency is present before continuing."""

    if nltk is None or find is None:
        message = (
            "The NLTK package is required for WordNet-backed lexicons; install "
            "`nltk` and its WordNet corpus manually to enable this backend."
        )
        if '_NLTK_IMPORT_ERROR' in globals() and _NLTK_IMPORT_ERROR is not None:
            raise RuntimeError(message) from _NLTK_IMPORT_ERROR
        raise RuntimeError(message)


def dependencies_available() -> bool:
    """Return ``True`` when the runtime NLTK dependency is present."""

    return nltk is not None and find is not None


def _load_wordnet_reader() -> WordNetCorpusReader:
    """Return a WordNet corpus reader from the downloaded corpus files."""

    _require_nltk()

    try:
        root = find("corpora/wordnet")
    except LookupError:
        try:
            zip_root = find("corpora/wordnet.zip")
        except LookupError as exc:
            raise RuntimeError(
                "The NLTK WordNet corpus is not installed; run `nltk.download('wordnet')`."
            ) from exc
        root = zip_root.join("wordnet/")

    return WordNetCorpusReader(root, None)


def _wordnet(force_refresh: bool = False) -> WordNetCorpusReader | Any:
    """Retrieve the active WordNet handle, rebuilding it on demand."""

    global _WORDNET_HANDLE

    if force_refresh:
        _WORDNET_HANDLE = _WORDNET_MODULE

    if _WORDNET_HANDLE is not None:
        return _WORDNET_HANDLE

    _WORDNET_HANDLE = _load_wordnet_reader()
    return _WORDNET_HANDLE


def ensure_wordnet() -> None:
    """Ensure the WordNet corpus is available before use."""

    global _wordnet_ready
    if _wordnet_ready:
        return

    _require_nltk()

    resource = _wordnet()

    try:
        resource.ensure_loaded()
    except LookupError:
        nltk.download("wordnet", quiet=True)
        try:
            resource = _wordnet(force_refresh=True)
            resource.ensure_loaded()
        except LookupError as exc:  # pragma: no cover - only triggered when download fails
            raise RuntimeError(
                "Unable to load NLTK WordNet corpus for synonym lookups."
            ) from exc

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


class WordNetLexicon(Lexicon):
    """Lexicon that retrieves synonyms from the NLTK WordNet corpus."""

    def get_synonyms(
        self, word: str, pos: str | None = None, n: int = 5
    ) -> list[str]:
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
        if pos is None:
            return True
        return pos.lower() in _VALID_POS

    def __repr__(self) -> str:  # pragma: no cover - trivial representation
        return f"WordNetLexicon(seed={self.seed!r})"


__all__ = ["WordNetLexicon", "dependencies_available", "ensure_wordnet"]

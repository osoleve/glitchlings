"""Graph-based lexicon backed by ConceptNet/Numberbatch embeddings."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence

from . import Lexicon
from .vector import VectorLexicon


_CONCEPT_RE = re.compile(r"^/c/(?P<lang>[a-z]{2})/(?P<term>[^/]+)")
_PUNCTUATION_RE = re.compile(r"[^\w\s-]+", re.UNICODE)


def _lemmatize_token(token: str) -> str:
    """Return a lightweight lemma for ``token`` using heuristic rules."""

    irregular = {
        "children": "child",
        "mice": "mouse",
        "geese": "goose",
        "feet": "foot",
        "teeth": "tooth",
        "men": "man",
        "women": "woman",
        "better": "good",
        "worse": "bad",
    }
    lowered = token.lower()
    if lowered in irregular:
        return irregular[lowered]

    if lowered.endswith("ies") and len(lowered) > 3:
        return lowered[:-3] + "y"
    if lowered.endswith("ves") and len(lowered) > 3:
        return lowered[:-3] + "f"
    if lowered.endswith("men") and len(lowered) > 3:
        return lowered[:-3] + "man"
    if lowered.endswith("ses") and len(lowered) > 3:
        return lowered[:-2]
    if lowered.endswith("es") and len(lowered) > 3:
        return lowered[:-2]
    if lowered.endswith("s") and len(lowered) > 2 and not lowered.endswith("ss"):
        return lowered[:-1]
    if lowered.endswith("ing") and len(lowered) > 4:
        stem = lowered[:-3]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if lowered.endswith("ed") and len(lowered) > 3:
        stem = lowered[:-2]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    return lowered


def _normalize_phrase(phrase: str) -> str:
    """Normalise ``phrase`` for ConceptNet lookups."""

    stripped = _PUNCTUATION_RE.sub(" ", phrase.lower())
    tokens = [token for token in stripped.split() if token]
    if not tokens:
        return ""
    lemmatised = [_lemmatize_token(token) for token in tokens]
    return " ".join(lemmatised)


def _concept_terms(normalized: str) -> list[str]:
    """Return ConceptNet term variants for ``normalized``."""

    collapsed = normalized.replace(" ", "_")
    if not collapsed:
        return []
    variants = {collapsed}
    variants.add(collapsed.replace("_", "-"))
    variants.add(collapsed.replace("-", "_"))
    return list(variants)


def _surface_from_concept(concept: str) -> str | None:
    """Return a human-readable surface form for ``concept``."""

    match = _CONCEPT_RE.match(concept)
    if match is None:
        return None
    term = match.group("term")
    surface = term.replace("_", " ")
    surface = surface.replace("-", " ")
    return " ".join(surface.split())


def _language_from_concept(concept: str) -> str | None:
    match = _CONCEPT_RE.match(concept)
    if match is None:
        return None
    return match.group("lang")


def _load_numberbatch(path: Path, *, languages: set[str]) -> Mapping[str, list[float]]:
    """Load ConceptNet Numberbatch embeddings from ``path``."""

    if not path.exists():
        return {}

    if path.suffix == ".gz":
        import gzip

        handle = gzip.open(path, "rt", encoding="utf8")
    else:
        handle = path.open("r", encoding="utf8")

    with handle as stream:
        header = stream.readline()
        try:
            parts = header.strip().split()
            if len(parts) >= 2:
                int(parts[0])
                int(parts[1])
        except ValueError:
            stream.seek(0)

        embeddings: dict[str, list[float]] = {}
        for line in stream:
            tokens = line.strip().split()
            if len(tokens) <= 2:
                continue
            concept = tokens[0]
            lang = _language_from_concept(concept)
            if lang is None or lang not in languages:
                continue
            try:
                vector = [float(value) for value in tokens[1:]]
            except ValueError:
                continue
            embeddings[concept] = vector
    return embeddings


def _load_cache(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise RuntimeError("Graph lexicon cache must be a mapping of strings to lists.")
    cache: dict[str, list[str]] = {}
    for key, values in payload.items():
        if not isinstance(key, str):
            raise RuntimeError("Graph lexicon cache keys must be strings.")
        if not isinstance(values, Sequence):
            raise RuntimeError("Graph lexicon cache values must be sequences of strings.")
        cache[key] = [str(value) for value in values]
    return cache


def _write_cache(path: Path, cache: Mapping[str, Sequence[str]]) -> None:
    serialisable = {key: list(values) for key, values in sorted(cache.items())}
    with path.open("w", encoding="utf8") as handle:
        json.dump(serialisable, handle, ensure_ascii=False, indent=2, sort_keys=True)


class GraphLexicon(Lexicon):
    """Lexicon backed by ConceptNet/Numberbatch embeddings."""

    def __init__(
        self,
        *,
        source: Mapping[str, Sequence[float]] | str | Path | None = None,
        cache: Mapping[str, Sequence[str]] | None = None,
        cache_path: str | Path | None = None,
        languages: Iterable[str] = ("en",),
        max_neighbors: int = 50,
        min_similarity: float = 0.0,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self._languages = {language.lower() for language in languages}
        if not self._languages:
            self._languages = {"en"}
        self._max_neighbors = max(1, max_neighbors)
        self._min_similarity = min_similarity
        self._cache: MutableMapping[str, list[str]] = {}
        self._cache_path = Path(cache_path) if cache_path is not None else None
        if self._cache_path is not None:
            self._cache.update(_load_cache(self._cache_path))
        if cache is not None:
            for key, values in cache.items():
                self._cache[str(key)] = [str(value) for value in values]
        self._cache_dirty = False

        prepared_source = self._prepare_source(source)
        self._backend = VectorLexicon(
            source=prepared_source if prepared_source else None,
            max_neighbors=self._max_neighbors,
            min_similarity=self._min_similarity,
            case_sensitive=True,
            seed=seed,
        )

    def _prepare_source(
        self, source: Mapping[str, Sequence[float]] | str | Path | None
    ) -> Mapping[str, Sequence[float]]:
        if source is None:
            return {}
        if isinstance(source, Mapping):
            prepared: dict[str, list[float]] = {}
            for key, vector in source.items():
                lang = _language_from_concept(key)
                if lang is None or lang not in self._languages:
                    continue
                prepared[key] = [float(value) for value in vector]
            return prepared
        path = Path(source)
        embeddings = _load_numberbatch(path, languages=self._languages)
        return embeddings

    def reseed(self, seed: int | None) -> None:
        super().reseed(seed)
        self._backend.reseed(seed)

    def _concept_candidates(self, normalized: str) -> list[str]:
        terms = _concept_terms(normalized)
        concepts = []
        for language in sorted(self._languages):
            for term in terms:
                concepts.append(f"/c/{language}/{term}")
        return concepts

    def _collect_synonyms(self, normalized: str) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()
        for concept in self._concept_candidates(normalized):
            neighbors = self._backend.precompute(concept, limit=self._max_neighbors)
            for neighbor in neighbors:
                lang = _language_from_concept(neighbor)
                if lang is None or lang not in self._languages:
                    continue
                surface = _surface_from_concept(neighbor)
                if surface is None:
                    continue
                surface_norm = _normalize_phrase(surface)
                if not surface_norm or surface_norm == normalized:
                    continue
                if surface_norm in seen:
                    continue
                seen.add(surface_norm)
                candidates.append(surface)
        return candidates

    def _ensure_cached(self, normalized: str) -> list[str]:
        if normalized in self._cache:
            return self._cache[normalized]
        synonyms = self._collect_synonyms(normalized)
        self._cache[normalized] = synonyms
        if self._cache_path is not None:
            self._cache_dirty = True
        return synonyms

    def get_synonyms(
        self, word: str, pos: str | None = None, n: int = 5
    ) -> list[str]:
        normalized = _normalize_phrase(word)
        if not normalized:
            return []
        synonyms = self._ensure_cached(normalized)
        return self._deterministic_sample(synonyms, limit=n, word=word, pos=pos)

    def precompute(self, word: str) -> list[str]:
        normalized = _normalize_phrase(word)
        if not normalized:
            return []
        return list(self._ensure_cached(normalized))

    def export_cache(self) -> dict[str, list[str]]:
        return {key: list(values) for key, values in self._cache.items()}

    def save_cache(self, path: str | Path | None = None) -> Path:
        if path is None:
            if self._cache_path is None:
                raise RuntimeError("No cache path supplied to GraphLexicon.")
            target = self._cache_path
        else:
            target = Path(path)
            self._cache_path = target
        _write_cache(target, self._cache)
        self._cache_dirty = False
        return target

    def supports_pos(self, pos: str | None) -> bool:
        return True

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        adapter = getattr(self._backend, "_adapter", None)
        state = "loaded" if adapter else "empty"
        return (
            f"GraphLexicon(languages={sorted(self._languages)!r}, "
            f"max_neighbors={self._max_neighbors}, seed={self.seed!r}, state={state})"
        )


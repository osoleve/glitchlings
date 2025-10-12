"""Vector-space lexicon implementation and cache building utilities."""

from __future__ import annotations

import argparse
import importlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable, Iterable, Iterator, Mapping, MutableMapping, Sequence

from . import LexiconBackend
from ._cache import CacheSnapshot, load_cache as _load_cache_file, write_cache as _write_cache_file


def _cosine_similarity(vector_a: Sequence[float], vector_b: Sequence[float]) -> float:
    """Return the cosine similarity between two dense vectors."""

    dot_product = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for value_a, value_b in zip(vector_a, vector_b):
        dot_product += value_a * value_b
        norm_a += value_a * value_a
        norm_b += value_b * value_b

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    magnitude = math.sqrt(norm_a) * math.sqrt(norm_b)
    if magnitude == 0.0:
        return 0.0

    return dot_product / magnitude


class _Adapter:
    """Base adapter that exposes nearest-neighbour queries for embeddings."""

    def contains(self, word: str) -> bool:
        raise NotImplementedError

    def nearest(self, word: str, *, limit: int) -> list[tuple[str, float]]:
        raise NotImplementedError

    def iter_keys(self) -> Iterator[str]:
        raise NotImplementedError


class _MappingAdapter(_Adapter):
    """Adapter for in-memory ``Mapping[str, Sequence[float]]`` embeddings."""

    def __init__(self, mapping: Mapping[str, Sequence[float]]) -> None:
        self._mapping = mapping

    def contains(self, word: str) -> bool:
        return word in self._mapping

    def nearest(self, word: str, *, limit: int) -> list[tuple[str, float]]:
        if word not in self._mapping:
            return []

        target_vector = self._mapping[word]
        scores: list[tuple[str, float]] = []
        for candidate, candidate_vector in self._mapping.items():
            if candidate == word:
                continue
            similarity = _cosine_similarity(target_vector, candidate_vector)
            if similarity == 0.0:
                continue
            scores.append((candidate, similarity))

        scores.sort(key=lambda pair: pair[1], reverse=True)
        if limit < len(scores):
            return scores[:limit]
        return scores

    def iter_keys(self) -> Iterator[str]:
        return iter(self._mapping.keys())


class _GensimAdapter(_Adapter):
    """Adapter that proxies to ``gensim`` ``KeyedVectors`` instances."""

    def __init__(self, keyed_vectors: Any) -> None:
        self._keyed_vectors = keyed_vectors

    def contains(self, word: str) -> bool:
        return word in self._keyed_vectors.key_to_index

    def nearest(self, word: str, *, limit: int) -> list[tuple[str, float]]:
        try:
            raw_neighbors = self._keyed_vectors.most_similar(word, topn=limit)
        except KeyError:
            return []

        return [(candidate, float(score)) for candidate, score in raw_neighbors]

    def iter_keys(self) -> Iterator[str]:
        return iter(self._keyed_vectors.key_to_index.keys())


class _SpaCyAdapter(_Adapter):
    """Adapter that interacts with spaCy ``Language`` objects."""

    def __init__(self, language: Any) -> None:
        self._language = language
        self._vectors = language.vocab.vectors
        spec = importlib.util.find_spec("numpy")
        if spec is None:
            raise RuntimeError("spaCy vector lexicons require NumPy to be installed.")
        self._numpy = importlib.import_module("numpy")

    def contains(self, word: str) -> bool:
        strings = self._language.vocab.strings
        return word in strings and strings[word] in self._vectors

    def nearest(self, word: str, *, limit: int) -> list[tuple[str, float]]:
        strings = self._language.vocab.strings
        if word not in strings:
            return []

        key = strings[word]
        if key not in self._vectors:
            return []

        vector = self._vectors.get(key)
        query = self._numpy.asarray([vector])
        keys, scores = self._vectors.most_similar(query, n=limit)
        candidates: list[tuple[str, float]] = []
        for candidate_key, score in zip(keys[0], scores[0]):
            candidate_word = strings[candidate_key]
            if candidate_word == word:
                continue
            candidates.append((candidate_word, float(score)))
        return candidates

    def iter_keys(self) -> Iterator[str]:
        strings = self._language.vocab.strings
        for key in self._vectors.keys():
            yield strings[key]


def _load_json_vectors(path: Path) -> Mapping[str, Sequence[float]]:
    """Load embeddings from a JSON mapping of token to vector list."""

    with path.open("r", encoding="utf8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, Mapping):
        raise RuntimeError("Vector JSON payload must map tokens to dense vectors.")

    validated: dict[str, list[float]] = {}
    for token, raw_vector in payload.items():
        if not isinstance(token, str):
            raise RuntimeError("Vector JSON keys must be strings.")
        if not isinstance(raw_vector, Sequence):
            raise RuntimeError(f"Vector for '{token}' must be a sequence of floats.")
        validated[token] = [float(value) for value in raw_vector]

    return validated


def _load_gensim_vectors(path: Path, *, binary: bool | None = None) -> Any:
    """Load ``gensim`` vectors from ``path``."""

    if importlib.util.find_spec("gensim") is None:
        raise RuntimeError(
            "The gensim package is required to load keyed vector embeddings."
        )

    keyed_vectors_module = importlib.import_module("gensim.models.keyedvectors")
    if binary is None:
        binary = path.suffix in {".bin", ".gz"}

    if path.suffix in {".kv", ".kv2"}:
        return keyed_vectors_module.KeyedVectors.load(str(path), mmap="r")

    return keyed_vectors_module.KeyedVectors.load_word2vec_format(
        str(path), binary=binary
    )


def _load_spacy_language(model_name: str) -> Any:
    """Load a spaCy language pipeline by name."""

    if importlib.util.find_spec("spacy") is None:
        raise RuntimeError(
            "spaCy is required to use spaCy-backed vector lexicons; install the 'vectors' extra."
        )

    spacy_module = importlib.import_module("spacy")
    return spacy_module.load(model_name)


def _resolve_source(source: Any | None) -> _Adapter | None:
    """Return an adapter instance for ``source`` if possible."""

    if source is None:
        return None

    if isinstance(source, _Adapter):
        return source

    if isinstance(source, Mapping):
        return _MappingAdapter(source)

    module_name = type(source).__module__
    if module_name.startswith("gensim") and hasattr(source, "most_similar"):
        return _GensimAdapter(source)

    if module_name.startswith("spacy") and hasattr(source, "vocab"):
        return _SpaCyAdapter(source)

    if isinstance(source, (str, Path)):
        text_source = str(source)
        if text_source.startswith("spacy:"):
            model = text_source.split(":", 1)[1]
            return _SpaCyAdapter(_load_spacy_language(model))

        resolved_path = Path(text_source)
        if not resolved_path.exists():
            raise RuntimeError(f"Vector source '{text_source}' does not exist.")

        suffix = resolved_path.suffix.lower()
        if suffix == ".json":
            return _MappingAdapter(_load_json_vectors(resolved_path))

        if suffix in {".kv", ".kv2", ".bin", ".gz", ".txt", ".vec"}:
            binary_flag = False if suffix in {".txt", ".vec"} else None
            return _GensimAdapter(
                _load_gensim_vectors(resolved_path, binary=binary_flag)
            )

    if hasattr(source, "most_similar") and hasattr(source, "key_to_index"):
        return _GensimAdapter(source)

    if hasattr(source, "vocab") and hasattr(source.vocab, "vectors"):
        return _SpaCyAdapter(source)

    raise RuntimeError("Unsupported vector source supplied to VectorLexicon.")


class VectorLexicon(LexiconBackend):
    """Lexicon implementation backed by dense word embeddings."""

    def __init__(
        self,
        *,
        source: Any | None = None,
        cache: Mapping[str, Sequence[str]] | None = None,
        cache_path: str | Path | None = None,
        max_neighbors: int = 50,
        min_similarity: float = 0.0,
        normalizer: Callable[[str], str] | None = None,
        case_sensitive: bool = False,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self._adapter = _resolve_source(source)
        self._max_neighbors = max(1, max_neighbors)
        self._min_similarity = min_similarity
        self._cache: MutableMapping[str, list[str]] = {}
        self._cache_path: Path | None
        self._cache_checksum: str | None = None
        if cache_path is not None:
            path = Path(cache_path)
            snapshot = _load_cache_file(path)
            self._cache.update(snapshot.entries)
            self._cache_checksum = snapshot.checksum
            self._cache_path = path
        else:
            self._cache_path = None
        if cache is not None:
            for key, values in cache.items():
                self._cache[str(key)] = [str(value) for value in values]
        self._cache_dirty = False
        self._case_sensitive = case_sensitive
        if normalizer is not None:
            self._lookup_normalizer: Callable[[str], str] = normalizer
            self._dedupe_normalizer: Callable[[str], str] = normalizer
        elif case_sensitive:
            self._lookup_normalizer = str.lower
            self._dedupe_normalizer = lambda value: value
        else:
            self._lookup_normalizer = str.lower
            self._dedupe_normalizer = str.lower

    def _normalize_for_lookup(self, word: str) -> str:
        return self._lookup_normalizer(word)

    def _normalize_for_dedupe(self, word: str) -> str:
        return self._dedupe_normalizer(word)

    def _fetch_neighbors(
        self, *, original: str, normalized: str, limit: int
    ) -> list[tuple[str, float]]:
        if self._adapter is None:
            return []

        attempts = [original]
        if normalized != original:
            attempts.append(normalized)

        collected: list[tuple[str, float]] = []
        seen: set[str] = set()
        for token in attempts:
            neighbors = self._adapter.nearest(token, limit=limit)
            for candidate, score in neighbors:
                if candidate in seen:
                    continue
                collected.append((candidate, score))
                seen.add(candidate)
            if len(collected) >= limit:
                break

        if len(collected) > limit:
            return collected[:limit]
        return collected

    def _ensure_cached(
        self, *, original: str, normalized: str, limit: int | None = None
    ) -> list[str]:
        cache_key = normalized if not self._case_sensitive else original
        if cache_key in self._cache:
            return self._cache[cache_key]

        neighbor_limit = self._max_neighbors if limit is None else max(1, limit)
        neighbors = self._fetch_neighbors(
            original=original, normalized=normalized, limit=neighbor_limit
        )
        synonyms: list[str] = []
        seen_candidates: set[str] = set()
        original_lookup = normalized
        original_dedupe = self._normalize_for_dedupe(original)
        for candidate, similarity in neighbors:
            if similarity < self._min_similarity:
                continue
            if self._case_sensitive:
                if candidate == original:
                    continue
                dedupe_key = self._normalize_for_dedupe(candidate)
                if dedupe_key == original_dedupe:
                    continue
            else:
                candidate_lookup = self._normalize_for_lookup(candidate)
                if candidate_lookup == original_lookup:
                    continue
                dedupe_key = candidate_lookup
            if dedupe_key in seen_candidates:
                continue
            seen_candidates.add(dedupe_key)
            synonyms.append(candidate)

        self._cache[cache_key] = synonyms
        if self._cache_path is not None:
            self._cache_dirty = True
        return synonyms

    def get_synonyms(
        self, word: str, pos: str | None = None, n: int = 5
    ) -> list[str]:
        normalized = self._normalize_for_lookup(word)
        synonyms = self._ensure_cached(original=word, normalized=normalized)
        return self._deterministic_sample(synonyms, limit=n, word=word, pos=pos)

    def precompute(self, word: str, *, limit: int | None = None) -> list[str]:
        """Populate the cache for ``word`` and return the stored synonyms."""

        normalized = self._normalize_for_lookup(word)
        return list(
            self._ensure_cached(original=word, normalized=normalized, limit=limit)
        )

    def iter_vocabulary(self) -> Iterator[str]:
        """Yield vocabulary tokens from the underlying embedding source."""

        if self._adapter is None:
            return iter(())
        return self._adapter.iter_keys()

    def export_cache(self) -> dict[str, list[str]]:
        """Return a copy of the in-memory synonym cache."""

        return {key: list(values) for key, values in self._cache.items()}

    @classmethod
    def load_cache(cls, path: str | Path) -> CacheSnapshot:
        """Load and validate a cache file for reuse."""

        return _load_cache_file(Path(path))

    def save_cache(self, path: str | Path | None = None) -> Path:
        """Persist the current cache to disk, returning the path used."""

        if path is None:
            if self._cache_path is None:
                raise RuntimeError("No cache path supplied to VectorLexicon.")
            target = self._cache_path
        else:
            target = Path(path)
            self._cache_path = target

        snapshot = _write_cache_file(target, self._cache)
        self._cache_checksum = snapshot.checksum
        self._cache_dirty = False
        return target

    def supports_pos(self, pos: str | None) -> bool:
        return True

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        source_name = self._adapter.__class__.__name__ if self._adapter else "None"
        return (
            f"VectorLexicon(source={source_name}, max_neighbors={self._max_neighbors}, "
            f"seed={self.seed!r})"
        )


def build_vector_cache(
    *,
    source: Any,
    words: Iterable[str],
    output_path: Path,
    max_neighbors: int = 50,
    min_similarity: float = 0.0,
    case_sensitive: bool = False,
    seed: int | None = None,
    normalizer: Callable[[str], str] | None = None,
) -> Path:
    """Generate a synonym cache for ``words`` using ``source`` embeddings."""

    lexicon = VectorLexicon(
        source=source,
        max_neighbors=max_neighbors,
        min_similarity=min_similarity,
        case_sensitive=case_sensitive,
        normalizer=normalizer,
        seed=seed,
    )

    for word in words:
        lexicon.precompute(word)

    return lexicon.save_cache(output_path)


def load_vector_source(spec: str) -> Any:
    """Resolve ``spec`` strings for the cache-building CLI."""

    if spec.startswith("spacy:"):
        model_name = spec.split(":", 1)[1]
        return _load_spacy_language(model_name)

    path = Path(spec).expanduser()
    if not path.exists():
        raise RuntimeError(f"Vector source '{spec}' does not exist.")

    if path.suffix.lower() == ".json":
        return _load_json_vectors(path)

    return _load_gensim_vectors(path)


def _parse_cli(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m glitchlings.lexicon.vector",
        description="Precompute synonym caches for the vector lexicon backend.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help=(
            "Vector source specification. Use 'spacy:<model>' for spaCy pipelines "
            "or provide a path to a gensim KeyedVectors/word2vec file."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to the JSON file that will receive the synonym cache.",
    )
    parser.add_argument(
        "--tokens",
        type=Path,
        help="Optional newline-delimited vocabulary file to restrict generation.",
    )
    parser.add_argument(
        "--max-neighbors",
        type=int,
        default=50,
        help="Number of nearest neighbours to cache per token (default: 50).",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
        help="Minimum cosine similarity required to keep a synonym (default: 0.0).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional deterministic seed to bake into the resulting cache.",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Preserve original casing instead of lower-casing cache keys.",
    )
    parser.add_argument(
        "--normalizer",
        choices=["lower", "identity"],
        default="lower",
        help="Token normalization strategy for cache keys (default: lower).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing cache file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional maximum number of tokens to process.",
    )
    return parser.parse_args(argv)


def _iter_tokens_from_file(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf8") as handle:
        for line in handle:
            token = line.strip()
            if token:
                yield token


def main(argv: Sequence[str] | None = None) -> int:
    """Entry-point for ``python -m glitchlings.lexicon.vector``."""

    args = _parse_cli(argv)

    if args.output.exists() and not args.overwrite:
        raise SystemExit(
            f"Refusing to overwrite existing cache at {args.output!s}; pass --overwrite."
        )

    if args.normalizer == "lower":
        normalizer: Callable[[str], str] | None = (
            None if args.case_sensitive else str.lower
        )
    else:
        normalizer = lambda value: value

    source = load_vector_source(args.source)
    if args.tokens is not None:
        token_iter: Iterable[str] = _iter_tokens_from_file(args.tokens)
    else:
        lexicon = VectorLexicon(
            source=source,
            max_neighbors=args.max_neighbors,
            min_similarity=args.min_similarity,
            case_sensitive=args.case_sensitive,
            normalizer=normalizer,
            seed=args.seed,
        )
        token_iter = lexicon.iter_vocabulary()

    if args.limit is not None:
        token_iter = (token for index, token in enumerate(token_iter) if index < args.limit)

    build_vector_cache(
        source=source,
        words=token_iter,
        output_path=args.output,
        max_neighbors=args.max_neighbors,
        min_similarity=args.min_similarity,
        case_sensitive=args.case_sensitive,
        seed=args.seed,
        normalizer=normalizer,
    )

    return 0


if __name__ == "__main__":  # pragma: no cover - manual CLI entry point
    sys.exit(main())


__all__ = ["VectorLexicon", "build_vector_cache", "load_vector_source", "main"]

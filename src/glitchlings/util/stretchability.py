"""Stretchability scoring and candidate selection for Hokey."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol, Sequence, TypedDict, cast

from glitchlings.zoo import assets

# Regexes reused across the module
TOKEN_REGEX = re.compile(r"\w+|\W+")
ALPHA_REGEX = re.compile(r"[A-Za-z]")
EMOJI_REGEX = re.compile(r"[\U0001F300-\U0001FAFF]")
CLAUSE_PUNCTUATION = {".", "?", "!", ";"}


class HokeyAssets(TypedDict):
    lexical_prior: dict[str, float]
    interjections: list[str]
    intensifiers: list[str]
    evaluatives: list[str]
    positive_lexicon: list[str]
    negative_lexicon: list[str]


class RandomLike(Protocol):
    """Interface for RNGs that expose ``random()``."""

    def random(self) -> float: ...


# Lexical prior probabilities and pragmatic lexica shared with the Rust fast path.
def _load_assets() -> HokeyAssets:
    with assets.open_text("hokey_assets.json") as payload:
        data: Any = json.load(payload)
    return cast(HokeyAssets, data)


_ASSETS = _load_assets()
LEXICAL_PRIOR: dict[str, float] = {
    token: float(score) for token, score in _ASSETS["lexical_prior"].items()
}

# Pragmatic lexica for POS/discourse cues
INTERJECTIONS = frozenset(_ASSETS["interjections"])
INTENSIFIERS = frozenset(_ASSETS["intensifiers"])
EVALUATIVES = frozenset(_ASSETS["evaluatives"])
POSITIVE_LEXICON = frozenset(_ASSETS["positive_lexicon"])
NEGATIVE_LEXICON = frozenset(_ASSETS["negative_lexicon"])

VOWELS = set("aeiouy")
SONORANT_CODAS = set("rlmnwyh")
SIBILANT_CODAS = {"s", "z", "x", "c", "j", "sh", "zh"}
DIGRAPHS = {
    "aa",
    "ae",
    "ai",
    "ay",
    "ee",
    "ei",
    "ey",
    "ie",
    "oa",
    "oe",
    "oi",
    "oo",
    "ou",
    "ue",
    "ui",
}

MAX_CANDIDATES_PER_CLAUSE = 4
MIN_SCORE_THRESHOLD = 0.18


@dataclass(slots=True)
class TokenInfo:
    text: str
    start: int
    end: int
    is_word: bool
    clause_index: int
    preceding_punct: str
    following_punct: str
    index: int

    @property
    def normalised(self) -> str:
        return self.text.lower()


@dataclass(slots=True)
class StretchabilityFeatures:
    lexical: float
    pos: float
    sentiment: float
    phonotactic: float
    context: float
    sentiment_swing: float

    def intensity(self) -> float:
        """Map features to an intensity scalar in [0, 1.5]."""
        emphasis = 0.6 * self.context + 0.4 * self.sentiment_swing
        return max(0.0, min(1.5, 0.5 * (self.lexical + self.phonotactic) + emphasis))


@dataclass(slots=True)
class StretchCandidate:
    token: TokenInfo
    score: float
    features: StretchabilityFeatures


class StretchabilityAnalyzer:
    """Compute stretchability scores and select candidates."""

    def __init__(
        self,
        *,
        lexical_prior: dict[str, float] | None = None,
        weights: tuple[float, float, float, float, float] = (0.32, 0.18, 0.14, 0.22, 0.14),
    ) -> None:
        self.lexical_prior = lexical_prior or LEXICAL_PRIOR
        self.weights = weights

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def tokenise(self, text: str) -> list[TokenInfo]:
        """Tokenise text preserving separator tokens."""
        return self._tokenise(text)

    def analyse(self, text: str) -> list[StretchCandidate]:
        if not text:
            return []
        tokens = self._tokenise(text)
        return self.analyse_tokens(tokens)

    def analyse_tokens(self, tokens: Sequence[TokenInfo]) -> list[StretchCandidate]:
        candidates: list[StretchCandidate] = []
        for idx, token in enumerate(tokens):
            if not token.is_word:
                continue
            if self._excluded(token, tokens, idx):
                continue

            features = self._compute_features(token, tokens, idx)
            score = self._composite_score(features)
            if score < MIN_SCORE_THRESHOLD:
                continue
            candidates.append(StretchCandidate(token=token, score=score, features=features))
        return candidates

    def select_candidates(
        self,
        candidates: Sequence[StretchCandidate],
        *,
        rate: float,
        rng: RandomLike,
    ) -> list[StretchCandidate]:
        if not candidates or rate <= 0:
            return []

        grouped: dict[int, list[StretchCandidate]] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.token.clause_index, []).append(candidate)

        selected: list[StretchCandidate] = []
        total_expected = max(0, min(len(candidates), int(round(len(candidates) * rate))))

        for clause_index in sorted(grouped):
            clause_candidates = sorted(
                grouped[clause_index], key=lambda c: (-c.score, c.token.start)
            )
            clause_candidates = clause_candidates[:MAX_CANDIDATES_PER_CLAUSE]
            clause_quota = max(
                0, min(len(clause_candidates), int(round(len(clause_candidates) * rate)))
            )

            provisional: list[StretchCandidate] = []
            for candidate in clause_candidates:
                probability = min(1.0, rate * (0.35 + 0.65 * candidate.score))
                if rng.random() < probability:
                    provisional.append(candidate)
                if len(provisional) >= clause_quota:
                    break

            if len(provisional) < clause_quota:
                leftovers = [c for c in clause_candidates if c not in provisional]
                needed = clause_quota - len(provisional)
                provisional.extend(leftovers[:needed])

            selected.extend(provisional)

        if len(selected) < total_expected:
            remaining = [c for c in candidates if c not in selected]
            remaining.sort(key=lambda c: (-c.score, c.token.start))
            selected.extend(remaining[: total_expected - len(selected)])

        # Keep deterministic order by position
        selected.sort(key=lambda c: c.token.start)
        return selected

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _tokenise(self, text: str) -> list[TokenInfo]:
        tokens: list[TokenInfo] = []
        clause_index = 0
        matches = list(TOKEN_REGEX.finditer(text))
        for idx, match in enumerate(matches):
            token_text = match.group(0)
            is_word = bool(ALPHA_REGEX.search(token_text)) and token_text.strip().isalnum()
            preceding = matches[idx - 1].group(0) if idx > 0 else ""
            following = matches[idx + 1].group(0) if idx + 1 < len(matches) else ""
            tokens.append(
                TokenInfo(
                    text=token_text,
                    start=match.start(),
                    end=match.end(),
                    is_word=is_word,
                    clause_index=clause_index,
                    preceding_punct=preceding,
                    following_punct=following,
                    index=idx,
                )
            )
            if any(ch in CLAUSE_PUNCTUATION for ch in token_text):
                clause_index += 1
        return tokens

    def _excluded(self, token: TokenInfo, tokens: Sequence[TokenInfo], index: int) -> bool:
        text = token.text
        normalised = token.normalised
        if sum(ch.isalpha() for ch in text) < 2:
            return True
        if any(ch.isdigit() for ch in text):
            return True
        lowered = normalised
        if "http" in lowered or "www" in lowered or "//" in lowered:
            return True
        if any(symbol in text for symbol in {"#", "@", "&", "{", "}", "<", ">"}):
            return True
        if "_" in text:
            return True
        if "/" in text or "\\" in text:
            return True

        # Heuristic proper noun check: Title case mid-clause counts as proper noun
        if text[:1].isupper() and text[1:].islower():
            previous_clause_start = index == 0
            if not previous_clause_start:
                for prior in reversed(tokens[:index]):
                    stripped = prior.text.strip()
                    if not stripped:
                        continue
                    if stripped[-1] in CLAUSE_PUNCTUATION:
                        previous_clause_start = True
                    break
            if not previous_clause_start:
                return True
        return False

    def _compute_features(
        self, token: TokenInfo, tokens: Sequence[TokenInfo], index: int
    ) -> StretchabilityFeatures:
        lexical = self.lexical_prior.get(token.normalised, 0.12)
        pos_score = self._pos_score(token)
        sentiment_score, sentiment_swing = self._sentiment(tokens, index)
        phon_score = self._phonotactic(token.normalised)
        context_score = self._contextual(token, tokens, index)
        return StretchabilityFeatures(
            lexical=lexical,
            pos=pos_score,
            sentiment=sentiment_score,
            phonotactic=phon_score,
            context=context_score,
            sentiment_swing=sentiment_swing,
        )

    def _composite_score(self, features: StretchabilityFeatures) -> float:
        lex_w, pos_w, sent_w, phon_w, ctx_w = self.weights
        weighted = (
            lex_w * features.lexical
            + pos_w * features.pos
            + sent_w * features.sentiment
            + phon_w * features.phonotactic
            + ctx_w * features.context
        )
        total_weight = sum(self.weights)
        score = weighted / total_weight if total_weight else 0.0
        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Feature helpers
    # ------------------------------------------------------------------
    def _pos_score(self, token: TokenInfo) -> float:
        normalised = token.normalised
        if normalised in INTERJECTIONS:
            return 0.95
        if normalised in INTENSIFIERS:
            return 0.85
        if normalised in EVALUATIVES:
            return 0.7
        if normalised.endswith("ly"):
            return 0.55
        if token.text.isupper() and len(token.text) > 1:
            return 0.65
        return 0.3

    def _sentiment(self, tokens: Sequence[TokenInfo], index: int) -> tuple[float, float]:
        window = [tok for tok in tokens[max(0, index - 2) : index + 3] if tok.is_word]
        if not window:
            return 0.5, 0.0
        pos_hits = sum(1 for tok in window if tok.normalised in POSITIVE_LEXICON)
        neg_hits = sum(1 for tok in window if tok.normalised in NEGATIVE_LEXICON)
        total = len(window)
        balance = (pos_hits - neg_hits) / total
        sentiment_score = 0.5 + 0.5 * max(-1.0, min(1.0, balance))
        swing = abs(balance)
        return sentiment_score, swing

    def _phonotactic(self, normalised: str) -> float:
        if not any(ch in VOWELS for ch in normalised):
            return 0.0
        score = 0.25
        if any(normalised.endswith(c) for c in SONORANT_CODAS):
            score += 0.2
        if any(normalised.endswith(c) for c in SIBILANT_CODAS):
            score += 0.18
        if any(digraph in normalised for digraph in DIGRAPHS):
            score += 0.22
        if re.search(r"[aeiouy]{2,}", normalised):
            score += 0.22
        if re.search(r"(.)(?!\1)(.)\1", normalised):
            score += 0.08
        return max(0.0, min(1.0, score))

    def _contextual(self, token: TokenInfo, tokens: Sequence[TokenInfo], index: int) -> float:
        score = 0.2
        before = token.preceding_punct
        after = token.following_punct
        token_text = token.text
        if after and after.count("!") >= 1:
            score += 0.25
        if after and after.count("?") >= 1:
            score += 0.2
        if before and before.count("!") >= 2:
            score += 0.2
        if after and ("!!" in after or "??" in after):
            score += 0.15
        if token_text.isupper() and len(token_text) > 1:
            score += 0.25
        if EMOJI_REGEX.search(before or "") or EMOJI_REGEX.search(after or ""):
            score += 0.15
        # Clause-final emphasis
        if index + 1 < len(tokens):
            trailing = tokens[index + 1].text
            if any(p in trailing for p in {"!!!", "??", "?!"}):
                score += 0.2
        return max(0.0, min(1.0, score))


__all__ = [
    "StretchabilityAnalyzer",
    "StretchCandidate",
    "StretchabilityFeatures",
    "TokenInfo",
    "RandomLike",
]

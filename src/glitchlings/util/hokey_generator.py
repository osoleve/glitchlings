"""Hokey expressive lengthening generator."""

from __future__ import annotations

from dataclasses import dataclass

from .stretch_locator import StretchSite, apply_stretch, find_stretch_site
from .stretchability import (
    StretchabilityAnalyzer,
    StretchabilityFeatures,
)


@dataclass(slots=True)
class HokeyConfig:
    rate: float = 0.3
    extension_min: int = 2
    extension_max: int = 5
    base_p: float = 0.45
    word_length_threshold: int = 6


@dataclass(slots=True)
class StretchEvent:
    token_index: int
    original: str
    stretched: str
    repeats: int
    site: StretchSite
    score: float
    features: StretchabilityFeatures


class NegativeBinomialSampler:
    """Sample stretch lengths from a clipped negative binomial distribution."""

    def __init__(self, base_p: float = 0.45) -> None:
        self.base_p = base_p

    def sample(
        self,
        rng: RandomLike,
        *,
        intensity: float,
        minimum: int,
        maximum: int,
    ) -> int:
        minimum = max(0, int(minimum))
        maximum = max(minimum, int(maximum))
        if maximum == 0:
            return 0
        if maximum == minimum:
            return maximum

        r = max(1, int(round(1 + 2 * intensity)))
        adjusted_p = self.base_p / (1.0 + 0.75 * max(0.0, intensity))
        adjusted_p = max(0.05, min(0.95, adjusted_p))
        failures = sum(self._geometric_sample(rng, adjusted_p) for _ in range(r))
        extra = minimum + failures
        return max(minimum, min(maximum, extra))

    @staticmethod
    def _geometric_sample(rng: RandomLike, p: float) -> int:
        count = 0
        while rng.random() > p:
            count += 1
        return count


class HokeyGenerator:
    """Full expressive lengthening pipeline."""

    def __init__(
        self,
        analyzer: StretchabilityAnalyzer | None = None,
        sampler: NegativeBinomialSampler | None = None,
    ) -> None:
        self.analyzer = analyzer or StretchabilityAnalyzer()
        self.sampler = sampler or NegativeBinomialSampler()

    def generate(
        self,
        text: str,
        *,
        rng: RandomLike,
        config: HokeyConfig,
    ) -> tuple[str, list[StretchEvent]]:
        if not text:
            return text, []

        if config.base_p != self.sampler.base_p:
            self.sampler.base_p = config.base_p

        tokens = self.analyzer.tokenise(text)
        candidates = self.analyzer.analyse_tokens(tokens)
        selected = self.analyzer.select_candidates(candidates, rate=config.rate, rng=rng)
        if not selected:
            return text, []

        token_strings = [token.text for token in tokens]
        events: list[StretchEvent] = []

        for candidate in selected:
            token_idx = candidate.token.index
            original = token_strings[token_idx]
            site = find_stretch_site(original)
            if site is None:
                continue

            intensity = min(1.5, candidate.features.intensity() + 0.35 * candidate.score)
            alpha_count = sum(1 for ch in original if ch.isalpha())
            if (
                config.word_length_threshold > 0
                and alpha_count > config.word_length_threshold * 2
            ):
                continue
            if config.word_length_threshold > 0 and alpha_count > config.word_length_threshold:
                excess = alpha_count - config.word_length_threshold
                intensity = intensity / (1.0 + 0.35 * excess)
                if candidate.score < 0.35 and excess >= 2:
                    continue
            intensity = max(0.05, intensity)

            repeats = self.sampler.sample(
                rng,
                intensity=intensity,
                minimum=config.extension_min,
                maximum=config.extension_max,
            )
            if repeats <= 0:
                continue

            stretched_word = apply_stretch(original, site, repeats)
            token_strings[token_idx] = stretched_word
            events.append(
                StretchEvent(
                    token_index=token_idx,
                    original=original,
                    stretched=stretched_word,
                    repeats=repeats,
                    site=site,
                    score=candidate.score,
                    features=candidate.features,
                )
            )

        return "".join(token_strings), events


__all__ = ["HokeyGenerator", "HokeyConfig", "StretchEvent", "NegativeBinomialSampler"]

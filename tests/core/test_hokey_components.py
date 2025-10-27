"""Unit tests for Hokey's scoring and stretch locator modules."""

from __future__ import annotations

import random

from glitchlings.util.hokey_generator import NegativeBinomialSampler
from glitchlings.util.stretch_locator import apply_stretch, find_stretch_site
from glitchlings.util.stretchability import StretchabilityAnalyzer


def test_analyzer_prioritises_lexically_salient_tokens():
    """The analyzer should give higher scores to known expressive items."""
    analyzer = StretchabilityAnalyzer()
    tokens = analyzer.tokenise("so maybe unbelievably long wow")
    candidates = analyzer.analyse_tokens(tokens)
    scores = {candidate.token.text: candidate.score for candidate in candidates}

    assert scores["so"] > scores["maybe"]
    assert scores["wow"] > scores["long"]


def test_candidate_selection_is_clause_aware():
    """Selection respects clause boundaries when applying the rate."""
    analyzer = StretchabilityAnalyzer()
    text = "wow so fun! this is so rad and so bright!"
    candidates = analyzer.analyse(text)
    selected = analyzer.select_candidates(candidates, rate=0.5, rng=random.Random(7))

    clause_ids = {candidate.token.clause_index for candidate in selected}
    assert clause_ids == {0, 1}
    assert len(selected) <= len(candidates)


def test_stretch_locator_handles_varied_word_shapes():
    """Different word shapes should map to sensible stretch sites."""
    assert apply_stretch("cute", find_stretch_site("cute"), 3) == "cuuuute"
    stretched_goal = apply_stretch("goal", find_stretch_site("goal"), 3)
    assert stretched_goal.endswith('l')
    assert 'ooo' in stretched_goal
    assert 'aaaa' in stretched_goal
    assert apply_stretch("yes", find_stretch_site("yes"), 3) == "yessss"


def test_negative_binomial_sampler_respects_bounds():
    """Sampler should always stay within configured bounds."""
    sampler = NegativeBinomialSampler(base_p=0.4)
    rng = random.Random(12)
    lengths = {
        sampler.sample(rng, intensity=1.0, minimum=2, maximum=6)
        for _ in range(30)
    }

    assert all(2 <= length <= 6 for length in lengths)
    assert max(lengths) > min(lengths)

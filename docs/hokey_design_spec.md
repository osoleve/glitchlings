# Hokey Design Specification

**Author:** Glitchlings Expressive Lengthening Working Group  \
**Last Updated:** 2025-10-26

## 1. Overview
Hokey is Glitchlings' expressive lengthening agent. The refreshed design grounds its
behaviour in two strands of sociolinguistic research:

* Gray et al. (2020) – expressive lengthening as affect signalling on social media, with
  correlations to sentiment, vowel nuclei, and sibilant codas.
* Brody & Diakopoulos (2011) – pragmatic cues (interjections, punctuation, discourse
  markers) that predict when people stretch tokens for emphasis online.

The implementation translates these findings into a deterministic scoring and generation
pipeline that favours naturally stretchable tokens, chooses linguistically plausible
stretch sites, and samples human-like stretch lengths.

## 2. Stretchability Score
For every alphabetic token, Hokey computes a composite *Stretchability Score*.
Tokens that contain numbers, code identifiers, URLs, or social tags (`@`, `#`) are
filtered out early.

```
S = w_lex * L + w_pos * P + w_sent * Σ + w_phon * Φ + w_ctx * C
```

Where each component is normalised to `[0, 1]` before weighting:

| Component | Description | Motivation |
| --- | --- | --- |
| `L` | Lexical prior derived from social-media frequency of stretched spellings. | Mirrors Gray et al.'s observation that some lemmas ("so", "lol", "yeah") are stretched far more often than others. |
| `P` | POS and discourse heuristics. Interjections, intensifiers, and sentence-final particles receive boosts; obvious nouns are damped. | Brody & Diakopoulos highlight pragmatic classes that invite elongation. |
| `Σ` | Sentiment windowing over a 5-token neighbourhood using polarity lexica. Positive bursts raise the score; sharply negative spans dampen it. | Expressive lengthening co-occurs with affect spikes. |
| `Φ` | Phonotactic cues: vowel nuclei, digraphs, sibilant/sonorant codas, and alternating bigrams. | Preserves pronounceability and keeps stretches anchored to vowel peaks. |
| `C` | Context cues such as terminal punctuation (`!`, `?`), repeated punctuation, capitalisation, and emoji adjacency. | Captures immediate emphasis signals. |

Default weights: `w_lex = 0.32`, `w_pos = 0.18`, `w_sent = 0.14`, `w_phon = 0.22`,
`w_ctx = 0.14`. We clamp `S` into `[0, 1]` and treat values below `0.18` as
noise.

## 3. Candidate Selection
Tokens are grouped by clause (split on `.`, `?`, `!`, and `;`). Within each clause
we retain the top 4 scoring tokens. The *rate* parameter scales the sampling
probability for each candidate:

```
P(select | S, rate) = min(1, rate * (0.35 + 0.65 * S))
```

If the stochastic pass produces fewer tokens than the rate implies, the remaining
quota is filled by the highest-scoring leftovers to maintain deterministic
coverage when needed.

Exclusion rules ensure we never stretch:

* Mixed-case proper nouns unless they appear sentence-initial.
* Tokens containing digits, URL fragments, or Markdown/code punctuation.
* Tokens shorter than two alphabetic characters.

## 4. Stretch Site Identification
The Rust implementation parses candidate words into grapheme clusters and applies
heuristics tailored to four frequent shape families:

1. **Vowel-final tokens** – extend the final vowel nucleus (`too → tooo`).
2. **CVCe patterns** – treat the `CV` nucleus as stretchable while preserving the
   silent `e` (`cute → cuuute`).
3. **Digraph nuclei** – repeat the entire digraph for vowel sequences such as
   `oa`, `ee`, `ai`, `oo`, `ie`, `ue` (`goal → goooaaaal`).
4. **Sibilant/Sonorant codas** – optionally trail an extra consonant stretch after
   the nucleus for forms like `yes → yesss`, `hmm → hmmmm`.

The module returns a `StretchSite` (`start`, `end`, `grapheme`, `category`), which the
length sampler consumes. When no heuristic matches, Hokey falls back to the longest
vowel span.

## 5. Length Sampling
Stretch length follows a clipped negative-binomial distribution to produce rare but
plausible long runs.

```
extra = min(max_extra,
            max(min_extra,
                NB(r = 1 + 2 * intensity, p = base_p / (1 + 0.75 * intensity))))
```

* `intensity` is derived from the stretchability score, contextual emphasis, and
  sentiment slope.
* `base_p` defaults to `0.45`; lower values yield heavier tails.
* The sampler never returns fewer than `min_extra` characters and honours the
  global `extension_max` cap.

## 6. Generation Pipeline
`rust/zoo/src/hokey.rs` orchestrates the full flow:

1. Tokenise text with separator preservation.
2. Score and filter candidates via the Rust stretchability analyser.
3. For each selected candidate, locate the stretch site.
4. Sample a stretch length using contextual intensity.
5. Apply the stretch while maintaining Unicode boundaries and original casing.

All randomness flows through the glitchling's RNG. The historical Python generator
and helper modules have been removed; the Python shim now delegates directly to the
compiled Rust pipeline and no longer surfaces trace events or intermediate data.

## 7. Rust Implementation
The Rust implementation mirrors the Python pipeline:

* Ported lexical prior and heuristic tables to `rust/zoo/src/hokey.rs`.
* Implemented a deterministic scorer and negative-binomial sampler using the
  `rand` traits already available in the crate.
* Trace replay now lives exclusively in Rust. The Python shim delegates all
  generation to the compiled operation and provides no tracing hooks.

Hokey relies exclusively on the compiled Rust pipeline.

## 8. Testing Strategy

* `tests/core/test_hokey.py` – Validates clause-aware scoring, sentiment
  effects, and deterministic site selection via the Rust-backed shim.
* `tests/rust/test_rust_backed_glitchlings.py` – Smoke coverage for the compiled
  extension and error propagation from Rust into Python.

## 9. Future Work

* Explore data-driven estimation of lexical priors from live corpora.
* Learn sentiment weights from downstream reinforcement feedback rather than
  static lexica.
* Investigate multi-token stretches ("no way" → "nooooo way") once the clause
  windowing API supports span-level operations.

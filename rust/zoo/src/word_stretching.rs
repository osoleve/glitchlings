use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use serde::Deserialize;
use std::borrow::Cow;
use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

use crate::operations::{TextOperation, OperationError, OperationRng};
use crate::text_buffer::TextBuffer;

static TOKEN_REGEX: OnceLock<Regex> = OnceLock::new();

fn token_regex() -> &'static Regex {
    TOKEN_REGEX.get_or_init(|| Regex::new(r"\w+|\W+").unwrap())
}

const CLAUSE_PUNCT: [char; 4] = ['.', '?', '!', ';'];

const HOKEY_ASSETS: &str = include_str!(concat!(env!("OUT_DIR"), "/hokey_assets.json"));

#[derive(Deserialize)]
struct RawHokeyAssets {
    lexical_prior: HashMap<String, f64>,
    interjections: Vec<String>,
    intensifiers: Vec<String>,
    evaluatives: Vec<String>,
    positive_lexicon: Vec<String>,
    negative_lexicon: Vec<String>,
}

struct HokeyAssets {
    lexical_prior: HashMap<String, f64>,
    interjections: HashSet<String>,
    intensifiers: HashSet<String>,
    evaluatives: HashSet<String>,
    positive_lexicon: HashSet<String>,
    negative_lexicon: HashSet<String>,
}

impl From<RawHokeyAssets> for HokeyAssets {
    fn from(value: RawHokeyAssets) -> Self {
        Self {
            lexical_prior: value.lexical_prior,
            interjections: value.interjections.into_iter().collect(),
            intensifiers: value.intensifiers.into_iter().collect(),
            evaluatives: value.evaluatives.into_iter().collect(),
            positive_lexicon: value.positive_lexicon.into_iter().collect(),
            negative_lexicon: value.negative_lexicon.into_iter().collect(),
        }
    }
}

fn assets() -> &'static HokeyAssets {
    static ASSETS: OnceLock<HokeyAssets> = OnceLock::new();
    ASSETS.get_or_init(|| {
        let raw: RawHokeyAssets =
            serde_json::from_str(HOKEY_ASSETS).expect("failed to parse Hokey asset payload");
        raw.into()
    })
}

fn lexical_prior() -> &'static HashMap<String, f64> {
    &assets().lexical_prior
}

fn interjections() -> &'static HashSet<String> {
    &assets().interjections
}

fn intensifiers() -> &'static HashSet<String> {
    &assets().intensifiers
}

fn evaluatives() -> &'static HashSet<String> {
    &assets().evaluatives
}

fn positive_lexicon() -> &'static HashSet<String> {
    &assets().positive_lexicon
}

fn negative_lexicon() -> &'static HashSet<String> {
    &assets().negative_lexicon
}

/// Token information with lazy-computed cached values.
/// Only computes lowercase/chars/etc. when actually needed.
struct TokenInfo<'a> {
    text: Cow<'a, str>,
    start: usize,
    is_word: bool,
    clause_index: usize,
    /// Whether this token is at the start of a clause (after .?!; or at index 0)
    at_clause_start: bool,
    /// Pre-computed lowercase for sentiment lookup (only set for word tokens)
    lowercase: Option<String>,
}

/// Cached analysis data, computed lazily only for tokens that become candidates
struct TokenCache {
    lowercase: String,
    lowercase_chars: Vec<char>,
    alpha_indices: Vec<usize>,
}

#[derive(Clone)]
struct StretchFeatures {
    lexical: f64,
    pos: f64,
    sentiment: f64,
    phonotactic: f64,
    context: f64,
    sentiment_swing: f64,
}

impl StretchFeatures {
    fn intensity(&self) -> f64 {
        let emphasis = 0.6 * self.context + 0.4 * self.sentiment_swing;
        let base = 0.5 * (self.lexical + self.phonotactic);
        (base + emphasis).clamp(0.0, 1.5)
    }
}

#[derive(Clone)]
struct StretchCandidate {
    token_index: usize,
    score: f64,
    features: StretchFeatures,
    /// Pre-computed stretch site to avoid recomputation during apply
    stretch_site: Option<StretchSite>,
}

#[derive(Clone, Copy)]
struct StretchSite {
    start: usize,
    end: usize,
}

#[derive(Debug, Clone)]
pub struct WordStretchOp {
    pub rate: f64,
    pub extension_min: i32,
    pub extension_max: i32,
    pub word_length_threshold: usize,
    pub base_p: f64,
}

impl WordStretchOp {
    fn tokenise<'a>(&self, text: &'a str) -> Vec<TokenInfo<'a>> {
        let regex = token_regex();
        // Estimate token count: ~1 token per 5 chars on average (words + separators)
        let estimated_tokens = text.len() / 5 + 1;
        let mut tokens = Vec::with_capacity(estimated_tokens);
        let mut clause_index = 0usize;
        let mut at_clause_start = true; // First token is always at clause start

        for mat in regex.find_iter(text) {
            let token_text = mat.as_str();
            // Check is_word by examining characters once
            let mut has_alpha = false;
            let mut has_non_alnum = false;
            for c in token_text.trim().chars() {
                if c.is_alphabetic() {
                    has_alpha = true;
                }
                if !c.is_alphanumeric() {
                    has_non_alnum = true;
                    break;
                }
            }
            let is_word = has_alpha && !has_non_alnum;

            // Pre-compute lowercase for word tokens (needed for sentiment lookups)
            let lowercase = if is_word {
                Some(token_text.to_lowercase())
            } else {
                None
            };

            // Use Cow::Borrowed to avoid allocation - the token_text lives as long as input text
            tokens.push(TokenInfo {
                text: Cow::Borrowed(token_text),
                start: mat.start(),
                is_word,
                clause_index,
                at_clause_start,
                lowercase,
            });

            // Check for clause punctuation to update state for next token
            let has_clause_punct = token_text.chars().any(|c| CLAUSE_PUNCT.contains(&c));
            if has_clause_punct {
                clause_index += 1;
                at_clause_start = true;
            } else if !token_text.trim().is_empty() {
                // Non-empty, non-punct token means next token is not at clause start
                at_clause_start = false;
            }
        }
        tokens
    }

    /// Build cached analysis data for a token. Called lazily only for candidates.
    fn build_cache(&self, token: &TokenInfo<'_>) -> TokenCache {
        // Use pre-computed lowercase if available
        let lower = token
            .lowercase
            .clone()
            .unwrap_or_else(|| token.text.to_lowercase());
        let lower_chars: Vec<char> = lower.chars().collect();
        let alpha_idx: Vec<usize> = token
            .text
            .chars()
            .enumerate()
            .filter_map(|(idx, ch)| if ch.is_alphabetic() { Some(idx) } else { None })
            .collect();
        TokenCache {
            lowercase: lower,
            lowercase_chars: lower_chars,
            alpha_indices: alpha_idx,
        }
    }

    fn excluded(&self, tokens: &[TokenInfo<'_>], index: usize) -> bool {
        let token = &tokens[index];
        let text: &str = &token.text;

        // Check alpha count - most common exclusion reason, check first
        let alpha_count = text.chars().filter(|c| c.is_alphabetic()).count();
        if alpha_count < 2 {
            return true;
        }

        // Check for digits
        if text.chars().any(|c| c.is_ascii_digit()) {
            return true;
        }

        // Check for special characters (cheap byte-level check)
        if text.contains('#')
            || text.contains('@')
            || text.contains('&')
            || text.contains('{')
            || text.contains('}')
            || text.contains('<')
            || text.contains('>')
            || text.contains('_')
            || text.contains('/')
            || text.contains('\\')
        {
            return true;
        }

        // URL check - use text directly (case insensitive contains)
        let text_lower = text.to_lowercase();
        if text_lower.contains("http") || text_lower.contains("www") || text_lower.contains("//") {
            return true;
        }

        // Title case check - use cached at_clause_start flag
        if text
            .chars()
            .next()
            .map(|c| c.is_uppercase())
            .unwrap_or(false)
            && text.chars().skip(1).all(|c| c.is_lowercase())
        {
            // Use pre-computed clause start flag instead of backward scan
            if !token.at_clause_start {
                return true;
            }
        }
        false
    }

    fn compute_features(
        &self,
        tokens: &[TokenInfo<'_>],
        index: usize,
        cache: &TokenCache,
    ) -> StretchFeatures {
        let token = &tokens[index];
        let normalised = &cache.lowercase;
        let lexical = *lexical_prior().get(normalised.as_str()).unwrap_or(&0.12);
        let pos = self.pos_score(&token.text, normalised);
        let (sentiment, swing) = self.sentiment(tokens, index);
        let phonotactic = self.phonotactic_with_cache(&cache.lowercase_chars);
        let context = self.context_score(tokens, index);
        StretchFeatures {
            lexical,
            pos,
            sentiment,
            phonotactic,
            context,
            sentiment_swing: swing,
        }
    }

    fn pos_score(&self, original: &str, normalised: &str) -> f64 {
        if interjections().contains(normalised) {
            0.95
        } else if intensifiers().contains(normalised) {
            0.85
        } else if evaluatives().contains(normalised) {
            0.70
        } else if normalised.ends_with("ly") {
            0.55
        } else if original.chars().all(|c| c.is_uppercase()) && original.chars().count() > 1 {
            0.65
        } else {
            0.30
        }
    }

    fn sentiment(&self, tokens: &[TokenInfo<'_>], index: usize) -> (f64, f64) {
        let start = index.saturating_sub(2);
        let end = (index + 3).min(tokens.len());

        // Count sentiment hits using pre-computed lowercase
        let mut pos_hits = 0usize;
        let mut neg_hits = 0usize;
        let mut word_count = 0usize;

        for token in &tokens[start..end] {
            if token.is_word {
                word_count += 1;
                // Use pre-computed lowercase
                if let Some(ref lower) = token.lowercase {
                    if positive_lexicon().contains(lower.as_str()) {
                        pos_hits += 1;
                    }
                    if negative_lexicon().contains(lower.as_str()) {
                        neg_hits += 1;
                    }
                }
            }
        }

        if word_count == 0 {
            return (0.5, 0.0);
        }

        let total = word_count as f64;
        let balance = (pos_hits as f64 - neg_hits as f64) / total;
        let sentiment_score = 0.5 + 0.5 * balance.clamp(-1.0, 1.0);
        let swing = balance.abs();
        (sentiment_score, swing)
    }

    /// Phonotactic scoring using pre-computed lowercase chars from cache.
    /// Uses a single pass over the character array to check all patterns.
    fn phonotactic_with_cache(&self, chars: &[char]) -> f64 {
        let len = chars.len();
        if len == 0 {
            return 0.0;
        }

        // Single pass to check for vowels and collect pattern matches
        let mut has_vowel = false;
        let mut has_digraph = false;
        let mut has_adjacent_vowels = false;
        let mut has_aba = false;

        for i in 0..len {
            let c0 = chars[i];

            // Check for any vowel (needed for early exit)
            if is_vowel(c0) {
                has_vowel = true;
            }

            // Check pairs (digraphs and adjacent vowels)
            if i + 1 < len {
                let c1 = chars[i + 1];

                // Digraph check via direct match instead of array lookup
                has_digraph |= matches!(
                    (c0, c1),
                    ('a', 'a')
                        | ('a', 'e')
                        | ('a', 'i')
                        | ('a', 'y')
                        | ('e', 'e')
                        | ('e', 'i')
                        | ('e', 'y')
                        | ('i', 'e')
                        | ('o', 'a')
                        | ('o', 'e')
                        | ('o', 'i')
                        | ('o', 'o')
                        | ('o', 'u')
                        | ('u', 'e')
                        | ('u', 'i')
                );

                // Adjacent vowels check
                has_adjacent_vowels |= is_vowel(c0) && is_vowel(c1);

                // ABA pattern check (needs i+2)
                if i + 2 < len {
                    let c2 = chars[i + 2];
                    has_aba |= c0 == c2 && c0 != c1;
                }
            }
        }

        // Early exit if no vowels
        if !has_vowel {
            return 0.0;
        }

        let mut score: f64 = 0.25;

        // Check sonorant and sibilant codas using last char
        let last = chars[len - 1];
        if matches!(last, 'r' | 'l' | 'm' | 'n' | 'w' | 'y' | 'h') {
            score += 0.2;
        }
        if matches!(last, 's' | 'z' | 'x' | 'c' | 'j') {
            score += 0.18;
        }

        // Check two-char sibilant codas (sh, zh)
        if len >= 2 {
            let last_two = (chars[len - 2], chars[len - 1]);
            if last_two == ('s', 'h') || last_two == ('z', 'h') {
                score += 0.18;
            }
        }

        // Apply scores from single-pass checks
        if has_digraph {
            score += 0.22;
        }
        if has_adjacent_vowels {
            score += 0.22;
        }
        if has_aba {
            score += 0.08;
        }

        score.clamp(0.0, 1.0)
    }

    fn context_score(&self, tokens: &[TokenInfo<'_>], index: usize) -> f64 {
        let mut score: f64 = 0.2;
        let before = if index > 0 {
            tokens[index - 1].text.as_ref()
        } else {
            ""
        };
        let after = if index + 1 < tokens.len() {
            tokens[index + 1].text.as_ref()
        } else {
            ""
        };
        let token_text = tokens[index].text.as_ref();
        if after.chars().filter(|&c| c == '!').count() >= 1 {
            score += 0.25;
        }
        if after.chars().filter(|&c| c == '?').count() >= 1 {
            score += 0.2;
        }
        if before.chars().filter(|&c| c == '!').count() >= 2 {
            score += 0.2;
        }
        if after.contains("!!") || after.contains("??") {
            score += 0.15;
        }
        if token_text.chars().all(|c| c.is_uppercase()) && token_text.chars().count() > 1 {
            score += 0.25;
        }
        if contains_emoji(before) || contains_emoji(after) {
            score += 0.15;
        }
        if index + 1 < tokens.len() {
            let trailing = tokens[index + 1].text.as_ref();
            if trailing.contains("!!!") || trailing.contains("??") || trailing.contains("?!") {
                score += 0.2;
            }
        }
        score.clamp(0.0, 1.0)
    }

    /// Threshold for switching to parallel analysis (word count)
    const PARALLEL_THRESHOLD: usize = 200;

    fn analyse(&self, tokens: &[TokenInfo<'_>]) -> Vec<StretchCandidate> {
        // Count word tokens to decide on parallel vs sequential
        let word_indices: Vec<usize> = tokens
            .iter()
            .enumerate()
            .filter(|(_, t)| t.is_word)
            .map(|(i, _)| i)
            .collect();

        if word_indices.len() < Self::PARALLEL_THRESHOLD {
            self.analyse_sequential(tokens, &word_indices)
        } else {
            self.analyse_parallel(tokens, &word_indices)
        }
    }

    fn analyse_sequential(
        &self,
        tokens: &[TokenInfo<'_>],
        word_indices: &[usize],
    ) -> Vec<StretchCandidate> {
        let mut candidates = Vec::with_capacity(word_indices.len() / 2);
        for &idx in word_indices {
            if let Some(candidate) = self.evaluate_candidate(tokens, idx) {
                candidates.push(candidate);
            }
        }
        candidates
    }

    fn analyse_parallel(
        &self,
        tokens: &[TokenInfo<'_>],
        word_indices: &[usize],
    ) -> Vec<StretchCandidate> {
        word_indices
            .par_iter()
            .filter_map(|&idx| self.evaluate_candidate(tokens, idx))
            .collect()
    }

    /// Evaluate a single token index and return a candidate if it qualifies.
    /// Extracted to share logic between sequential and parallel paths.
    fn evaluate_candidate(
        &self,
        tokens: &[TokenInfo<'_>],
        idx: usize,
    ) -> Option<StretchCandidate> {
        let token = &tokens[idx];
        if self.excluded(tokens, idx) {
            return None;
        }
        // Build cache lazily only for non-excluded word tokens
        let cache = self.build_cache(token);
        let features = self.compute_features(tokens, idx, &cache);
        let weights = (0.32, 0.18, 0.14, 0.22, 0.14);
        let weighted = weights.0 * features.lexical
            + weights.1 * features.pos
            + weights.2 * features.sentiment
            + weights.3 * features.phonotactic
            + weights.4 * features.context;
        let score = weighted / (weights.0 + weights.1 + weights.2 + weights.3 + weights.4);
        if score >= 0.18 {
            // Pre-compute stretch site using cached token data
            let stretch_site = self.find_stretch_site_with_cache(&cache);
            Some(StretchCandidate {
                token_index: idx,
                score: score.clamp(0.0, 1.0),
                features,
                stretch_site,
            })
        } else {
            None
        }
    }

    fn select_candidates(
        &self,
        candidates: &[StretchCandidate],
        tokens: &[TokenInfo<'_>],
        rate: f64,
        rng: &mut dyn OperationRng,
    ) -> Result<Vec<usize>, OperationError> {
        if candidates.is_empty() || rate <= 0.0 {
            return Ok(Vec::new());
        }

        // Group candidate indices by clause instead of cloning candidates
        let mut grouped: HashMap<usize, Vec<usize>> = HashMap::new();
        for (idx, candidate) in candidates.iter().enumerate() {
            grouped
                .entry(tokens[candidate.token_index].clause_index)
                .or_default()
                .push(idx);
        }

        let total_expected = (candidates.len() as f64 * rate).round() as usize;
        // Use HashSet for O(1) membership checks instead of O(n) Vec::contains
        let mut selected_set: HashSet<usize> = HashSet::with_capacity(total_expected);
        let mut selected_indices: Vec<usize> = Vec::with_capacity(total_expected);
        let mut grouped_keys: Vec<usize> = grouped.keys().copied().collect();
        grouped_keys.sort_unstable();

        for clause in grouped_keys {
            let mut clause_candidate_indices = grouped.remove(&clause).unwrap();
            // Sort by score descending, then by position
            clause_candidate_indices.sort_by(|&a, &b| {
                let score_order = candidates[b]
                    .score
                    .partial_cmp(&candidates[a].score)
                    .unwrap_or(Ordering::Equal);
                if score_order == Ordering::Equal {
                    tokens[candidates[a].token_index]
                        .start
                        .cmp(&tokens[candidates[b].token_index].start)
                } else {
                    score_order
                }
            });
            clause_candidate_indices.truncate(4);
            let clause_quota = ((clause_candidate_indices.len() as f64) * rate).round() as usize;
            let mut provisional: Vec<usize> = Vec::new();

            for &cand_idx in &clause_candidate_indices {
                let candidate = &candidates[cand_idx];
                let probability = (rate * (0.35 + 0.65 * candidate.score)).clamp(0.0, 1.0);
                if rng.random()? < probability {
                    provisional.push(cand_idx);
                }
                if provisional.len() >= clause_quota {
                    break;
                }
            }

            if provisional.len() < clause_quota {
                for &cand_idx in clause_candidate_indices.iter() {
                    // O(1) membership check via HashSet
                    if provisional.contains(&cand_idx) {
                        continue;
                    }
                    provisional.push(cand_idx);
                    if provisional.len() >= clause_quota {
                        break;
                    }
                }
            }
            // Track selected in HashSet for fast lookup during backfill
            for &idx in &provisional {
                selected_set.insert(idx);
            }
            selected_indices.extend(provisional);
        }

        if selected_indices.len() < total_expected {
            // O(1) membership check via HashSet instead of O(n) Vec::contains
            let mut remaining: Vec<usize> = (0..candidates.len())
                .filter(|idx| !selected_set.contains(idx))
                .collect();
            remaining.sort_by(|&a, &b| {
                let score_order = candidates[b]
                    .score
                    .partial_cmp(&candidates[a].score)
                    .unwrap_or(Ordering::Equal);
                if score_order == Ordering::Equal {
                    tokens[candidates[a].token_index]
                        .start
                        .cmp(&tokens[candidates[b].token_index].start)
                } else {
                    score_order
                }
            });
            selected_indices.extend(
                remaining
                    .into_iter()
                    .take(total_expected - selected_indices.len()),
            );
        }

        // Sort by token position
        selected_indices.sort_by_key(|&idx| tokens[candidates[idx].token_index].start);
        Ok(selected_indices)
    }

    /// Find stretch site using pre-computed char vectors from TokenCache
    fn find_stretch_site_with_cache(&self, cache: &TokenCache) -> Option<StretchSite> {
        let lower_chars = &cache.lowercase_chars;
        let alpha_indices = &cache.alpha_indices;

        if lower_chars.is_empty() || alpha_indices.is_empty() {
            return None;
        }

        let clusters = vowel_clusters(lower_chars, alpha_indices);

        // Check if there's a multi-vowel cluster (for coda site logic)
        let has_multi_vowel = clusters.iter().any(|(start, end)| {
            let length = end - start;
            // Don't count leading 'y' as multi-vowel
            if length >= 2 {
                !(*start == 0 && lower_chars[*start] == 'y')
            } else {
                false
            }
        });

        if let Some(site) = coda_site(lower_chars, alpha_indices, has_multi_vowel) {
            return Some(site);
        }
        if let Some(site) = cvce_site(lower_chars, alpha_indices) {
            return Some(site);
        }
        if let Some(site) = vowel_site(&clusters) {
            return Some(site);
        }
        alpha_indices.last().map(|&idx| StretchSite {
            start: idx,
            end: idx + 1,
        })
    }

    fn apply_stretch(&self, word: &str, site: &StretchSite, repeats: usize) -> String {
        if repeats == 0 {
            return word.to_string();
        }
        let chars: Vec<char> = word.chars().collect();
        let mut result = String::new();
        for (idx, ch) in chars.iter().enumerate() {
            result.push(*ch);
            if idx >= site.start && idx < site.end {
                for _ in 0..repeats {
                    result.push(*ch);
                }
            }
        }
        result
    }

    fn sample_length(
        &self,
        rng: &mut dyn OperationRng,
        intensity: f64,
        minimum: i32,
        maximum: i32,
    ) -> Result<i32, OperationError> {
        let min_extra = minimum.max(0);
        let max_extra = maximum.max(min_extra);
        if max_extra == 0 {
            return Ok(0);
        }
        if max_extra == min_extra {
            return Ok(max_extra);
        }
        let r = (1.0 + 2.0 * intensity).round().max(1.0) as usize;
        let adjusted_p = (self.base_p / (1.0 + 0.75 * intensity)).clamp(0.05, 0.95);
        let mut failures = 0i32;
        for _ in 0..r {
            let mut count = 0;
            while rng.random()? > adjusted_p {
                count += 1;
            }
            failures += count;
        }
        let extra = min_extra + failures;
        Ok(extra.clamp(min_extra, max_extra))
    }
}

/// A stretch replacement to apply, sorted by byte position for efficient single-pass assembly.
struct StretchReplacement {
    /// Byte offset in the original text where this token starts
    byte_start: usize,
    /// Byte offset in the original text where this token ends
    byte_end: usize,
    /// The stretched replacement text
    stretched: String,
}

impl TextOperation for WordStretchOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        let text = buffer.to_string();
        if text.is_empty() {
            return Ok(());
        }

        let tokens = self.tokenise(&text);
        let candidates = self.analyse(&tokens);
        let selected_indices = self.select_candidates(&candidates, &tokens, self.rate, rng)?;
        if selected_indices.is_empty() {
            return Ok(());
        }

        // Collect stretch replacements with byte positions (already sorted by token position)
        let mut replacements: Vec<StretchReplacement> = Vec::with_capacity(selected_indices.len());

        for &cand_idx in &selected_indices {
            let candidate = &candidates[cand_idx];
            let token_idx = candidate.token_index;
            let token = &tokens[token_idx];

            // Use pre-computed stretch site from candidate
            let site = match candidate.stretch_site {
                Some(site) => site,
                None => continue, // Skip if no stretch site was found during analysis
            };

            let mut intensity = (candidate.features.intensity() + 0.35 * candidate.score).min(1.5);
            // Count alpha characters
            let alpha_len = token.text.chars().filter(|c| c.is_alphabetic()).count();

            // First check: skip if word is more than double the threshold
            if self.word_length_threshold > 0 && alpha_len > self.word_length_threshold * 2 {
                continue;
            }

            // Second check: adjust intensity if word exceeds threshold
            if self.word_length_threshold > 0 && alpha_len > self.word_length_threshold {
                let excess = (alpha_len - self.word_length_threshold) as f64;
                intensity /= 1.0 + 0.35 * excess;
                if candidate.score < 0.35 && excess >= 2.0 {
                    continue;
                }
            }

            intensity = intensity.max(0.05);
            let repeats =
                self.sample_length(rng, intensity, self.extension_min, self.extension_max)?;
            if repeats <= 0 {
                continue;
            }

            let stretched = self.apply_stretch(&token.text, &site, repeats as usize);
            let byte_end = token.start + token.text.len();
            replacements.push(StretchReplacement {
                byte_start: token.start,
                byte_end,
                stretched,
            });
        }

        if replacements.is_empty() {
            return Ok(());
        }

        // Ensure replacements are sorted by byte position for correct reconstruction.
        // While selected_indices is sorted by token position, some candidates may be
        // skipped during iteration, and we need ascending byte order for the cursor logic.
        replacements.sort_by_key(|r| r.byte_start);

        // Build result string in a single pass using byte positions
        // Estimate capacity: original length + extra chars from stretching
        let extra_chars: usize = replacements
            .iter()
            .map(|r| r.stretched.len().saturating_sub(r.byte_end - r.byte_start))
            .sum();
        let mut result = String::with_capacity(text.len() + extra_chars);

        let mut cursor = 0usize;
        for replacement in &replacements {
            // Copy unchanged text before this replacement
            if cursor < replacement.byte_start {
                result.push_str(&text[cursor..replacement.byte_start]);
            }
            // Insert stretched text
            result.push_str(&replacement.stretched);
            cursor = replacement.byte_end;
        }
        // Copy remaining text after last replacement
        if cursor < text.len() {
            result.push_str(&text[cursor..]);
        }

        *buffer = buffer.rebuild_with_patterns(result);
        buffer.reindex_if_needed();
        Ok(())
    }
}

fn contains_emoji(text: &str) -> bool {
    text.chars()
        .any(|c| (0x1F300..=0x1FAFF).contains(&(c as u32)))
}

fn vowel_clusters(lower_chars: &[char], alpha_indices: &[usize]) -> Vec<(usize, usize)> {
    let vowels = ['a', 'e', 'i', 'o', 'u', 'y'];
    let mut clusters = Vec::new();
    let mut start: Option<usize> = None;
    let mut prev_idx: Option<usize> = None;
    for idx in alpha_indices {
        let ch = lower_chars[*idx];
        if vowels.contains(&ch) {
            if start.is_none() {
                start = Some(*idx);
            } else if let Some(prev) = prev_idx {
                if *idx != prev + 1 {
                    clusters.push((start.unwrap(), prev + 1));
                    start = Some(*idx);
                }
            }
        } else if let Some(st) = start.take() {
            clusters.push((st, *idx));
        }
        prev_idx = Some(*idx);
    }
    if let (Some(st), Some(prev)) = (start, prev_idx) {
        clusters.push((st, prev + 1));
    }
    clusters
}

fn coda_site(
    lower_chars: &[char],
    alpha_indices: &[usize],
    has_multi_vowel: bool,
) -> Option<StretchSite> {
    if alpha_indices.is_empty() {
        return None;
    }
    let last_idx = *alpha_indices.last().unwrap();
    let last_char = lower_chars[last_idx];
    let prev_char = if alpha_indices.len() >= 2 {
        Some(lower_chars[alpha_indices[alpha_indices.len() - 2]])
    } else {
        None
    };
    if let Some(prev) = prev_char {
        // Only add coda site if there's no multi-vowel cluster
        if !has_multi_vowel {
            if (last_char == 's' || last_char == 'z') && is_vowel(prev) {
                return Some(StretchSite {
                    start: last_idx,
                    end: last_idx + 1,
                });
            }
            let sonorants = ['r', 'l', 'm', 'n', 'w', 'y', 'h'];
            if sonorants.contains(&last_char) && is_vowel(prev) {
                return Some(StretchSite {
                    start: last_idx,
                    end: last_idx + 1,
                });
            }
        }
    } else if !contains_vowel(lower_chars) {
        return Some(StretchSite {
            start: last_idx,
            end: last_idx + 1,
        });
    }
    None
}

fn cvce_site(lower_chars: &[char], alpha_indices: &[usize]) -> Option<StretchSite> {
    if lower_chars.last().copied() != Some('e') {
        return None;
    }
    if alpha_indices.len() < 3 {
        return None;
    }
    let v_idx = alpha_indices[alpha_indices.len() - 3];
    let c_idx = alpha_indices[alpha_indices.len() - 2];
    let v_char = lower_chars[v_idx];
    let c_char = lower_chars[c_idx];
    if is_vowel(v_char) && !is_vowel(c_char) {
        return Some(StretchSite {
            start: v_idx,
            end: v_idx + 1,
        });
    }
    None
}

fn vowel_site(clusters: &[(usize, usize)]) -> Option<StretchSite> {
    clusters
        .iter()
        .max_by(|a, b| {
            let len_a = a.1 - a.0;
            let len_b = b.1 - b.0;
            match len_a.cmp(&len_b) {
                Ordering::Equal => a.0.cmp(&b.0),
                other => other,
            }
        })
        .map(|&(start, end)| StretchSite { start, end })
}

fn is_vowel(ch: char) -> bool {
    matches!(ch, 'a' | 'e' | 'i' | 'o' | 'u' | 'y')
}

fn contains_vowel(chars: &[char]) -> bool {
    chars.iter().any(|&c| is_vowel(c))
}

/// Python wrapper for the word stretching operation.
#[pyfunction(name = "stretch_word", signature = (text, rate, extension_min, extension_max, word_length_threshold, base_p, seed=None))]
pub fn stretch_word(
    text: &str,
    rate: f64,
    extension_min: i32,
    extension_max: i32,
    word_length_threshold: usize,
    base_p: f64,
    seed: Option<u64>,
) -> PyResult<String> {
    let op = WordStretchOp {
        rate,
        extension_min,
        extension_max,
        word_length_threshold,
        base_p,
    };
    crate::apply_operation(text, op, seed).map_err(crate::operations::OperationError::into_pyerr)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::DeterministicRng;
    use crate::text_buffer::TextBuffer;

    fn default_op() -> WordStretchOp {
        WordStretchOp {
            rate: 0.3,
            extension_min: 2,
            extension_max: 5,
            word_length_threshold: 6,
            base_p: 0.45,
        }
    }

    fn cache_from_text(text: &str) -> TokenCache {
        let lowercase = text.to_lowercase();
        let lowercase_chars: Vec<char> = lowercase.chars().collect();
        let alpha_indices: Vec<usize> = text
            .chars()
            .enumerate()
            .filter_map(|(idx, ch)| if ch.is_alphabetic() { Some(idx) } else { None })
            .collect();
        TokenCache {
            lowercase,
            lowercase_chars,
            alpha_indices,
        }
    }

    // --- Helper function tests ---

    #[test]
    fn is_vowel_identifies_vowels() {
        assert!(is_vowel('a'));
        assert!(is_vowel('e'));
        assert!(is_vowel('i'));
        assert!(is_vowel('o'));
        assert!(is_vowel('u'));
        assert!(is_vowel('y'));
        assert!(!is_vowel('b'));
        assert!(!is_vowel('x'));
        assert!(!is_vowel('z'));
    }

    #[test]
    fn contains_vowel_detects_vowels() {
        assert!(contains_vowel(&['h', 'e', 'l', 'l', 'o']));
        assert!(contains_vowel(&['a']));
        assert!(!contains_vowel(&['h', 'm', 'm']));
        assert!(!contains_vowel(&['b', 'r', 'r']));
    }

    #[test]
    fn contains_emoji_detects_emoji_range() {
        assert!(contains_emoji("hello 🎉"));
        assert!(contains_emoji("🔥"));
        assert!(!contains_emoji("hello world"));
        assert!(!contains_emoji(""));
    }

    // --- Tokenization tests ---

    #[test]
    fn tokenise_splits_words_and_punctuation() {
        let op = default_op();
        let tokens = op.tokenise("Hello, world!");
        assert_eq!(tokens.len(), 4);
        assert_eq!(tokens[0].text, "Hello");
        assert!(tokens[0].is_word);
        assert_eq!(tokens[1].text, ", ");
        assert!(!tokens[1].is_word);
        assert_eq!(tokens[2].text, "world");
        assert!(tokens[2].is_word);
        assert_eq!(tokens[3].text, "!");
        assert!(!tokens[3].is_word);
    }

    #[test]
    fn tokenise_tracks_clause_indices() {
        let op = default_op();
        let tokens = op.tokenise("First. Second! Third?");
        // Clause punctuation should increment clause_index
        let clause_indices: Vec<usize> = tokens.iter().map(|t| t.clause_index).collect();
        assert!(clause_indices.contains(&0));
        assert!(clause_indices.contains(&1));
        assert!(clause_indices.contains(&2));
    }

    #[test]
    fn tokenise_preserves_start_positions() {
        let op = default_op();
        let tokens = op.tokenise("ab cd");
        assert_eq!(tokens[0].start, 0);
        assert_eq!(tokens[1].start, 2); // space
        assert_eq!(tokens[2].start, 3);
    }

    // --- Exclusion tests ---

    #[test]
    fn excluded_rejects_short_words() {
        let op = default_op();
        let tokens = op.tokenise("a is");
        assert!(op.excluded(&tokens, 0)); // "a" - too short
    }

    #[test]
    fn excluded_rejects_words_with_digits() {
        let op = default_op();
        let tokens = op.tokenise("hello123 world");
        assert!(op.excluded(&tokens, 0)); // "hello123" has digits
        assert!(!op.excluded(&tokens, 2)); // "world" is valid
    }

    #[test]
    fn excluded_rejects_urls() {
        let op = default_op();
        let tokens = op.tokenise("visit https://example.com today");
        // URL fragment detection
        for (i, token) in tokens.iter().enumerate() {
            if token.text.contains("http") || token.text.contains("//") {
                assert!(op.excluded(&tokens, i));
            }
        }
    }

    #[test]
    fn excluded_rejects_social_tags() {
        let op = default_op();
        let tokens = op.tokenise("follow @user and #hashtag");
        for (i, token) in tokens.iter().enumerate() {
            if token.text.contains('@') || token.text.contains('#') {
                assert!(op.excluded(&tokens, i));
            }
        }
    }

    #[test]
    fn excluded_allows_sentence_initial_caps() {
        let op = default_op();
        let tokens = op.tokenise("Hello world");
        assert!(!op.excluded(&tokens, 0)); // "Hello" at sentence start is OK
    }

    #[test]
    fn excluded_rejects_mid_sentence_proper_nouns() {
        let op = default_op();
        let tokens = op.tokenise("visit Paris today");
        // "Paris" is Title case mid-sentence -> excluded
        let paris_idx = tokens.iter().position(|t| t.text == "Paris").unwrap();
        assert!(op.excluded(&tokens, paris_idx));
    }

    // --- Vowel cluster tests ---

    #[test]
    fn vowel_clusters_finds_single_vowel() {
        let chars: Vec<char> = "cat".chars().collect();
        let indices: Vec<usize> = (0..chars.len()).collect();
        let clusters = vowel_clusters(&chars, &indices);
        assert_eq!(clusters, vec![(1, 2)]); // 'a' at index 1
    }

    #[test]
    fn vowel_clusters_finds_digraphs() {
        let chars: Vec<char> = "cool".chars().collect();
        let indices: Vec<usize> = (0..chars.len()).collect();
        let clusters = vowel_clusters(&chars, &indices);
        assert_eq!(clusters, vec![(1, 3)]); // "oo" spans indices 1-2
    }

    #[test]
    fn vowel_clusters_finds_multiple_clusters() {
        let chars: Vec<char> = "banana".chars().collect();
        let indices: Vec<usize> = (0..chars.len()).collect();
        let clusters = vowel_clusters(&chars, &indices);
        assert_eq!(clusters.len(), 3); // three separate 'a's
    }

    // --- Stretch site tests ---

    #[test]
    fn find_stretch_site_cvce_pattern() {
        let op = default_op();
        let cache = cache_from_text("cute");
        let site = op.find_stretch_site_with_cache(&cache).unwrap();
        // CVCe pattern: stretch the vowel before consonant-e
        assert_eq!(site.start, 1); // 'u'
        assert_eq!(site.end, 2);
    }

    #[test]
    fn find_stretch_site_vowel_digraph() {
        let op = default_op();
        let cache = cache_from_text("cool");
        let site = op.find_stretch_site_with_cache(&cache).unwrap();
        // "oo" digraph
        assert_eq!(site.start, 1);
        assert_eq!(site.end, 3);
    }

    #[test]
    fn find_stretch_site_sonorant_coda() {
        let op = default_op();
        let cache = cache_from_text("yes");
        let site = op.find_stretch_site_with_cache(&cache).unwrap();
        // "yes" ends in sibilant 's' after vowel -> coda site
        assert_eq!(site.start, 2); // 's'
        assert_eq!(site.end, 3);
    }

    #[test]
    fn find_stretch_site_no_vowels() {
        let op = default_op();
        let cache = cache_from_text("hmm");
        let site = op.find_stretch_site_with_cache(&cache).unwrap();
        // No vowels -> stretch last char
        assert_eq!(site.start, 2);
        assert_eq!(site.end, 3);
    }

    #[test]
    fn find_stretch_site_empty_returns_none() {
        let op = default_op();
        let cache = cache_from_text("");
        assert!(op.find_stretch_site_with_cache(&cache).is_none());
    }

    // --- Stretch application tests ---

    #[test]
    fn apply_stretch_repeats_single_char() {
        let op = default_op();
        let site = StretchSite { start: 1, end: 2 };
        let result = op.apply_stretch("so", &site, 3);
        assert_eq!(result, "soooo"); // original 'o' + 3 repeats
    }

    #[test]
    fn apply_stretch_repeats_range() {
        let op = default_op();
        let site = StretchSite { start: 1, end: 3 }; // "oo" in "cool"
        let result = op.apply_stretch("cool", &site, 2);
        assert_eq!(result, "coooool"); // each char in range repeated
    }

    #[test]
    fn apply_stretch_zero_repeats_unchanged() {
        let op = default_op();
        let site = StretchSite { start: 0, end: 1 };
        let result = op.apply_stretch("hello", &site, 0);
        assert_eq!(result, "hello");
    }

    // --- Scoring tests ---

    #[test]
    fn pos_score_interjections_high() {
        let op = default_op();
        let score = op.pos_score("wow", "wow");
        assert!(score > 0.9); // interjections get 0.95
    }

    #[test]
    fn pos_score_adverbs_moderate() {
        let op = default_op();
        let score = op.pos_score("really", "really");
        assert!(score > 0.5); // ends with "ly" -> 0.55
    }

    #[test]
    fn pos_score_all_caps_boosted() {
        let op = default_op();
        let score = op.pos_score("WOW", "wow");
        assert!(score > 0.6); // all caps -> 0.65
    }

    #[test]
    fn phonotactic_vowel_words_score_above_zero() {
        let op = default_op();
        let hello_cache = cache_from_text("hello");
        let cool_cache = cache_from_text("cool");
        assert!(op.phonotactic_with_cache(&hello_cache.lowercase_chars) > 0.0);
        assert!(op.phonotactic_with_cache(&cool_cache.lowercase_chars) > 0.0);
    }

    #[test]
    fn phonotactic_no_vowels_returns_zero() {
        let op = default_op();
        let hmm_cache = cache_from_text("hmm");
        let brr_cache = cache_from_text("brr");
        assert_eq!(op.phonotactic_with_cache(&hmm_cache.lowercase_chars), 0.0);
        assert_eq!(op.phonotactic_with_cache(&brr_cache.lowercase_chars), 0.0);
    }

    #[test]
    fn phonotactic_sonorant_coda_boosted() {
        let op = default_op();
        let yes_cache = cache_from_text("yes");
        let cat_cache = cache_from_text("cat");
        let score_yes = op.phonotactic_with_cache(&yes_cache.lowercase_chars);
        let score_cat = op.phonotactic_with_cache(&cat_cache.lowercase_chars);
        // "yes" ends in 's' (sibilant) after vowel -> boosted
        assert!(score_yes > score_cat);
    }

    // --- Full operation tests ---

    #[test]
    fn hokey_stretches_high_scoring_words() {
        let op = WordStretchOp {
            rate: 1.0,
            extension_min: 2,
            extension_max: 5,
            word_length_threshold: 10,
            base_p: 0.45,
        };
        let mut buffer = TextBuffer::from_owned("wow so cool".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        op.apply(&mut buffer, &mut rng).expect("hokey succeeds");
        let result = buffer.to_string();
        assert_ne!(result, "wow so cool");
        // At least one word should be stretched
        assert!(result.len() > "wow so cool".len());
    }

    #[test]
    fn hokey_respects_zero_rate() {
        let op = WordStretchOp {
            rate: 0.0,
            extension_min: 2,
            extension_max: 5,
            word_length_threshold: 6,
            base_p: 0.45,
        };
        let original = "wow so cool";
        let mut buffer = TextBuffer::from_owned(original.to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        op.apply(&mut buffer, &mut rng).expect("hokey succeeds");
        assert_eq!(buffer.to_string(), original);
    }

    #[test]
    fn hokey_handles_empty_input() {
        let op = default_op();
        let mut buffer = TextBuffer::from_owned(String::new(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        op.apply(&mut buffer, &mut rng).expect("hokey succeeds");
        assert_eq!(buffer.to_string(), "");
    }

    #[test]
    fn hokey_is_deterministic() {
        let op = WordStretchOp {
            rate: 0.5,
            extension_min: 2,
            extension_max: 5,
            word_length_threshold: 6,
            base_p: 0.45,
        };
        let text = "wow this is so cool and fun";

        let mut buffer1 = TextBuffer::from_owned(text.to_string(), &[], &[]);
        let mut rng1 = DeterministicRng::new(123);
        op.apply(&mut buffer1, &mut rng1).expect("hokey succeeds");

        let mut buffer2 = TextBuffer::from_owned(text.to_string(), &[], &[]);
        let mut rng2 = DeterministicRng::new(123);
        op.apply(&mut buffer2, &mut rng2).expect("hokey succeeds");

        assert_eq!(buffer1.to_string(), buffer2.to_string());
    }

    #[test]
    fn hokey_respects_word_length_threshold() {
        let op = WordStretchOp {
            rate: 1.0,
            extension_min: 2,
            extension_max: 5,
            word_length_threshold: 4, // very short threshold
            base_p: 0.45,
        };
        let mut buffer =
            TextBuffer::from_owned("supercalifragilisticexpialidocious".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        op.apply(&mut buffer, &mut rng).expect("hokey succeeds");
        // Very long word should be unchanged (exceeds 2x threshold)
        assert_eq!(buffer.to_string(), "supercalifragilisticexpialidocious");
    }

    #[test]
    fn hokey_handles_punctuation_only() {
        let op = default_op();
        let mut buffer = TextBuffer::from_owned("!!! ???".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        op.apply(&mut buffer, &mut rng).expect("hokey succeeds");
        assert_eq!(buffer.to_string(), "!!! ???");
    }

    #[test]
    fn hokey_handles_utf8_correctly() {
        let op = WordStretchOp {
            rate: 1.0,
            extension_min: 2,
            extension_max: 3,
            word_length_threshold: 10,
            base_p: 0.45,
        };
        let mut buffer = TextBuffer::from_owned("café cool".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        op.apply(&mut buffer, &mut rng).expect("hokey succeeds");
        let result = buffer.to_string();
        // Should still be valid UTF-8 and longer
        assert!(result.len() >= "café cool".len());
        assert!(result.is_char_boundary(0));
    }
}

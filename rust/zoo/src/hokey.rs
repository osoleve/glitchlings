use pyo3::prelude::*;
use pyo3::types::PyAny;
use pyo3::Bound;
use regex::Regex;
use serde::Deserialize;
use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

use crate::glitch_ops::{GlitchOp, GlitchOpError, GlitchRng};
use crate::text_buffer::TextBuffer;

static TOKEN_REGEX: OnceLock<Regex> = OnceLock::new();

fn token_regex() -> &'static Regex {
    TOKEN_REGEX.get_or_init(|| Regex::new(r"\w+|\W+").unwrap())
}

const CLAUSE_PUNCT: [char; 4] = ['.', '?', '!', ';'];

const HOKEY_ASSETS: &str = include_str!("../../../src/glitchlings/data/hokey_assets.json");

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
        let raw: RawHokeyAssets = serde_json::from_str(HOKEY_ASSETS)
            .expect("failed to parse Hokey asset payload");
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

#[derive(Clone)]
struct TokenInfo {
    text: String,
    start: usize,
    is_word: bool,
    clause_index: usize,
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
}

#[derive(Clone, Copy)]
struct StretchSite {
    start: usize,
    end: usize,
}

#[derive(Debug, Clone)]
pub struct HokeyOp {
    pub rate: f64,
    pub extension_min: i32,
    pub extension_max: i32,
    pub word_length_threshold: usize,
    pub base_p: f64,
}

impl HokeyOp {
    fn tokenise(&self, text: &str) -> Vec<TokenInfo> {
        let regex = token_regex();
        let mut tokens = Vec::new();
        let mut clause_index = 0usize;
        for mat in regex.find_iter(text) {
            let token_text = mat.as_str();
            let is_word = token_text.chars().any(|c| c.is_alphabetic())
                && token_text.trim().chars().all(|c| c.is_alphanumeric());
            tokens.push(TokenInfo {
                text: token_text.to_string(),
                start: mat.start(),
                is_word,
                clause_index,
            });
            if token_text.chars().any(|c| CLAUSE_PUNCT.contains(&c)) {
                clause_index += 1;
            }
        }
        tokens
    }

    fn excluded(&self, tokens: &[TokenInfo], index: usize) -> bool {
        let token = &tokens[index];
        let text = token.text.as_str();
        let alpha_count = text.chars().filter(|c| c.is_alphabetic()).count();
        if alpha_count < 2 {
            return true;
        }
        if text.chars().any(|c| c.is_ascii_digit()) {
            return true;
        }
        let lowered = text.to_lowercase();
        if lowered.contains("http") || lowered.contains("www") || lowered.contains("//") {
            return true;
        }
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
        if text
            .chars()
            .next()
            .map(|c| c.is_uppercase())
            .unwrap_or(false)
            && text.chars().skip(1).all(|c| c.is_lowercase())
        {
            let mut at_clause_start = index == 0;
            if !at_clause_start {
                for prior in tokens[..index].iter().rev() {
                    let trimmed = prior.text.trim();
                    if trimmed.is_empty() {
                        continue;
                    }
                    if trimmed
                        .chars()
                        .last()
                        .map(|ch| CLAUSE_PUNCT.contains(&ch))
                        .unwrap_or(false)
                    {
                        at_clause_start = true;
                    }
                    break;
                }
            }
            if !at_clause_start {
                return true;
            }
        }
        false
    }

    fn compute_features(&self, tokens: &[TokenInfo], index: usize) -> StretchFeatures {
        let token = &tokens[index];
        let normalised = token.text.to_lowercase();
        let lexical = *lexical_prior().get(normalised.as_str()).unwrap_or(&0.12);
        let pos = self.pos_score(&token.text, normalised.as_str());
        let (sentiment, swing) = self.sentiment(tokens, index);
        let phonotactic = self.phonotactic(normalised.as_str());
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

    fn sentiment(&self, tokens: &[TokenInfo], index: usize) -> (f64, f64) {
        let mut window = Vec::new();
        let start = index.saturating_sub(2);
        let end = (index + 3).min(tokens.len());
        for token in &tokens[start..end] {
            if token.is_word {
                window.push(token.text.to_lowercase());
            }
        }
        if window.is_empty() {
            return (0.5, 0.0);
        }
        let pos_hits = window
            .iter()
            .filter(|word| positive_lexicon().contains(word.as_str()))
            .count() as f64;
        let neg_hits = window
            .iter()
            .filter(|word| negative_lexicon().contains(word.as_str()))
            .count() as f64;
        let total = window.len() as f64;
        let balance = if total > 0.0 {
            (pos_hits - neg_hits) / total
        } else {
            0.0
        };
        let sentiment_score = 0.5 + 0.5 * balance.clamp(-1.0, 1.0);
        let swing = balance.abs();
        (sentiment_score, swing)
    }

    fn phonotactic(&self, normalised: &str) -> f64 {
        let vowels = ["a", "e", "i", "o", "u", "y"];
        if !normalised
            .chars()
            .any(|c| vowels.contains(&c.to_string().as_str()))
        {
            return 0.0;
        }
        let mut score: f64 = 0.25;
        let sonorant_codas = ["r", "l", "m", "n", "w", "y", "h"];
        if sonorant_codas
            .iter()
            .any(|ending| normalised.ends_with(ending))
        {
            score += 0.2;
        }
        let sibilant_codas = ["s", "z", "x", "c", "j", "sh", "zh"];
        if sibilant_codas
            .iter()
            .any(|ending| normalised.ends_with(ending))
        {
            score += 0.18;
        }
        let digraphs = [
            "aa", "ae", "ai", "ay", "ee", "ei", "ey", "ie", "oa", "oe", "oi", "oo", "ou", "ue",
            "ui",
        ];
        if digraphs.iter().any(|d| normalised.contains(d)) {
            score += 0.22;
        }
        let chars: Vec<char> = normalised.chars().collect();
        if chars
            .windows(2)
            .any(|pair| is_vowel(pair[0]) && is_vowel(pair[1]))
        {
            score += 0.22;
        }
        if chars
            .windows(3)
            .any(|triple| triple[0] == triple[2] && triple[0] != triple[1])
        {
            score += 0.08;
        }
        score.clamp(0.0, 1.0)
    }

    fn context_score(&self, tokens: &[TokenInfo], index: usize) -> f64 {
        let mut score: f64 = 0.2;
        let before = if index > 0 {
            tokens[index - 1].text.as_str()
        } else {
            ""
        };
        let after = if index + 1 < tokens.len() {
            tokens[index + 1].text.as_str()
        } else {
            ""
        };
        let token_text = tokens[index].text.as_str();
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
            let trailing = tokens[index + 1].text.as_str();
            if trailing.contains("!!!") || trailing.contains("??") || trailing.contains("?!") {
                score += 0.2;
            }
        }
        score.clamp(0.0, 1.0)
    }

    fn analyse(&self, tokens: &[TokenInfo]) -> Vec<StretchCandidate> {
        let mut candidates = Vec::new();
        for (idx, token) in tokens.iter().enumerate() {
            if !token.is_word {
                continue;
            }
            if self.excluded(tokens, idx) {
                continue;
            }
            let features = self.compute_features(tokens, idx);
            let weights = (0.32, 0.18, 0.14, 0.22, 0.14);
            let weighted = weights.0 * features.lexical
                + weights.1 * features.pos
                + weights.2 * features.sentiment
                + weights.3 * features.phonotactic
                + weights.4 * features.context;
            let score = weighted / (weights.0 + weights.1 + weights.2 + weights.3 + weights.4);
            if score >= 0.18 {
                candidates.push(StretchCandidate {
                    token_index: idx,
                    score: score.clamp(0.0, 1.0),
                    features,
                });
            }
        }
        candidates
    }

    fn select_candidates(
        &self,
        candidates: &[StretchCandidate],
        tokens: &[TokenInfo],
        rate: f64,
        rng: &mut dyn GlitchRng,
    ) -> Result<Vec<StretchCandidate>, GlitchOpError> {
        if candidates.is_empty() || rate <= 0.0 {
            return Ok(Vec::new());
        }
        let mut grouped: HashMap<usize, Vec<StretchCandidate>> = HashMap::new();
        for candidate in candidates {
            grouped
                .entry(tokens[candidate.token_index].clause_index)
                .or_default()
                .push(candidate.clone());
        }
        let mut selected = Vec::new();
        let total_expected = (candidates.len() as f64 * rate).round() as usize;
        let mut grouped_keys: Vec<usize> = grouped.keys().copied().collect();
        grouped_keys.sort_unstable();

        for clause in grouped_keys {
            let mut clause_candidates = grouped.remove(&clause).unwrap();
            clause_candidates.sort_by(|a, b| {
                let score_order = b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal);
                if score_order == Ordering::Equal {
                    tokens[a.token_index]
                        .start
                        .cmp(&tokens[b.token_index].start)
                } else {
                    score_order
                }
            });
            clause_candidates.truncate(4);
            let clause_quota = ((clause_candidates.len() as f64) * rate).round() as usize;
            let mut provisional = Vec::new();
            for candidate in &clause_candidates {
                let probability = (rate * (0.35 + 0.65 * candidate.score)).clamp(0.0, 1.0);
                if rng.random()? < probability {
                    provisional.push(candidate.clone());
                }
                if provisional.len() >= clause_quota {
                    break;
                }
            }
            if provisional.len() < clause_quota {
                for candidate in clause_candidates.iter() {
                    if provisional
                        .iter()
                        .any(|c| c.token_index == candidate.token_index)
                    {
                        continue;
                    }
                    provisional.push(candidate.clone());
                    if provisional.len() >= clause_quota {
                        break;
                    }
                }
            }
            selected.extend(provisional);
        }

        if selected.len() < total_expected {
            let mut remaining: Vec<_> = candidates
                .iter()
                .filter(|cand| !selected.iter().any(|s| s.token_index == cand.token_index))
                .cloned()
                .collect();
            remaining.sort_by(|a, b| {
                let score_order = b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal);
                if score_order == Ordering::Equal {
                    tokens[a.token_index]
                        .start
                        .cmp(&tokens[b.token_index].start)
                } else {
                    score_order
                }
            });
            selected.extend(remaining.into_iter().take(total_expected - selected.len()));
        }

        selected.sort_by_key(|cand| tokens[cand.token_index].start);
        Ok(selected)
    }

    fn find_stretch_site(&self, word: &str) -> Option<StretchSite> {
        let chars: Vec<char> = word.chars().collect();
        if chars.is_empty() {
            return None;
        }
        let alpha_indices: Vec<usize> = chars
            .iter()
            .enumerate()
            .filter_map(|(idx, ch)| if ch.is_alphabetic() { Some(idx) } else { None })
            .collect();
        if alpha_indices.is_empty() {
            return None;
        }
        let lower: String = word.to_lowercase();
        let lower_chars: Vec<char> = lower.chars().collect();
        let clusters = vowel_clusters(&lower_chars, &alpha_indices);

        if let Some(site) = coda_site(&lower_chars, &alpha_indices) {
            return Some(site);
        }
        if let Some(site) = cvce_site(&lower_chars, &alpha_indices) {
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
        rng: &mut dyn GlitchRng,
        intensity: f64,
        minimum: i32,
        maximum: i32,
    ) -> Result<i32, GlitchOpError> {
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

impl GlitchOp for HokeyOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let text = buffer.to_string();
        if text.is_empty() {
            return Ok(());
        }

        let tokens = self.tokenise(&text);
        let candidates = self.analyse(&tokens);
        let selected = self.select_candidates(&candidates, &tokens, self.rate, rng)?;
        if selected.is_empty() {
            return Ok(());
        }

        let mut token_strings: Vec<String> = tokens.iter().map(|t| t.text.clone()).collect();

        for candidate in selected {
            let token_idx = candidate.token_index;
            let original = token_strings[token_idx].clone();
            let site = match self.find_stretch_site(&original) {
                Some(site) => site,
                None => continue,
            };
            let mut intensity = (candidate.features.intensity() + 0.35 * candidate.score).min(1.5);
            let alpha_len = original.chars().filter(|c| c.is_alphabetic()).count();
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
            let stretched = self.apply_stretch(&original, &site, repeats as usize);
            token_strings[token_idx] = stretched;
        }

        let result = token_strings.join("");
        *buffer = TextBuffer::from_owned(result);
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

fn coda_site(lower_chars: &[char], alpha_indices: &[usize]) -> Option<StretchSite> {
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

/// Python wrapper for the Hokey operation.
#[pyfunction]
pub fn hokey(
    text: &str,
    rate: f64,
    extension_min: i32,
    extension_max: i32,
    word_length_threshold: usize,
    base_p: f64,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    use crate::PythonRngAdapter;

    let op = HokeyOp {
        rate,
        extension_min,
        extension_max,
        word_length_threshold,
        base_p,
    };

    let mut buffer = TextBuffer::from_str(text);
    let mut adapter = PythonRngAdapter::new(rng.clone());

    op.apply(&mut buffer, &mut adapter)
        .map_err(|err| err.into_pyerr())?;

    Ok(buffer.to_string())
}

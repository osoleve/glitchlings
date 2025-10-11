use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::PyErr;
use regex::{Captures, Regex};
use std::collections::HashMap;

use crate::resources::{
    confusion_table, is_whitespace_only, split_affixes, MULTIPLE_WHITESPACE,
    SPACE_BEFORE_PUNCTUATION,
};
use crate::rng::{PyRng, PyRngError};
use crate::text_buffer::{SegmentKind, TextBuffer, TextBufferError};

/// Errors produced while applying a [`GlitchOp`].
#[derive(Debug)]
pub enum GlitchOpError {
    Buffer(TextBufferError),
    NoRedactableWords,
    ExcessiveRedaction { requested: usize, available: usize },
    Rng(PyRngError),
    Python(PyErr),
    Regex(String),
}

impl GlitchOpError {
    pub fn into_pyerr(self) -> PyErr {
        match self {
            GlitchOpError::Buffer(err) => PyValueError::new_err(err.to_string()),
            GlitchOpError::NoRedactableWords => PyValueError::new_err(
                "Cannot redact words because the input text contains no redactable words.",
            ),
            GlitchOpError::ExcessiveRedaction { .. } => {
                PyValueError::new_err("Cannot redact more words than available in text")
            }
            GlitchOpError::Rng(err) => PyValueError::new_err(err.to_string()),
            GlitchOpError::Python(err) => err,
            GlitchOpError::Regex(message) => PyRuntimeError::new_err(message),
        }
    }

    pub fn from_pyerr(err: PyErr) -> Self {
        GlitchOpError::Python(err)
    }
}

impl From<TextBufferError> for GlitchOpError {
    fn from(value: TextBufferError) -> Self {
        GlitchOpError::Buffer(value)
    }
}

impl From<PyRngError> for GlitchOpError {
    fn from(value: PyRngError) -> Self {
        GlitchOpError::Rng(value)
    }
}

/// RNG abstraction used by glitchling operations so they can work with both the
/// Rust [`PyRng`] and Python's ``random.Random`` objects.
pub trait GlitchRng {
    fn random(&mut self) -> Result<f64, GlitchOpError>;
    fn rand_index(&mut self, upper: usize) -> Result<usize, GlitchOpError>;
    #[allow(dead_code)]
    fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, GlitchOpError>;
}

impl GlitchRng for PyRng {
    fn random(&mut self) -> Result<f64, GlitchOpError> {
        Ok(PyRng::random(self))
    }

    fn rand_index(&mut self, upper: usize) -> Result<usize, GlitchOpError> {
        let value = PyRng::randrange(self, 0, Some(upper as i64), 1)?;
        Ok(value as usize)
    }

    #[allow(dead_code)]
    fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, GlitchOpError> {
        PyRng::sample_indices(self, population, k).map_err(GlitchOpError::from)
    }
}

fn core_length_for_weight(core: &str, original: &str) -> usize {
    let mut length = if !core.is_empty() {
        core.chars().count()
    } else {
        original.chars().count()
    };
    if length == 0 {
        let trimmed = original.trim();
        length = if trimmed.is_empty() {
            original.chars().count()
        } else {
            trimmed.chars().count()
        };
    }
    if length == 0 {
        length = 1;
    }
    length
}

fn inverse_length_weight(core: &str, original: &str) -> f64 {
    1.0 / (core_length_for_weight(core, original) as f64)
}

fn direct_length_weight(core: &str, original: &str) -> f64 {
    core_length_for_weight(core, original) as f64
}

#[derive(Debug)]
struct ReduplicateCandidate {
    index: usize,
    prefix: String,
    core: String,
    suffix: String,
    weight: f64,
}

#[derive(Debug)]
struct DeleteCandidate {
    index: usize,
    prefix: String,
    suffix: String,
    weight: f64,
}

#[derive(Debug)]
struct RedactCandidate {
    index: usize,
    prefix: String,
    suffix: String,
    repeat: usize,
    weight: f64,
}

fn weighted_sample_without_replacement(
    rng: &mut dyn GlitchRng,
    items: &[(usize, f64)],
    k: usize,
) -> Result<Vec<usize>, GlitchOpError> {
    if k == 0 || items.is_empty() {
        return Ok(Vec::new());
    }

    let mut pool: Vec<(usize, f64)> = items
        .iter()
        .map(|(index, weight)| (*index, *weight))
        .collect();

    if k > pool.len() {
        return Err(GlitchOpError::ExcessiveRedaction {
            requested: k,
            available: pool.len(),
        });
    }

    let mut selections: Vec<usize> = Vec::with_capacity(k);
    for _ in 0..k {
        if pool.is_empty() {
            break;
        }
        let total_weight: f64 = pool.iter().map(|(_, weight)| weight.max(0.0)).sum();
        let chosen_index = if total_weight <= f64::EPSILON {
            rng.rand_index(pool.len())?
        } else {
            let threshold = rng.random()? * total_weight;
            let mut cumulative = 0.0;
            let mut selected = pool.len() - 1;
            for (idx, (_, weight)) in pool.iter().enumerate() {
                cumulative += weight.max(0.0);
                if cumulative >= threshold {
                    selected = idx;
                    break;
                }
            }
            selected
        };
        let (value, _) = pool.remove(chosen_index);
        selections.push(value);
    }

    Ok(selections)
}

/// Trait implemented by each glitchling mutation so they can be sequenced by
/// the pipeline.
pub trait GlitchOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError>;
}

/// Repeats words to simulate stuttered speech.
#[derive(Debug, Clone, Copy)]
pub struct ReduplicateWordsOp {
    pub reduplication_rate: f64,
    pub unweighted: bool,
}

impl GlitchOp for ReduplicateWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        if buffer.word_count() == 0 {
            return Ok(());
        }

        let total_words = buffer.word_count();
        let mut candidates: Vec<ReduplicateCandidate> = Vec::new();
        for idx in 0..total_words {
            if let Some(segment) = buffer.word_segment(idx) {
                if matches!(segment.kind(), SegmentKind::Separator) {
                    continue;
                }
                let original = segment.text().to_string();
                if original.trim().is_empty() {
                    continue;
                }
                let (prefix, core, suffix) = split_affixes(&original);
                let weight = if self.unweighted {
                    1.0
                } else {
                    inverse_length_weight(&core, &original)
                };
                candidates.push(ReduplicateCandidate {
                    index: idx,
                    prefix,
                    core,
                    suffix,
                    weight,
                });
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let effective_rate = self.reduplication_rate.max(0.0);
        if effective_rate <= 0.0 {
            return Ok(());
        }

        let mean_weight = candidates
            .iter()
            .map(|candidate| candidate.weight)
            .sum::<f64>()
            / (candidates.len() as f64);

        let mut offset = 0usize;
        for candidate in candidates.into_iter() {
            let probability = if effective_rate >= 1.0 {
                1.0
            } else if mean_weight <= f64::EPSILON {
                effective_rate
            } else {
                (effective_rate * (candidate.weight / mean_weight)).min(1.0)
            };

            if rng.random()? >= probability {
                continue;
            }

            let target = candidate.index + offset;
            let first = format!("{}{}", candidate.prefix, candidate.core);
            let second = format!("{}{}", candidate.core, candidate.suffix);
            buffer.replace_word(target, &first)?;
            buffer.insert_word_after(target, &second, Some(" "))?;
            offset += 1;
        }

        Ok(())
    }
}

/// Deletes random words while preserving punctuation cleanup semantics.
#[derive(Debug, Clone, Copy)]
pub struct DeleteRandomWordsOp {
    pub max_deletion_rate: f64,
    pub unweighted: bool,
}

impl GlitchOp for DeleteRandomWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        if buffer.word_count() <= 1 {
            return Ok(());
        }

        let total_words = buffer.word_count();
        let mut candidates: Vec<DeleteCandidate> = Vec::new();
        for idx in 1..total_words {
            if let Some(segment) = buffer.word_segment(idx) {
                let text = segment.text();
                if text.is_empty() || is_whitespace_only(text) {
                    continue;
                }
                let original = text.to_string();
                let (prefix, core, suffix) = split_affixes(&original);
                let weight = if self.unweighted {
                    1.0
                } else {
                    inverse_length_weight(&core, &original)
                };
                candidates.push(DeleteCandidate {
                    index: idx,
                    prefix,
                    suffix,
                    weight,
                });
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let effective_rate = self.max_deletion_rate.max(0.0);
        if effective_rate <= 0.0 {
            return Ok(());
        }

        let allowed = ((candidates.len() as f64) * effective_rate).floor() as usize;
        if allowed == 0 {
            return Ok(());
        }

        let mean_weight = candidates
            .iter()
            .map(|candidate| candidate.weight)
            .sum::<f64>()
            / (candidates.len() as f64);

        let mut deletions = 0usize;
        for candidate in candidates.into_iter() {
            if deletions >= allowed {
                break;
            }

            let probability = if effective_rate >= 1.0 {
                1.0
            } else if mean_weight <= f64::EPSILON {
                effective_rate
            } else {
                (effective_rate * (candidate.weight / mean_weight)).min(1.0)
            };

            if rng.random()? >= probability {
                continue;
            }

            let replacement = format!("{}{}", candidate.prefix.trim(), candidate.suffix.trim());
            buffer.replace_word(candidate.index, &replacement)?;
            deletions += 1;
        }

        let mut joined = buffer.to_string();
        joined = SPACE_BEFORE_PUNCTUATION
            .replace_all(&joined, "$1")
            .into_owned();
        joined = MULTIPLE_WHITESPACE.replace_all(&joined, " ").into_owned();
        let final_text = joined.trim().to_string();
        *buffer = TextBuffer::from_owned(final_text);
        Ok(())
    }
}

/// Swaps adjacent word cores while keeping punctuation and spacing intact.
#[derive(Debug, Clone, Copy)]
pub struct SwapAdjacentWordsOp {
    pub swap_rate: f64,
}

impl GlitchOp for SwapAdjacentWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let total_words = buffer.word_count();
        if total_words < 2 {
            return Ok(());
        }

        let clamped = self.swap_rate.max(0.0).min(1.0);
        if clamped <= 0.0 {
            return Ok(());
        }

        let mut index = 0usize;
        while index + 1 < total_words {
            let left_segment = match buffer.word_segment(index) {
                Some(segment) => segment,
                None => break,
            };
            let right_segment = match buffer.word_segment(index + 1) {
                Some(segment) => segment,
                None => break,
            };

            let left_original = left_segment.text().to_string();
            let right_original = right_segment.text().to_string();

            let (left_prefix, left_core, left_suffix) = split_affixes(&left_original);
            let (right_prefix, right_core, right_suffix) = split_affixes(&right_original);

            if left_core.is_empty() || right_core.is_empty() {
                index += 2;
                continue;
            }

            let should_swap = clamped >= 1.0 || rng.random()? < clamped;
            if should_swap {
                let left_replacement = format!("{left_prefix}{right_core}{left_suffix}");
                let right_replacement = format!("{right_prefix}{left_core}{right_suffix}");
                buffer.replace_word(index, &left_replacement)?;
                buffer.replace_word(index + 1, &right_replacement)?;
            }

            index += 2;
        }

        Ok(())
    }
}

/// Redacts words by replacing core characters with a replacement token.
#[derive(Debug, Clone)]
pub struct RedactWordsOp {
    pub replacement_char: String,
    pub redaction_rate: f64,
    pub merge_adjacent: bool,
    pub unweighted: bool,
}

impl GlitchOp for RedactWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        if buffer.word_count() == 0 {
            return Err(GlitchOpError::NoRedactableWords);
        }

        let total_words = buffer.word_count();
        let mut candidates: Vec<RedactCandidate> = Vec::new();
        for idx in 0..total_words {
            if let Some(segment) = buffer.word_segment(idx) {
                let text = segment.text();
                if text.trim().is_empty() {
                    continue;
                }
                let original = text.to_string();
                let (prefix, core, suffix) = split_affixes(&original);
                if core.is_empty() {
                    continue;
                }
                let repeat = core.chars().count();
                if repeat == 0 {
                    continue;
                }
                let weight = if self.unweighted {
                    1.0
                } else {
                    direct_length_weight(&core, &original)
                };
                candidates.push(RedactCandidate {
                    index: idx,
                    prefix,
                    suffix,
                    repeat,
                    weight,
                });
            }
        }

        if candidates.is_empty() {
            return Err(GlitchOpError::NoRedactableWords);
        }

        let effective_rate = self.redaction_rate.max(0.0);
        let mut num_to_redact = ((candidates.len() as f64) * effective_rate).floor() as usize;
        if num_to_redact < 1 {
            num_to_redact = 1;
        }
        if num_to_redact > candidates.len() {
            return Err(GlitchOpError::ExcessiveRedaction {
                requested: num_to_redact,
                available: candidates.len(),
            });
        }

        let weighted_indices: Vec<(usize, f64)> = candidates
            .iter()
            .enumerate()
            .map(|(idx, candidate)| (idx, candidate.weight))
            .collect();

        let mut selections =
            weighted_sample_without_replacement(rng, &weighted_indices, num_to_redact)?;
        selections.sort_unstable_by_key(|candidate_idx| candidates[*candidate_idx].index);

        for selection in selections {
            let candidate = &candidates[selection];
            let mut replacement = String::with_capacity(
                candidate.prefix.len()
                    + candidate.suffix.len()
                    + self.replacement_char.len() * candidate.repeat,
            );
            replacement.push_str(&candidate.prefix);
            for _ in 0..candidate.repeat {
                replacement.push_str(&self.replacement_char);
            }
            replacement.push_str(&candidate.suffix);
            buffer.replace_word(candidate.index, &replacement)?;
        }

        if self.merge_adjacent {
            let text = buffer.to_string();
            let pattern = format!(
                "{}\\W+{}",
                regex::escape(&self.replacement_char),
                regex::escape(&self.replacement_char)
            );
            let regex = Regex::new(&pattern).map_err(|err| {
                GlitchOpError::Regex(format!("failed to build merge regex: {err}"))
            })?;
            let merged = regex
                .replace_all(&text, |caps: &Captures| {
                    let matched = caps.get(0).map_or("", |m| m.as_str());
                    let repeat = matched.chars().count().saturating_sub(1);
                    self.replacement_char.repeat(repeat)
                })
                .into_owned();
            *buffer = TextBuffer::from_owned(merged);
        }

        Ok(())
    }
}

/// Introduces OCR-style character confusions.
#[derive(Debug, Clone, Copy)]
pub struct OcrArtifactsOp {
    pub error_rate: f64,
}

impl GlitchOp for OcrArtifactsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let text = buffer.to_string();
        if text.is_empty() {
            return Ok(());
        }

        let mut candidates: Vec<(usize, usize, &'static [&'static str])> = Vec::new();
        for &(src, choices) in confusion_table() {
            for (start, _) in text.match_indices(src) {
                candidates.push((start, start + src.len(), choices));
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let to_select = ((candidates.len() as f64) * self.error_rate).floor() as usize;
        if to_select == 0 {
            return Ok(());
        }

        let mut order: Vec<usize> = (0..candidates.len()).collect();
        // We hand-roll Fisher–Yates instead of using helper utilities so the
        // shuffle mirrors Python's `random.shuffle` exactly. The regression
        // tests rely on this parity to keep the Rust and Python paths in lockstep.
        for idx in (1..order.len()).rev() {
            let swap_with = rng.rand_index(idx + 1)?;
            order.swap(idx, swap_with);
        }
        let mut chosen: Vec<(usize, usize, &'static str)> = Vec::new();
        let mut occupied: Vec<(usize, usize)> = Vec::new();

        for idx in order {
            if chosen.len() >= to_select {
                break;
            }
            let (start, end, choices) = candidates[idx];
            if choices.is_empty() {
                continue;
            }
            if occupied.iter().any(|&(s, e)| !(end <= s || e <= start)) {
                continue;
            }
            let choice_idx = rng.rand_index(choices.len())?;
            chosen.push((start, end, choices[choice_idx]));
            occupied.push((start, end));
        }

        if chosen.is_empty() {
            return Ok(());
        }

        chosen.sort_by_key(|&(start, _, _)| start);
        let mut output = String::with_capacity(text.len());
        let mut cursor = 0usize;
        for (start, end, replacement) in chosen {
            if cursor < start {
                output.push_str(&text[cursor..start]);
            }
            output.push_str(replacement);
            cursor = end;
        }
        if cursor < text.len() {
            output.push_str(&text[cursor..]);
        }

        *buffer = TextBuffer::from_owned(output);
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct ZeroWidthOp {
    pub rate: f64,
    pub characters: Vec<String>,
}

impl GlitchOp for ZeroWidthOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let palette: Vec<String> = self
            .characters
            .iter()
            .filter(|value| !value.is_empty())
            .cloned()
            .collect();
        if palette.is_empty() {
            return Ok(());
        }

        let text = buffer.to_string();
        if text.is_empty() {
            return Ok(());
        }

        let chars: Vec<char> = text.chars().collect();
        if chars.len() < 2 {
            return Ok(());
        }

        let mut positions: Vec<usize> = Vec::new();
        for index in 0..(chars.len() - 1) {
            if !chars[index].is_whitespace() && !chars[index + 1].is_whitespace() {
                positions.push(index + 1);
            }
        }

        if positions.is_empty() {
            return Ok(());
        }

        let clamped_rate = if self.rate.is_nan() {
            0.0
        } else {
            self.rate.max(0.0)
        };
        if clamped_rate <= 0.0 {
            return Ok(());
        }

        let total = positions.len();
        let mut count = (clamped_rate * total as f64).floor() as usize;
        let remainder = clamped_rate * total as f64 - count as f64;
        if remainder > 0.0 && rng.random()? < remainder {
            count += 1;
        }
        if count > total {
            count = total;
        }
        if count == 0 {
            return Ok(());
        }

        let mut index_samples = rng.sample_indices(total, count)?;
        index_samples.sort_unstable();
        let mut chosen: Vec<usize> = index_samples
            .into_iter()
            .map(|sample| positions[sample])
            .collect();

        let mut result = String::with_capacity(text.len() + count);
        let mut iter = chosen.into_iter();
        let mut next = iter.next();

        for (idx, ch) in chars.iter().enumerate() {
            result.push(*ch);
            if let Some(insert_pos) = next {
                if insert_pos == idx + 1 {
                    let palette_idx = rng.rand_index(palette.len())?;
                    result.push_str(&palette[palette_idx]);
                    next = iter.next();
                }
            }
        }

        *buffer = TextBuffer::from_owned(result);
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct TypoOp {
    pub rate: f64,
    pub layout: HashMap<String, Vec<String>>,
}

impl TypoOp {
    fn is_word_char(c: char) -> bool {
        c.is_alphanumeric() || c == '_'
    }

    fn eligible_idx(chars: &[char], idx: usize) -> bool {
        if idx == 0 || idx + 1 >= chars.len() {
            return false;
        }
        if !Self::is_word_char(chars[idx]) {
            return false;
        }
        Self::is_word_char(chars[idx - 1]) && Self::is_word_char(chars[idx + 1])
    }

    fn draw_eligible_index(
        rng: &mut dyn GlitchRng,
        chars: &[char],
        max_tries: usize,
    ) -> Result<Option<usize>, GlitchOpError> {
        let n = chars.len();
        if n == 0 {
            return Ok(None);
        }

        for _ in 0..max_tries {
            let idx = rng.rand_index(n)?;
            if Self::eligible_idx(chars, idx) {
                return Ok(Some(idx));
            }
        }

        let start = rng.rand_index(n)?;
        if Self::eligible_idx(chars, start) {
            return Ok(Some(start));
        }

        let mut i = (start + 1) % n;
        while i != start {
            if Self::eligible_idx(chars, i) {
                return Ok(Some(i));
            }
            i = (i + 1) % n;
        }

        Ok(None)
    }

    fn neighbors_for_char(&self, ch: char) -> Vec<String> {
        let key: String = ch.to_lowercase().collect();
        self.layout.get(&key).cloned().unwrap_or_default()
    }

    fn remove_space(rng: &mut dyn GlitchRng, chars: &mut Vec<char>) -> Result<(), GlitchOpError> {
        let positions: Vec<usize> = chars
            .iter()
            .enumerate()
            .filter_map(|(idx, ch)| if *ch == ' ' { Some(idx) } else { None })
            .collect();
        if positions.is_empty() {
            return Ok(());
        }
        let choice = rng.rand_index(positions.len())?;
        let idx = positions[choice];
        if idx < chars.len() {
            chars.remove(idx);
        }
        Ok(())
    }

    fn insert_space(rng: &mut dyn GlitchRng, chars: &mut Vec<char>) -> Result<(), GlitchOpError> {
        if chars.len() < 2 {
            return Ok(());
        }
        let idx = rng.rand_index(chars.len() - 1)? + 1;
        if idx <= chars.len() {
            chars.insert(idx, ' ');
        }
        Ok(())
    }

    fn repeat_char(rng: &mut dyn GlitchRng, chars: &mut Vec<char>) -> Result<(), GlitchOpError> {
        let positions: Vec<usize> = chars
            .iter()
            .enumerate()
            .filter_map(|(idx, ch)| if ch.is_whitespace() { None } else { Some(idx) })
            .collect();
        if positions.is_empty() {
            return Ok(());
        }
        let choice = rng.rand_index(positions.len())?;
        let idx = positions[choice];
        if idx < chars.len() {
            let ch = chars[idx];
            chars.insert(idx, ch);
        }
        Ok(())
    }

    fn collapse_duplicate(
        rng: &mut dyn GlitchRng,
        chars: &mut Vec<char>,
    ) -> Result<(), GlitchOpError> {
        if chars.len() < 3 {
            return Ok(());
        }
        let mut matches: Vec<usize> = Vec::new();
        let mut i = 0;
        while i + 2 < chars.len() {
            if chars[i] == chars[i + 1] && Self::is_word_char(chars[i + 2]) {
                matches.push(i);
                i += 2;
            } else {
                i += 1;
            }
        }
        if matches.is_empty() {
            return Ok(());
        }
        let choice = rng.rand_index(matches.len())?;
        let idx = matches[choice];
        if idx + 1 < chars.len() {
            chars.remove(idx + 1);
        }
        Ok(())
    }
}

impl GlitchOp for TypoOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let text = buffer.to_string();
        if text.is_empty() {
            return Ok(());
        }

        let clamped_rate = if self.rate.is_nan() {
            0.0
        } else {
            self.rate.max(0.0)
        };
        if clamped_rate <= 0.0 {
            return Ok(());
        }

        let mut chars: Vec<char> = text.chars().collect();
        if chars.is_empty() {
            return Ok(());
        }

        let mut max_changes = (chars.len() as f64 * clamped_rate).ceil() as usize;
        if max_changes == 0 {
            return Ok(());
        }

        const ACTIONS: [&str; 8] = [
            "char_swap",
            "missing_char",
            "extra_char",
            "nearby_char",
            "skipped_space",
            "random_space",
            "unichar",
            "repeated_char",
        ];

        let mut sequence: Vec<&str> = Vec::with_capacity(max_changes);
        for _ in 0..max_changes {
            let idx = rng.rand_index(ACTIONS.len())?;
            sequence.push(ACTIONS[idx]);
        }

        for action in sequence {
            match action {
                "char_swap" | "missing_char" | "extra_char" | "nearby_char" => {
                    if let Some(idx) = Self::draw_eligible_index(rng, &chars, 16)? {
                        match action {
                            "char_swap" => {
                                if idx + 1 < chars.len() {
                                    chars.swap(idx, idx + 1);
                                }
                            }
                            "missing_char" => {
                                if idx < chars.len() {
                                    chars.remove(idx);
                                }
                            }
                            "extra_char" => {
                                if idx <= chars.len() {
                                    let ch = chars[idx];
                                    let mut neighbors = self.neighbors_for_char(ch);
                                    if neighbors.is_empty() {
                                        neighbors.push(ch.to_string());
                                    }
                                    let choice = rng.rand_index(neighbors.len())?;
                                    let insertion: Vec<char> = neighbors[choice].chars().collect();
                                    chars.splice(idx..idx, insertion);
                                }
                            }
                            "nearby_char" => {
                                if idx < chars.len() {
                                    let neighbors = self.neighbors_for_char(chars[idx]);
                                    if neighbors.is_empty() {
                                        continue;
                                    }
                                    let choice = rng.rand_index(neighbors.len())?;
                                    let replacement: Vec<char> =
                                        neighbors[choice].chars().collect();
                                    chars.splice(idx..idx + 1, replacement);
                                }
                            }
                            _ => {}
                        }
                    }
                }
                "skipped_space" => {
                    Self::remove_space(rng, &mut chars)?;
                }
                "random_space" => {
                    Self::insert_space(rng, &mut chars)?;
                }
                "unichar" => {
                    Self::collapse_duplicate(rng, &mut chars)?;
                }
                "repeated_char" => {
                    Self::repeat_char(rng, &mut chars)?;
                }
                _ => {}
            }
        }

        *buffer = TextBuffer::from_owned(chars.into_iter().collect());
        Ok(())
    }
}

/// Type-erased glitchling operation for pipeline sequencing.
#[derive(Debug, Clone)]
pub enum GlitchOperation {
    Reduplicate(ReduplicateWordsOp),
    Delete(DeleteRandomWordsOp),
    SwapAdjacent(SwapAdjacentWordsOp),
    Redact(RedactWordsOp),
    Ocr(OcrArtifactsOp),
    Typo(TypoOp),
    ZeroWidth(ZeroWidthOp),
}

impl GlitchOp for GlitchOperation {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        match self {
            GlitchOperation::Reduplicate(op) => op.apply(buffer, rng),
            GlitchOperation::Delete(op) => op.apply(buffer, rng),
            GlitchOperation::SwapAdjacent(op) => op.apply(buffer, rng),
            GlitchOperation::Redact(op) => op.apply(buffer, rng),
            GlitchOperation::Ocr(op) => op.apply(buffer, rng),
            GlitchOperation::Typo(op) => op.apply(buffer, rng),
            GlitchOperation::ZeroWidth(op) => op.apply(buffer, rng),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        DeleteRandomWordsOp, GlitchOp, GlitchOpError, OcrArtifactsOp, RedactWordsOp,
        ReduplicateWordsOp, SwapAdjacentWordsOp,
    };
    use crate::rng::PyRng;
    use crate::text_buffer::TextBuffer;

    #[test]
    fn reduplication_inserts_duplicate_with_space() {
        let mut buffer = TextBuffer::from_str("Hello world");
        let mut rng = PyRng::new(151);
        let op = ReduplicateWordsOp {
            reduplication_rate: 1.0,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng)
            .expect("reduplication works");
        assert_eq!(buffer.to_string(), "Hello Hello world world");
    }

    #[test]
    fn swap_adjacent_words_swaps_cores() {
        let mut buffer = TextBuffer::from_str("Alpha, beta! Gamma delta");
        let mut rng = PyRng::new(7);
        let op = SwapAdjacentWordsOp { swap_rate: 1.0 };
        op.apply(&mut buffer, &mut rng)
            .expect("swap operation succeeds");
        assert_eq!(buffer.to_string(), "beta, Alpha! delta Gamma");
    }

    #[test]
    fn swap_adjacent_words_respects_zero_rate() {
        let original = "Do not move these words";
        let mut buffer = TextBuffer::from_str(original);
        let mut rng = PyRng::new(42);
        let op = SwapAdjacentWordsOp { swap_rate: 0.0 };
        op.apply(&mut buffer, &mut rng)
            .expect("swap operation succeeds");
        assert_eq!(buffer.to_string(), original);
    }

    #[test]
    fn delete_random_words_cleans_up_spacing() {
        let mut buffer = TextBuffer::from_str("One two three four five");
        let mut rng = PyRng::new(151);
        let op = DeleteRandomWordsOp {
            max_deletion_rate: 0.75,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("deletion works");
        assert_eq!(buffer.to_string(), "One three four");
    }

    #[test]
    fn redact_words_respects_sample_and_merge() {
        let mut buffer = TextBuffer::from_str("Keep secrets safe");
        let mut rng = PyRng::new(151);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            redaction_rate: 0.8,
            merge_adjacent: true,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("redaction works");
        let result = buffer.to_string();
        assert!(result.contains("█"));
    }

    #[test]
    fn redact_words_without_candidates_errors() {
        let mut buffer = TextBuffer::from_str("   ");
        let mut rng = PyRng::new(151);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            redaction_rate: 0.5,
            merge_adjacent: false,
            unweighted: false,
        };
        let error = op.apply(&mut buffer, &mut rng).unwrap_err();
        match error {
            GlitchOpError::NoRedactableWords => {}
            other => panic!("expected no redactable words, got {other:?}"),
        }
    }

    #[test]
    fn ocr_artifacts_replaces_expected_regions() {
        let mut buffer = TextBuffer::from_str("Hello rn world");
        let mut rng = PyRng::new(151);
        let op = OcrArtifactsOp { error_rate: 1.0 };
        op.apply(&mut buffer, &mut rng).expect("ocr works");
        let text = buffer.to_string();
        assert_ne!(text, "Hello rn world");
        assert!(text.contains('m') || text.contains('h'));
    }

    #[test]
    fn reduplication_matches_python_reference_seed_123() {
        let mut buffer = TextBuffer::from_str("The quick brown fox");
        let mut rng = PyRng::new(123);
        let op = ReduplicateWordsOp {
            reduplication_rate: 0.5,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng)
            .expect("reduplication succeeds");
        assert_eq!(buffer.to_string(), "The The quick quick brown fox fox");
    }

    #[test]
    fn delete_matches_python_reference_seed_123() {
        let mut buffer = TextBuffer::from_str("The quick brown fox jumps over the lazy dog.");
        let mut rng = PyRng::new(123);
        let op = DeleteRandomWordsOp {
            max_deletion_rate: 0.5,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("deletion succeeds");
        assert_eq!(buffer.to_string(), "The over the lazy dog.");
    }

    #[test]
    fn redact_matches_python_reference_seed_42() {
        let mut buffer = TextBuffer::from_str("Hide these words please");
        let mut rng = PyRng::new(42);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            redaction_rate: 0.5,
            merge_adjacent: false,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("redaction succeeds");
        assert_eq!(buffer.to_string(), "████ these █████ please");
    }

    #[test]
    fn redact_merge_matches_python_reference_seed_7() {
        let mut buffer = TextBuffer::from_str("redact these words");
        let mut rng = PyRng::new(7);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            redaction_rate: 1.0,
            merge_adjacent: true,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("redaction succeeds");
        assert_eq!(buffer.to_string(), "█████████████████");
    }

    #[test]
    fn ocr_matches_python_reference_seed_1() {
        let mut buffer = TextBuffer::from_str("The m rn");
        let mut rng = PyRng::new(1);
        let op = OcrArtifactsOp { error_rate: 1.0 };
        op.apply(&mut buffer, &mut rng).expect("ocr succeeds");
        assert_eq!(buffer.to_string(), "Tlie rn rri");
    }
}

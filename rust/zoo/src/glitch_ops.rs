use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::PyErr;
use regex::{Captures, Regex};
use smallvec::SmallVec;
use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

use crate::ekkokin::EkkokinOp;
use crate::mim1c::Mim1cOp;
use crate::pedant::PedantOp;
use crate::resources::{
    affix_bounds, apostrofae_pairs, confusion_table, is_whitespace_only, split_affixes,
    MULTIPLE_WHITESPACE, SPACE_BEFORE_PUNCTUATION,
};
use crate::rng::{DeterministicRng, RngError};
use crate::spectroll::SpectrollOp;
use crate::text_buffer::{SegmentKind, TextBuffer, TextBufferError};

static MERGE_REGEX_CACHE: OnceLock<Mutex<HashMap<String, Regex>>> = OnceLock::new();

/// Errors produced while applying a [`GlitchOp`].
#[derive(Debug)]
pub enum GlitchOpError {
    Buffer(TextBufferError),
    NoRedactableWords,
    ExcessiveRedaction { requested: usize, available: usize },
    Rng(RngError),
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
            GlitchOpError::Regex(message) => PyRuntimeError::new_err(message),
        }
    }
}

impl From<TextBufferError> for GlitchOpError {
    fn from(value: TextBufferError) -> Self {
        GlitchOpError::Buffer(value)
    }
}

impl From<RngError> for GlitchOpError {
    fn from(value: RngError) -> Self {
        GlitchOpError::Rng(value)
    }
}

/// RNG abstraction used by glitchling operations.
pub trait GlitchRng {
    fn random(&mut self) -> Result<f64, GlitchOpError>;
    fn rand_index(&mut self, upper: usize) -> Result<usize, GlitchOpError>;
    #[allow(dead_code)]
    fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, GlitchOpError>;
}

impl GlitchRng for DeterministicRng {
    fn random(&mut self) -> Result<f64, GlitchOpError> {
        Ok(DeterministicRng::random(self))
    }

    fn rand_index(&mut self, upper: usize) -> Result<usize, GlitchOpError> {
        DeterministicRng::rand_index(self, upper).map_err(GlitchOpError::from)
    }

    #[allow(dead_code)]
    fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, GlitchOpError> {
        DeterministicRng::sample_indices(self, population, k).map_err(GlitchOpError::from)
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
    core_start: usize,
    core_end: usize,
    repeat: usize,
    weight: f64,
}

fn cached_merge_regex(token: &str) -> Result<Regex, GlitchOpError> {
    let cache = MERGE_REGEX_CACHE.get_or_init(|| Mutex::new(HashMap::new()));
    if let Some(regex) = cache.lock().unwrap().get(token).cloned() {
        return Ok(regex);
    }

    let pattern = format!("{}\\W+{}", regex::escape(token), regex::escape(token));
    let compiled = Regex::new(&pattern)
        .map_err(|err| GlitchOpError::Regex(format!("failed to build merge regex: {err}")))?;

    let mut guard = cache.lock().unwrap();
    let entry = guard.entry(token.to_string()).or_insert_with(|| compiled);
    Ok(entry.clone())
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
    pub rate: f64,
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

        let effective_rate = self.rate.max(0.0);
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
    pub rate: f64,
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

        let effective_rate = self.rate.max(0.0);
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

        // Collect deletion decisions
        use std::collections::HashSet;
        let mut delete_set: HashSet<usize> = HashSet::new();
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

            delete_set.insert(candidate.index);
            deletions += 1;
        }

        // Build output string in a single pass with normalization
        let mut result = String::new();
        let mut needs_separator = false;

        for (_seg_idx, segment, word_idx_opt) in buffer.segments_with_word_indices() {
            match segment.kind() {
                SegmentKind::Word => {
                    if let Some(word_idx) = word_idx_opt {
                        if delete_set.contains(&word_idx) {
                            // Word is deleted - emit only affixes
                            let text = segment.text();
                            let (prefix, _core, suffix) = split_affixes(text);
                            let combined = format!("{}{}", prefix.trim(), suffix.trim());

                            if !combined.is_empty() {
                                // Check if we need space before this
                                if needs_separator {
                                    let starts_with_punct = combined.chars().next()
                                        .map(|c| matches!(c, '.' | ',' | ':' | ';'))
                                        .unwrap_or(false);
                                    if !starts_with_punct {
                                        result.push(' ');
                                    }
                                }
                                result.push_str(&combined);
                                needs_separator = true;
                            }
                            continue;
                        }
                    }

                    // Word not deleted - emit with separator if needed
                    let text = segment.text();
                    if !text.is_empty() {
                        if needs_separator {
                            let starts_with_punct = text.chars().next()
                                .map(|c| matches!(c, '.' | ',' | ':' | ';'))
                                .unwrap_or(false);
                            if !starts_with_punct {
                                result.push(' ');
                            }
                        }
                        result.push_str(text);
                        needs_separator = true;
                    }
                }
                SegmentKind::Separator => {
                    // Mark that we need a separator before the next word
                    // (actual separator will be added when we emit next word)
                    let sep_text = segment.text();
                    if sep_text.contains('\n') || !sep_text.trim().is_empty() {
                        needs_separator = true;
                    }
                }
            }
        }

        let final_text = result.trim().to_string();
        *buffer = TextBuffer::from_owned(final_text);
        Ok(())
    }
}

/// Swaps adjacent word cores while keeping punctuation and spacing intact.
#[derive(Debug, Clone, Copy)]
pub struct SwapAdjacentWordsOp {
    pub rate: f64,
}

impl GlitchOp for SwapAdjacentWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let total_words = buffer.word_count();
        if total_words < 2 {
            return Ok(());
        }

        let clamped = self.rate.max(0.0).min(1.0);
        if clamped <= 0.0 {
            return Ok(());
        }

        let mut index = 0usize;
        let mut replacements: SmallVec<[(usize, String); 8]> = SmallVec::new();
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
                replacements.push((index, left_replacement));
                replacements.push((index + 1, right_replacement));
            }

            index += 2;
        }

        if !replacements.is_empty() {
            buffer.replace_words_bulk(replacements.into_iter())?;
        }

        Ok(())
    }
}

#[derive(Debug, Clone, Copy)]
pub enum RushmoreComboMode {
    Delete,
    Duplicate,
    Swap,
}

#[derive(Debug, Clone)]
pub struct RushmoreComboOp {
    pub modes: Vec<RushmoreComboMode>,
    pub delete: Option<DeleteRandomWordsOp>,
    pub duplicate: Option<ReduplicateWordsOp>,
    pub swap: Option<SwapAdjacentWordsOp>,
}

impl RushmoreComboOp {
    pub fn new(
        modes: Vec<RushmoreComboMode>,
        delete: Option<DeleteRandomWordsOp>,
        duplicate: Option<ReduplicateWordsOp>,
        swap: Option<SwapAdjacentWordsOp>,
    ) -> Self {
        Self {
            modes,
            delete,
            duplicate,
            swap,
        }
    }
}

impl GlitchOp for RushmoreComboOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        for mode in &self.modes {
            match mode {
                RushmoreComboMode::Delete => {
                    if let Some(op) = self.delete {
                        op.apply(buffer, rng)?;
                    }
                }
                RushmoreComboMode::Duplicate => {
                    if let Some(op) = self.duplicate {
                        op.apply(buffer, rng)?;
                    }
                }
                RushmoreComboMode::Swap => {
                    if let Some(op) = self.swap {
                        op.apply(buffer, rng)?;
                    }
                }
            }
        }

        Ok(())
    }
}

/// Redacts words by replacing core characters with a replacement token.
#[derive(Debug, Clone)]
pub struct RedactWordsOp {
    pub replacement_char: String,
    pub rate: f64,
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
                let Some((core_start, core_end)) = affix_bounds(text) else {
                    continue;
                };
                if core_start == core_end {
                    continue;
                }
                let core = &text[core_start..core_end];
                let repeat = core.chars().count();
                if repeat == 0 {
                    continue;
                }
                let weight = if self.unweighted {
                    1.0
                } else {
                    direct_length_weight(core, text)
                };
                candidates.push(RedactCandidate {
                    index: idx,
                    core_start,
                    core_end,
                    repeat,
                    weight,
                });
            }
        }

        if candidates.is_empty() {
            return Err(GlitchOpError::NoRedactableWords);
        }

        let effective_rate = self.rate.max(0.0);
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

        // Build map of word_index -> RedactCandidate for selected words
        use std::collections::HashMap;
        let mut redact_map: HashMap<usize, &RedactCandidate> = HashMap::new();
        for selection in selections {
            let candidate = &candidates[selection];
            redact_map.insert(candidate.index, candidate);
        }

        // Build output string in a single pass
        let mut result = String::new();
        let mut pending_tokens = 0usize;
        let mut pending_suffix = String::new();

        for (_seg_idx, segment, word_idx_opt) in buffer.segments_with_word_indices() {
            match segment.kind() {
                SegmentKind::Word => {
                    // Check if this word should be redacted
                    if let Some(word_idx) = word_idx_opt {
                        if let Some(candidate) = redact_map.get(&word_idx) {
                            let text = segment.text();

                            // Re-validate bounds in case segment changed
                            let (core_start, core_end, repeat) = if candidate.core_end <= text.len()
                                && candidate.core_start <= candidate.core_end
                                && candidate.core_start <= text.len()
                            {
                                (candidate.core_start, candidate.core_end, candidate.repeat)
                            } else if let Some((start, end)) = affix_bounds(text) {
                                let repeat = text[start..end].chars().count();
                                if repeat == 0 {
                                    // Can't redact - treat as non-redacted
                                    if pending_tokens > 0 {
                                        result.push_str(&self.replacement_char.repeat(pending_tokens));
                                        result.push_str(&pending_suffix);
                                        pending_tokens = 0;
                                        pending_suffix.clear();
                                    }
                                    result.push_str(text);
                                    continue;
                                }
                                (start, end, repeat)
                            } else {
                                // Can't redact - treat as non-redacted
                                if pending_tokens > 0 {
                                    result.push_str(&self.replacement_char.repeat(pending_tokens));
                                    result.push_str(&pending_suffix);
                                    pending_tokens = 0;
                                    pending_suffix.clear();
                                }
                                result.push_str(text);
                                continue;
                            };

                            let prefix = &text[..core_start];
                            let suffix = &text[core_end..];

                            if self.merge_adjacent {
                                // Accumulate tokens for merging
                                if pending_tokens == 0 {
                                    // Start of new redaction block
                                    result.push_str(prefix);
                                }
                                pending_tokens += repeat;
                                pending_suffix = suffix.to_string();
                            } else {
                                // Not merging - emit immediately
                                result.push_str(prefix);
                                result.push_str(&self.replacement_char.repeat(repeat));
                                result.push_str(suffix);
                            }
                            continue;
                        }
                    }

                    // Not redacted - flush any pending redaction first
                    if pending_tokens > 0 {
                        result.push_str(&self.replacement_char.repeat(pending_tokens));
                        result.push_str(&pending_suffix);
                        pending_tokens = 0;
                        pending_suffix.clear();
                    }
                    result.push_str(segment.text());
                }
                SegmentKind::Separator => {
                    if self.merge_adjacent && pending_tokens > 0 {
                        // Check if this separator should be skipped (merged across)
                        let sep_text = segment.text();
                        // Skip if separator is only punctuation/whitespace (non-word characters)
                        if sep_text.chars().all(|c| !c.is_alphanumeric() && c != '_') {
                            continue; // Skip this separator - we're merging across it
                        }
                    }

                    // Not merging or separator contains word characters - flush pending
                    if pending_tokens > 0 {
                        result.push_str(&self.replacement_char.repeat(pending_tokens));
                        result.push_str(&pending_suffix);
                        pending_tokens = 0;
                        pending_suffix.clear();
                    }
                    result.push_str(segment.text());
                }
            }
        }

        // Flush any final pending redaction
        if pending_tokens > 0 {
            result.push_str(&self.replacement_char.repeat(pending_tokens));
            result.push_str(&pending_suffix);
        }

        *buffer = TextBuffer::from_owned(result);
        Ok(())
    }
}

/// Introduces OCR-style character confusions.
#[derive(Debug, Clone, Copy)]
pub struct OcrArtifactsOp {
    pub rate: f64,
}

impl GlitchOp for OcrArtifactsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        // Find candidates across all segments
        // Track (segment_index, start_byte_in_segment, end_byte_in_segment, choices)
        let mut candidates: Vec<(usize, usize, usize, &'static [&'static str])> = Vec::new();

        for (seg_idx, segment) in segments.iter().enumerate() {
            let seg_text = segment.text();
            for &(src, choices) in confusion_table() {
                for (start, _) in seg_text.match_indices(src) {
                    candidates.push((seg_idx, start, start + src.len(), choices));
                }
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let to_select = ((candidates.len() as f64) * self.rate).floor() as usize;
        if to_select == 0 {
            return Ok(());
        }

        let mut order: Vec<usize> = (0..candidates.len()).collect();
        // Hand-roll Fisher–Yates to mirror Python's random.shuffle for test parity
        for idx in (1..order.len()).rev() {
            let swap_with = rng.rand_index(idx + 1)?;
            order.swap(idx, swap_with);
        }

        let mut chosen: Vec<(usize, usize, usize, &'static str)> = Vec::new();
        let mut occupied: std::collections::HashMap<usize, Vec<(usize, usize)>> = std::collections::HashMap::new();

        for idx in order {
            if chosen.len() >= to_select {
                break;
            }
            let (seg_idx, start, end, choices) = candidates[idx];
            if choices.is_empty() {
                continue;
            }

            // Check for overlap within the same segment
            let seg_occupied = occupied.entry(seg_idx).or_default();
            if seg_occupied.iter().any(|&(s, e)| !(end <= s || e <= start)) {
                continue;
            }

            let choice_idx = rng.rand_index(choices.len())?;
            chosen.push((seg_idx, start, end, choices[choice_idx]));
            seg_occupied.push((start, end));
        }

        if chosen.is_empty() {
            return Ok(());
        }

        // Group replacements by segment
        let mut by_segment: std::collections::HashMap<usize, Vec<(usize, usize, &str)>> = std::collections::HashMap::new();
        for (seg_idx, start, end, replacement) in chosen {
            by_segment.entry(seg_idx).or_default().push((start, end, replacement));
        }

        // Build segment replacements
        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        for (seg_idx, mut seg_replacements) in by_segment {
            // Sort by start position
            seg_replacements.sort_by_key(|&(start, _, _)| start);

            let seg_text = segments[seg_idx].text();
            let mut output = String::with_capacity(seg_text.len());
            let mut cursor = 0usize;

            for (start, end, replacement) in seg_replacements {
                if cursor < start {
                    output.push_str(&seg_text[cursor..start]);
                }
                output.push_str(replacement);
                cursor = end;
            }
            if cursor < seg_text.len() {
                output.push_str(&seg_text[cursor..]);
            }

            segment_replacements.push((seg_idx, output));
        }

        // Apply all segment replacements in bulk without reparsing
        buffer.replace_segments_bulk(segment_replacements.into_iter());

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

        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        // Collect insertion positions across all segments
        // Track (segment_index, char_index_in_segment) for each insertion point
        let mut positions: Vec<(usize, usize)> = Vec::new();

        for (seg_idx, segment) in segments.iter().enumerate() {
            let text = segment.text();
            let chars: Vec<char> = text.chars().collect();

            if chars.len() < 2 {
                continue;
            }

            for char_idx in 0..(chars.len() - 1) {
                if !chars[char_idx].is_whitespace() && !chars[char_idx + 1].is_whitespace() {
                    // Mark position after char_idx (before char_idx + 1)
                    positions.push((seg_idx, char_idx + 1));
                }
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

        // Sample positions to insert zero-width characters
        let mut index_samples = rng.sample_indices(total, count)?;
        index_samples.sort_unstable();

        // Collect (seg_idx, char_idx, zero_width_char) for selected positions
        let mut insertions: Vec<(usize, usize, String)> = Vec::new();
        for sample_idx in index_samples {
            let (seg_idx, char_idx) = positions[sample_idx];
            let palette_idx = rng.rand_index(palette.len())?;
            insertions.push((seg_idx, char_idx, palette[palette_idx].clone()));
        }

        // Group insertions by segment
        use std::collections::HashMap;
        let mut by_segment: HashMap<usize, Vec<(usize, String)>> = HashMap::new();
        for (seg_idx, char_idx, zero_width) in insertions {
            by_segment.entry(seg_idx).or_default().push((char_idx, zero_width));
        }

        // Build replacement text for each affected segment
        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        for (seg_idx, mut seg_insertions) in by_segment {
            // Sort by char_idx in ascending order to build string left to right
            seg_insertions.sort_unstable_by_key(|(char_idx, _)| *char_idx);

            let original_text = segments[seg_idx].text();
            let chars: Vec<char> = original_text.chars().collect();
            let mut modified = String::with_capacity(original_text.len() + seg_insertions.len() * 5);

            let mut prev_idx = 0;
            for (char_idx, zero_width) in seg_insertions {
                // Add characters from prev_idx up to (but not including) char_idx
                for i in prev_idx..char_idx {
                    modified.push(chars[i]);
                }
                // Insert zero-width character at char_idx
                modified.push_str(&zero_width);
                prev_idx = char_idx;
            }
            // Add remaining characters from prev_idx to end
            for i in prev_idx..chars.len() {
                modified.push(chars[i]);
            }

            segment_replacements.push((seg_idx, modified));
        }

        // Apply all segment replacements in bulk
        if !segment_replacements.is_empty() {
            buffer.replace_segments_bulk(segment_replacements.into_iter());
        }

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

    fn neighbors_for_char(&self, ch: char) -> Option<&[String]> {
        let key: String = ch.to_lowercase().collect();
        self.layout
            .get(key.as_str())
            .map(|values| values.as_slice())
    }

    fn remove_space(rng: &mut dyn GlitchRng, chars: &mut Vec<char>) -> Result<(), GlitchOpError> {
        let mut count = 0usize;
        for ch in chars.iter() {
            if *ch == ' ' {
                count += 1;
            }
        }
        if count == 0 {
            return Ok(());
        }
        let choice = rng.rand_index(count)?;
        let mut seen = 0usize;
        let mut target: Option<usize> = None;
        for (idx, ch) in chars.iter().enumerate() {
            if *ch == ' ' {
                if seen == choice {
                    target = Some(idx);
                    break;
                }
                seen += 1;
            }
        }
        if let Some(idx) = target {
            if idx < chars.len() {
                chars.remove(idx);
            }
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
        let mut count = 0usize;
        for ch in chars.iter() {
            if !ch.is_whitespace() {
                count += 1;
            }
        }
        if count == 0 {
            return Ok(());
        }
        let choice = rng.rand_index(count)?;
        let mut seen = 0usize;
        for idx in 0..chars.len() {
            if !chars[idx].is_whitespace() {
                if seen == choice {
                    let ch = chars[idx];
                    chars.insert(idx, ch);
                    break;
                }
                seen += 1;
            }
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
        let total_chars = buffer.char_len();
        if total_chars == 0 {
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

        let max_changes = (total_chars as f64 * clamped_rate).ceil() as usize;
        if max_changes == 0 {
            return Ok(());
        }

        // Track modified segment texts
        let mut segment_texts: HashMap<usize, String> = HashMap::new();

        const TOTAL_ACTIONS: usize = 8;
        let mut scratch = SmallVec::<[char; 4]>::new();

        for _ in 0..max_changes {
            let action_idx = rng.rand_index(TOTAL_ACTIONS)?;

            match action_idx {
                0 | 1 | 2 | 3 => {
                    // Character-level operations within Word segments only
                    let word_segments: Vec<(usize, &TextSegment)> = buffer
                        .segments()
                        .enumerate()
                        .filter(|(_, seg)| matches!(seg.kind(), SegmentKind::Word))
                        .collect();

                    if word_segments.is_empty() {
                        continue;
                    }

                    // Pick a random word segment
                    let seg_choice = rng.rand_index(word_segments.len())?;
                    let (seg_idx, segment) = word_segments[seg_choice];

                    // Get current text (possibly modified)
                    let current_text = segment_texts
                        .get(&seg_idx)
                        .map(|s| s.as_str())
                        .unwrap_or_else(|| segment.text());

                    let mut chars: Vec<char> = current_text.chars().collect();

                    // Try to find an eligible index within this segment
                    if let Some(idx) = Self::draw_eligible_index(rng, &chars, 16)? {
                        match action_idx {
                            0 => {
                                // Swap with next char
                                if idx + 1 < chars.len() {
                                    chars.swap(idx, idx + 1);
                                }
                            }
                            1 => {
                                // Delete char
                                if idx < chars.len() {
                                    chars.remove(idx);
                                }
                            }
                            2 => {
                                // Insert keyboard neighbor before char
                                if idx < chars.len() {
                                    let ch = chars[idx];
                                    scratch.clear();
                                    match self.neighbors_for_char(ch) {
                                        Some(neighbors) if !neighbors.is_empty() => {
                                            let choice = rng.rand_index(neighbors.len())?;
                                            scratch.extend(neighbors[choice].chars());
                                        }
                                        _ => {
                                            // Maintain deterministic RNG advancement when no replacements are available.
                                            rng.rand_index(1)?;
                                            scratch.push(ch);
                                        }
                                    }
                                    if !scratch.is_empty() {
                                        chars.splice(idx..idx, scratch.iter().copied());
                                    }
                                }
                            }
                            3 => {
                                // Replace with keyboard neighbor
                                if idx < chars.len() {
                                    if let Some(neighbors) = self.neighbors_for_char(chars[idx]) {
                                        if !neighbors.is_empty() {
                                            let choice = rng.rand_index(neighbors.len())?;
                                            scratch.clear();
                                            scratch.extend(neighbors[choice].chars());
                                            if !scratch.is_empty() {
                                                chars.splice(idx..idx + 1, scratch.iter().copied());
                                            }
                                        } else {
                                            rng.rand_index(1)?;
                                        }
                                    }
                                }
                            }
                            _ => {}
                        }

                        segment_texts.insert(seg_idx, chars.into_iter().collect());
                    }
                }
                4 => {
                    // Remove space from Separator segments
                    let sep_segments: Vec<(usize, &TextSegment)> = buffer
                        .segments()
                        .enumerate()
                        .filter(|(_, seg)| matches!(seg.kind(), SegmentKind::Separator))
                        .collect();

                    if sep_segments.is_empty() {
                        continue;
                    }

                    let seg_choice = rng.rand_index(sep_segments.len())?;
                    let (seg_idx, segment) = sep_segments[seg_choice];

                    let current_text = segment_texts
                        .get(&seg_idx)
                        .map(|s| s.as_str())
                        .unwrap_or_else(|| segment.text());

                    let mut chars: Vec<char> = current_text.chars().collect();
                    Self::remove_space(rng, &mut chars)?;
                    segment_texts.insert(seg_idx, chars.into_iter().collect());
                }
                5 => {
                    // Insert space into a Word segment (splitting it)
                    let word_segments: Vec<(usize, &TextSegment)> = buffer
                        .segments()
                        .enumerate()
                        .filter(|(_, seg)| matches!(seg.kind(), SegmentKind::Word))
                        .collect();

                    if word_segments.is_empty() {
                        continue;
                    }

                    let seg_choice = rng.rand_index(word_segments.len())?;
                    let (seg_idx, segment) = word_segments[seg_choice];

                    let current_text = segment_texts
                        .get(&seg_idx)
                        .map(|s| s.as_str())
                        .unwrap_or_else(|| segment.text());

                    let mut chars: Vec<char> = current_text.chars().collect();
                    Self::insert_space(rng, &mut chars)?;
                    segment_texts.insert(seg_idx, chars.into_iter().collect());
                }
                6 => {
                    // Collapse duplicate within Word segments
                    let word_segments: Vec<(usize, &TextSegment)> = buffer
                        .segments()
                        .enumerate()
                        .filter(|(_, seg)| matches!(seg.kind(), SegmentKind::Word))
                        .collect();

                    if word_segments.is_empty() {
                        continue;
                    }

                    let seg_choice = rng.rand_index(word_segments.len())?;
                    let (seg_idx, segment) = word_segments[seg_choice];

                    let current_text = segment_texts
                        .get(&seg_idx)
                        .map(|s| s.as_str())
                        .unwrap_or_else(|| segment.text());

                    let mut chars: Vec<char> = current_text.chars().collect();
                    Self::collapse_duplicate(rng, &mut chars)?;
                    segment_texts.insert(seg_idx, chars.into_iter().collect());
                }
                7 => {
                    // Repeat char within Word segments
                    let word_segments: Vec<(usize, &TextSegment)> = buffer
                        .segments()
                        .enumerate()
                        .filter(|(_, seg)| matches!(seg.kind(), SegmentKind::Word))
                        .collect();

                    if word_segments.is_empty() {
                        continue;
                    }

                    let seg_choice = rng.rand_index(word_segments.len())?;
                    let (seg_idx, segment) = word_segments[seg_choice];

                    let current_text = segment_texts
                        .get(&seg_idx)
                        .map(|s| s.as_str())
                        .unwrap_or_else(|| segment.text());

                    let mut chars: Vec<char> = current_text.chars().collect();
                    Self::repeat_char(rng, &mut chars)?;
                    segment_texts.insert(seg_idx, chars.into_iter().collect());
                }
                _ => unreachable!("action index out of range"),
            }
        }

        // Rebuild buffer from modified segments
        if segment_texts.is_empty() {
            return Ok(());
        }

        let mut result = String::new();
        for (idx, segment) in buffer.segments().enumerate() {
            if let Some(modified_text) = segment_texts.get(&idx) {
                result.push_str(modified_text);
            } else {
                result.push_str(segment.text());
            }
        }

        *buffer = TextBuffer::from_owned(result);
        Ok(())
    }
}

#[derive(Clone, Copy, Debug)]
enum QuoteKind {
    Double,
    Single,
    Backtick,
}

impl QuoteKind {
    fn from_char(ch: char) -> Option<Self> {
        match ch {
            '"' => Some(Self::Double),
            '\'' => Some(Self::Single),
            '`' => Some(Self::Backtick),
            _ => None,
        }
    }

    fn as_char(self) -> char {
        match self {
            Self::Double => '"',
            Self::Single => '\'',
            Self::Backtick => '`',
        }
    }

    fn index(self) -> usize {
        match self {
            Self::Double => 0,
            Self::Single => 1,
            Self::Backtick => 2,
        }
    }
}

#[derive(Debug, Clone, Copy)]
struct QuotePair {
    start: usize,
    end: usize,
    kind: QuoteKind,
}

#[derive(Debug)]
struct Replacement {
    start: usize,
    end: usize,
    value: String,
}

#[derive(Debug, Default, Clone, Copy)]
pub struct QuotePairsOp;

impl QuotePairsOp {
    fn collect_pairs(text: &str) -> Vec<QuotePair> {
        let mut pairs: Vec<QuotePair> = Vec::new();
        let mut stack: [Option<usize>; 3] = [None, None, None];

        for (idx, ch) in text.char_indices() {
            if let Some(kind) = QuoteKind::from_char(ch) {
                let slot = kind.index();
                if let Some(start) = stack[slot] {
                    pairs.push(QuotePair {
                        start,
                        end: idx,
                        kind,
                    });
                    stack[slot] = None;
                } else {
                    stack[slot] = Some(idx);
                }
            }
        }

        pairs
    }
}

impl GlitchOp for QuotePairsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        // Build mapping from global byte index to (segment_index, byte_offset_in_segment)
        let mut byte_to_segment: Vec<(usize, usize)> = Vec::new(); // (seg_idx, byte_offset)
        for (seg_idx, segment) in segments.iter().enumerate() {
            let seg_text = segment.text();
            for byte_offset in 0..seg_text.len() {
                byte_to_segment.push((seg_idx, byte_offset));
            }
        }

        // Build full text for quote pair detection (we need to find pairs across segments)
        let text = buffer.to_string();
        let pairs = Self::collect_pairs(&text);
        if pairs.is_empty() {
            return Ok(());
        }

        let table = apostrofae_pairs();
        if table.is_empty() {
            return Ok(());
        }

        // Collect replacements with global byte positions
        let mut replacements: Vec<Replacement> = Vec::with_capacity(pairs.len() * 2);

        for pair in pairs {
            let key = pair.kind.as_char();
            let Some(options) = table.get(&key) else {
                continue;
            };
            if options.is_empty() {
                continue;
            }
            let choice = rng.rand_index(options.len())?;
            let (left, right) = &options[choice];
            let glyph_len = pair.kind.as_char().len_utf8();
            replacements.push(Replacement {
                start: pair.start,
                end: pair.start + glyph_len,
                value: left.clone(),
            });
            replacements.push(Replacement {
                start: pair.end,
                end: pair.end + glyph_len,
                value: right.clone(),
            });
        }

        if replacements.is_empty() {
            return Ok(());
        }

        // Group replacements by segment
        let mut by_segment: std::collections::HashMap<usize, Vec<(usize, usize, String)>> = std::collections::HashMap::new();

        for replacement in replacements {
            if replacement.start < byte_to_segment.len() {
                let (seg_idx, _) = byte_to_segment[replacement.start];
                // Calculate byte offset within segment
                let mut segment_byte_start = 0;
                for i in 0..seg_idx {
                    segment_byte_start += segments[i].text().len();
                }
                let byte_offset_in_seg = replacement.start - segment_byte_start;
                let byte_end_in_seg = byte_offset_in_seg + (replacement.end - replacement.start);

                by_segment
                    .entry(seg_idx)
                    .or_default()
                    .push((byte_offset_in_seg, byte_end_in_seg, replacement.value));
            }
        }

        // Build segment replacements
        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        for (seg_idx, mut seg_replacements) in by_segment {
            seg_replacements.sort_by_key(|&(start, _, _)| start);

            let seg_text = segments[seg_idx].text();
            let mut result = String::with_capacity(seg_text.len());
            let mut cursor = 0usize;

            for (start, end, value) in seg_replacements {
                if cursor < start {
                    result.push_str(&seg_text[cursor..start]);
                }
                result.push_str(&value);
                cursor = end;
            }
            if cursor < seg_text.len() {
                result.push_str(&seg_text[cursor..]);
            }

            segment_replacements.push((seg_idx, result));
        }

        // Apply all segment replacements in bulk without reparsing
        buffer.replace_segments_bulk(segment_replacements.into_iter());

        Ok(())
    }
}

/// Type-erased glitchling operation for pipeline sequencing.
#[derive(Debug, Clone)]
pub enum GlitchOperation {
    Reduplicate(ReduplicateWordsOp),
    Delete(DeleteRandomWordsOp),
    SwapAdjacent(SwapAdjacentWordsOp),
    RushmoreCombo(RushmoreComboOp),
    Redact(RedactWordsOp),
    Ocr(OcrArtifactsOp),
    Typo(TypoOp),
    Mimic(Mim1cOp),
    ZeroWidth(ZeroWidthOp),
    Spectroll(SpectrollOp),
    QuotePairs(QuotePairsOp),
    Hokey(crate::hokey::HokeyOp),
    Ekkokin(EkkokinOp),
    Pedant(PedantOp),
}

impl GlitchOp for GlitchOperation {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        match self {
            GlitchOperation::Reduplicate(op) => op.apply(buffer, rng),
            GlitchOperation::Delete(op) => op.apply(buffer, rng),
            GlitchOperation::SwapAdjacent(op) => op.apply(buffer, rng),
            GlitchOperation::RushmoreCombo(op) => op.apply(buffer, rng),
            GlitchOperation::Redact(op) => op.apply(buffer, rng),
            GlitchOperation::Ocr(op) => op.apply(buffer, rng),
            GlitchOperation::Typo(op) => op.apply(buffer, rng),
            GlitchOperation::Mimic(op) => op.apply(buffer, rng),
            GlitchOperation::ZeroWidth(op) => op.apply(buffer, rng),
            GlitchOperation::Spectroll(op) => op.apply(buffer, rng),
            GlitchOperation::QuotePairs(op) => op.apply(buffer, rng),
            GlitchOperation::Hokey(op) => op.apply(buffer, rng),
            GlitchOperation::Ekkokin(op) => op.apply(buffer, rng),
            GlitchOperation::Pedant(op) => op.apply(buffer, rng),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        DeleteRandomWordsOp, GlitchOp, GlitchOpError, OcrArtifactsOp, RedactWordsOp,
        ReduplicateWordsOp, SwapAdjacentWordsOp,
    };
    use crate::rng::DeterministicRng;
    use crate::text_buffer::TextBuffer;

    #[test]
    fn reduplication_inserts_duplicate_with_space() {
        let mut buffer = TextBuffer::from_str("Hello world");
        let mut rng = DeterministicRng::new(151);
        let op = ReduplicateWordsOp {
            rate: 1.0,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng)
            .expect("reduplication works");
        assert_eq!(buffer.to_string(), "Hello Hello world world");
    }

    #[test]
    fn swap_adjacent_words_swaps_cores() {
        let mut buffer = TextBuffer::from_str("Alpha, beta! Gamma delta");
        let mut rng = DeterministicRng::new(7);
        let op = SwapAdjacentWordsOp { rate: 1.0 };
        op.apply(&mut buffer, &mut rng)
            .expect("swap operation succeeds");
        let result = buffer.to_string();
        assert_ne!(result, "Alpha, beta! Gamma delta");
        assert!(result.contains("beta, Alpha"));
        assert!(result.contains("delta Gamma"));
    }

    #[test]
    fn swap_adjacent_words_respects_zero_rate() {
        let original = "Do not move these words";
        let mut buffer = TextBuffer::from_str(original);
        let mut rng = DeterministicRng::new(42);
        let op = SwapAdjacentWordsOp { rate: 0.0 };
        op.apply(&mut buffer, &mut rng)
            .expect("swap operation succeeds");
        assert_eq!(buffer.to_string(), original);
    }

    #[test]
    fn delete_random_words_cleans_up_spacing() {
        let mut buffer = TextBuffer::from_str("One two three four five");
        let mut rng = DeterministicRng::new(151);
        let op = DeleteRandomWordsOp {
            rate: 0.75,
            unweighted: false,
        };
        let original_words = buffer.to_string().split_whitespace().count();
        op.apply(&mut buffer, &mut rng).expect("deletion works");
        let result = buffer.to_string();
        assert!(result.split_whitespace().count() < original_words);
        assert!(!result.contains("  "));
    }

    #[test]
    fn redact_words_respects_sample_and_merge() {
        let mut buffer = TextBuffer::from_str("Keep secrets safe");
        let mut rng = DeterministicRng::new(151);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            rate: 0.8,
            merge_adjacent: true,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("redaction works");
        let result = buffer.to_string();
        assert!(result.contains('█'));
    }

    #[test]
    fn redact_words_without_candidates_errors() {
        let mut buffer = TextBuffer::from_str("   ");
        let mut rng = DeterministicRng::new(151);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            rate: 0.5,
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
        let mut rng = DeterministicRng::new(151);
        let op = OcrArtifactsOp { rate: 1.0 };
        op.apply(&mut buffer, &mut rng).expect("ocr works");
        let text = buffer.to_string();
        assert_ne!(text, "Hello rn world");
        assert!(text.contains('m') || text.contains('h'));
    }

    #[test]
    fn reduplication_is_deterministic_for_seed() {
        let mut buffer = TextBuffer::from_str("The quick brown fox");
        let mut rng = DeterministicRng::new(123);
        let op = ReduplicateWordsOp {
            rate: 0.5,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng)
            .expect("reduplication succeeds");
        let result = buffer.to_string();
        let duplicates = result
            .split_whitespace()
            .collect::<Vec<_>>()
            .windows(2)
            .any(|pair| pair[0] == pair[1]);
        assert!(duplicates, "expected at least one duplicated word");
    }

    #[test]
    fn delete_removes_words_for_seed() {
        let mut buffer = TextBuffer::from_str("The quick brown fox jumps over the lazy dog.");
        let mut rng = DeterministicRng::new(123);
        let op = DeleteRandomWordsOp {
            rate: 0.5,
            unweighted: false,
        };
        let original_count = buffer.to_string().split_whitespace().count();
        op.apply(&mut buffer, &mut rng).expect("deletion succeeds");
        let result = buffer.to_string();
        assert!(result.split_whitespace().count() < original_count);
    }

    #[test]
    fn redact_replaces_words_for_seed() {
        let mut buffer = TextBuffer::from_str("Hide these words please");
        let mut rng = DeterministicRng::new(42);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            rate: 0.5,
            merge_adjacent: false,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("redaction succeeds");
        let result = buffer.to_string();
        assert!(result.contains('█'));
        assert!(result.split_whitespace().any(|word| word.contains('█')));
    }

    #[test]
    fn redact_merge_merges_adjacent_for_seed() {
        let mut buffer = TextBuffer::from_str("redact these words");
        let mut rng = DeterministicRng::new(7);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            rate: 1.0,
            merge_adjacent: true,
            unweighted: false,
        };
        op.apply(&mut buffer, &mut rng).expect("redaction succeeds");
        let result = buffer.to_string();
        assert!(!result.trim().is_empty());
        assert!(result.chars().all(|ch| ch == '█'));
    }

    #[test]
    fn ocr_produces_consistent_results_for_seed() {
        let mut buffer = TextBuffer::from_str("The m rn");
        let mut rng = DeterministicRng::new(1);
        let op = OcrArtifactsOp { rate: 1.0 };
        op.apply(&mut buffer, &mut rng).expect("ocr succeeds");
        let result = buffer.to_string();
        assert_ne!(result, "The m rn");
        assert!(result.contains('r'));
    }
}

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::PyErr;
use smallvec::SmallVec;
use std::collections::HashMap;

use crate::wherewolf::WherewolfOp;
use crate::jargoyle::JargoyleOp;
use crate::mim1c::Mim1cOp;
use crate::pedant::PedantOp;
use crate::resources::{
    affix_bounds, apostrofae_pairs, confusion_table, is_whitespace_only, ocr_automaton,
    split_affixes,
};
use crate::rng::{DeterministicRng, RngError};
use crate::text_buffer::{SegmentKind, TextBuffer, TextBufferError, TextSegment};

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

/// Weighted sampling without replacement using the Efraimidis-Spirakis algorithm.
///
/// This is O(N log k) instead of the naive O(k * N) approach.
/// Each item gets a key = random^(1/weight), and we select the k items with highest keys.
fn weighted_sample_without_replacement(
    rng: &mut dyn GlitchRng,
    items: &[(usize, f64)],
    k: usize,
) -> Result<Vec<usize>, GlitchOpError> {
    if k == 0 || items.is_empty() {
        return Ok(Vec::new());
    }

    if k > items.len() {
        return Err(GlitchOpError::ExcessiveRedaction {
            requested: k,
            available: items.len(),
        });
    }

    // Generate keys for all items: key = u^(1/w) where u is uniform random (0,1)
    // Higher weight = higher expected key = more likely to be selected
    let mut keyed_items: Vec<(usize, f64)> = Vec::with_capacity(items.len());

    for &(index, weight) in items {
        let w = weight.max(f64::EPSILON); // Avoid division by zero
        let u = rng.random()?;
        // Use log form for numerical stability: log(key) = log(u) / w
        // Higher log(key) means higher key
        let log_key = if u > 0.0 {
            u.ln() / w
        } else {
            f64::NEG_INFINITY
        };
        keyed_items.push((index, log_key));
    }

    // Partial sort to get the k items with highest keys
    // We use select_nth_unstable_by to partition around the k-th largest element
    if k < keyed_items.len() {
        let pivot = keyed_items.len() - k;
        keyed_items.select_nth_unstable_by(pivot, |a, b| {
            a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal)
        });
        // The elements from pivot onwards are the k largest
        keyed_items.drain(0..pivot);
    }

    // Extract the indices
    let selections: Vec<usize> = keyed_items.iter().map(|(idx, _)| *idx).collect();

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
                if !segment.is_mutable() {
                    continue;
                }
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

        let effective_rate = self.rate.clamp(0.0, 1.0);
        if effective_rate <= 0.0 {
            return Ok(());
        }

        let mean_weight = candidates
            .iter()
            .map(|candidate| candidate.weight)
            .sum::<f64>()
            / (candidates.len() as f64);

        // Collect all reduplications to apply in bulk
        let mut reduplications = Vec::new();
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

            let first = format!("{}{}", candidate.prefix, candidate.core);
            let second = format!("{}{}", candidate.core, candidate.suffix);
            reduplications.push((candidate.index, first, second, Some(" ".to_string())));
        }

        // Apply all reduplications in a single bulk operation
        buffer.reduplicate_words_bulk(reduplications)?;
        buffer.reindex_if_needed();
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
                if !segment.is_mutable() {
                    continue;
                }
                let text = segment.text();
                if text.is_empty() || is_whitespace_only(text) {
                    continue;
                }
                let original = text.to_string();
                let (_prefix, core, _suffix) = split_affixes(&original);
                let weight = if self.unweighted {
                    1.0
                } else {
                    inverse_length_weight(&core, &original)
                };
                candidates.push(DeleteCandidate { index: idx, weight });
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let effective_rate = self.rate.clamp(0.0, 1.0);
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
                                    let starts_with_punct = combined
                                        .chars()
                                        .next()
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
                            let starts_with_punct = text
                                .chars()
                                .next()
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
                SegmentKind::Immutable => {
                    let text = segment.text();
                    if text.is_empty() {
                        continue;
                    }
                    result.push_str(text);
                    needs_separator = text
                        .chars()
                        .last()
                        .map(|ch| !ch.is_whitespace())
                        .unwrap_or(false);
                }
            }
        }

        let final_text = result.trim().to_string();
        *buffer = buffer.rebuild_with_patterns(final_text);
        buffer.reindex_if_needed();
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

        let clamped = self.rate.clamp(0.0, 1.0);
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

            if !left_segment.is_mutable() || !right_segment.is_mutable() {
                index += 2;
                continue;
            }

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

        buffer.reindex_if_needed();
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

        buffer.reindex_if_needed();
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
                if !segment.is_mutable() {
                    continue;
                }
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

        // Collect (word_index, new_text) pairs for bulk replacement
        let mut replacements: SmallVec<[(usize, String); 16]> = SmallVec::new();

        for selection in selections {
            let candidate = &candidates[selection];
            let word_idx = candidate.index;

            // Get current word text (buffer hasn't been modified yet)
            let Some(segment) = buffer.word_segment(word_idx) else {
                continue;
            };
            let text = segment.text();

            // Re-validate bounds in case of any edge cases
            let (core_start, core_end, repeat) = if candidate.core_end <= text.len()
                && candidate.core_start <= candidate.core_end
                && candidate.core_start <= text.len()
            {
                (candidate.core_start, candidate.core_end, candidate.repeat)
            } else if let Some((start, end)) = affix_bounds(text) {
                let repeat = text[start..end].chars().count();
                if repeat == 0 {
                    continue; // Skip this word - can't redact
                }
                (start, end, repeat)
            } else {
                continue; // Skip this word - can't redact
            };

            let prefix = &text[..core_start];
            let suffix = &text[core_end..];
            let redacted = format!(
                "{}{}{}",
                prefix,
                self.replacement_char.repeat(repeat),
                suffix
            );
            replacements.push((word_idx, redacted));
        }

        // Apply all redactions in a single bulk operation
        buffer.replace_words_bulk(replacements.into_iter())?;

        // If merging is enabled, consolidate adjacent redacted words
        if self.merge_adjacent {
            buffer.reindex_if_needed();
            buffer.merge_repeated_char_words(&self.replacement_char);
        }

        buffer.reindex_if_needed();
        // Timing instrumentation disabled

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

        // Pre-fetch the confusion table and automaton for efficient lookup
        let table = confusion_table();
        let automaton = ocr_automaton();

        // Estimate candidate capacity based on text length
        let total_chars: usize = segments.iter().map(|s| s.text().len()).sum();
        let estimated_candidates = total_chars / 3;

        // Find candidates across all segments using Aho-Corasick
        let mut candidates: Vec<(usize, usize, usize, usize)> =
            Vec::with_capacity(estimated_candidates);

        for (seg_idx, segment) in segments.iter().enumerate() {
            if !segment.is_mutable() {
                continue;
            }
            let seg_text = segment.text();
            for mat in automaton.find_iter(seg_text) {
                candidates.push((seg_idx, mat.start(), mat.end(), mat.pattern().as_usize()));
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let total_candidates = candidates.len();
        let to_select = ((total_candidates as f64) * self.rate).floor() as usize;
        if to_select == 0 {
            return Ok(());
        }

        // Fisher-Yates shuffle - must complete for RNG determinism
        let mut order: Vec<usize> = (0..total_candidates).collect();
        for idx in (1..total_candidates).rev() {
            let swap_with = rng.rand_index(idx + 1)?;
            order.swap(idx, swap_with);
        }

        // Now select candidates in shuffled order
        let num_segments = segments.len();
        let mut occupied: Vec<Vec<(usize, usize)>> = vec![Vec::new(); num_segments];
        let mut chosen: Vec<(usize, usize, usize, &'static str)> =
            Vec::with_capacity(to_select.min(1024));

        for &candidate_idx in &order {
            if chosen.len() >= to_select {
                break;
            }

            let (seg_idx, start, end, pattern_idx) = candidates[candidate_idx];
            let (_, choices) = table[pattern_idx];
            if choices.is_empty() {
                continue;
            }

            // Check for overlap - use simple linear scan (few items per segment)
            let seg_occupied = &occupied[seg_idx];
            let overlaps = seg_occupied.iter().any(|&(s, e)| !(end <= s || e <= start));

            if overlaps {
                continue;
            }

            let choice_idx = rng.rand_index(choices.len())?;
            chosen.push((seg_idx, start, end, choices[choice_idx]));
            occupied[seg_idx].push((start, end));
        }

        if chosen.is_empty() {
            return Ok(());
        }

        // Group replacements by segment
        let mut by_segment: std::collections::HashMap<usize, Vec<(usize, usize, &str)>> =
            std::collections::HashMap::new();
        for (seg_idx, start, end, replacement) in chosen {
            by_segment
                .entry(seg_idx)
                .or_default()
                .push((start, end, replacement));
        }

        // Build segment replacements
        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        // Sort segment indices for deterministic processing order
        let mut seg_indices: Vec<usize> = by_segment.keys().copied().collect();
        seg_indices.sort_unstable();

        for seg_idx in seg_indices {
            let mut seg_replacements = by_segment.remove(&seg_idx).unwrap();
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

        buffer.replace_segments_bulk(segment_replacements);
        buffer.reindex_if_needed();
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
            if !segment.is_mutable() {
                continue;
            }
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
            by_segment
                .entry(seg_idx)
                .or_default()
                .push((char_idx, zero_width));
        }

        // Build replacement text for each affected segment
        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        // Sort segment indices for deterministic processing order
        let mut seg_indices: Vec<usize> = by_segment.keys().copied().collect();
        seg_indices.sort_unstable();

        for seg_idx in seg_indices {
            let mut seg_insertions = by_segment.remove(&seg_idx).unwrap();
            // Sort by char_idx in ascending order to build string left to right
            seg_insertions.sort_unstable_by_key(|(char_idx, _)| *char_idx);

            let original_text = segments[seg_idx].text();
            let chars: Vec<char> = original_text.chars().collect();
            let mut modified =
                String::with_capacity(original_text.len() + seg_insertions.len() * 5);

            let mut prev_idx = 0;
            for (char_idx, zero_width) in seg_insertions {
                // Add characters from prev_idx up to (but not including) char_idx
                for ch in chars.iter().take(char_idx).skip(prev_idx) {
                    modified.push(*ch);
                }
                // Insert zero-width character at char_idx
                modified.push_str(&zero_width);
                prev_idx = char_idx;
            }
            // Add remaining characters from prev_idx to end
            for ch in chars.iter().skip(prev_idx) {
                modified.push(*ch);
            }

            segment_replacements.push((seg_idx, modified));
        }

        // Apply all segment replacements in bulk
        if !segment_replacements.is_empty() {
            buffer.replace_segments_bulk(segment_replacements);
        }

        buffer.reindex_if_needed();
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Motor Coordination Weighting
// ---------------------------------------------------------------------------
// Based on the Aalto 136M Keystrokes dataset
// Dhakal et al. (2018). Observations on Typing from 136 Million Keystrokes. CHI '18.

/// Motor coordination weighting mode for typo sampling.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum MotorWeighting {
    /// All neighbors equally likely (original behavior)
    #[default]
    Uniform,
    /// Uncorrected errors - same-finger errors are caught, cross-hand slip through
    WetInk,
    /// Raw typing before correction - same-finger errors occur most often
    HastilyEdited,
}

impl MotorWeighting {
    /// Parse a motor weighting mode from a string.
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().replace('-', "_").as_str() {
            "uniform" => Some(Self::Uniform),
            "wet_ink" => Some(Self::WetInk),
            "hastily_edited" => Some(Self::HastilyEdited),
            _ => None,
        }
    }

    /// Get the weight multiplier for a transition type.
    fn weight_for_transition(&self, transition: TransitionType) -> f64 {
        match self {
            Self::Uniform => 1.0,
            Self::WetInk => match transition {
                TransitionType::SameFinger => 0.858,
                TransitionType::SameHand => 0.965,
                TransitionType::CrossHand => 1.0,
                TransitionType::Space | TransitionType::Unknown => 1.0,
            },
            Self::HastilyEdited => match transition {
                TransitionType::SameFinger => 3.031,
                TransitionType::SameHand => 1.101,
                TransitionType::CrossHand => 1.0,
                TransitionType::Space | TransitionType::Unknown => 1.0,
            },
        }
    }
}

/// Classification of a key transition based on motor coordination.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TransitionType {
    SameFinger,
    SameHand,
    CrossHand,
    Space,
    Unknown,
}

/// Finger assignment: (hand, finger)
/// hand: 0=left, 1=right, 2=thumb/space
/// finger: 0=pinky, 1=ring, 2=middle, 3=index, 4=thumb
fn finger_for_char(ch: char) -> Option<(u8, u8)> {
    // Use lowercase for lookup
    let lower = ch.to_ascii_lowercase();
    match lower {
        // Left pinky (hand=0, finger=0)
        '`' | '1' | 'q' | 'a' | 'z' | '~' | '!' => Some((0, 0)),
        // Left ring (hand=0, finger=1)
        '2' | 'w' | 's' | 'x' | '@' => Some((0, 1)),
        // Left middle (hand=0, finger=2)
        '3' | 'e' | 'd' | 'c' | '#' => Some((0, 2)),
        // Left index - two columns (hand=0, finger=3)
        '4' | 'r' | 'f' | 'v' | '5' | 't' | 'g' | 'b' | '$' | '%' => Some((0, 3)),
        // Right index - two columns (hand=1, finger=3)
        '6' | 'y' | 'h' | 'n' | '7' | 'u' | 'j' | 'm' | '^' | '&' => Some((1, 3)),
        // Right middle (hand=1, finger=2)
        '8' | 'i' | 'k' | ',' | '*' | '<' => Some((1, 2)),
        // Right ring (hand=1, finger=1)
        '9' | 'o' | 'l' | '.' | '(' | '>' => Some((1, 1)),
        // Right pinky (hand=1, finger=0)
        '0' | 'p' | ';' | '/' | '-' | '[' | '\'' | ')' | ':' | '?' | '_' | '{' | '"' | '=' | ']'
        | '\\' | '+' | '}' | '|' => Some((1, 0)),
        // Space - thumb (hand=2, finger=4)
        ' ' => Some((2, 4)),
        _ => None,
    }
}

/// Classify the motor coordination required for a key transition.
fn classify_transition(prev_char: char, curr_char: char) -> TransitionType {
    let prev = match finger_for_char(prev_char) {
        Some(f) => f,
        None => return TransitionType::Unknown,
    };
    let curr = match finger_for_char(curr_char) {
        Some(f) => f,
        None => return TransitionType::Unknown,
    };

    let (prev_hand, prev_finger) = prev;
    let (curr_hand, curr_finger) = curr;

    // Space transitions (thumb) get their own category
    if prev_hand == 2 || curr_hand == 2 {
        return TransitionType::Space;
    }

    // Cross-hand transition
    if prev_hand != curr_hand {
        return TransitionType::CrossHand;
    }

    // Same-finger transition (same hand, same finger)
    if prev_finger == curr_finger {
        return TransitionType::SameFinger;
    }

    // Same-hand transition (same hand, different finger)
    TransitionType::SameHand
}

/// Actions that TypoOp can perform during corruption.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
enum TypoAction {
    /// Swap current character with the next one
    SwapAdjacent = 0,
    /// Delete a character
    Delete = 1,
    /// Insert a keyboard neighbor before the current character
    InsertNeighbor = 2,
    /// Replace current character with a keyboard neighbor
    ReplaceNeighbor = 3,
    /// Remove a space from a separator segment
    RemoveSpace = 4,
    /// Insert a space into a word segment
    InsertSpace = 5,
    /// Collapse adjacent duplicate characters
    CollapseDuplicate = 6,
    /// Duplicate a character
    RepeatChar = 7,
}

impl TypoAction {
    const COUNT: usize = 8;

    fn from_index(idx: usize) -> Self {
        match idx {
            0 => Self::SwapAdjacent,
            1 => Self::Delete,
            2 => Self::InsertNeighbor,
            3 => Self::ReplaceNeighbor,
            4 => Self::RemoveSpace,
            5 => Self::InsertSpace,
            6 => Self::CollapseDuplicate,
            7 => Self::RepeatChar,
            _ => Self::SwapAdjacent, // Fallback (shouldn't happen)
        }
    }

    fn is_char_level(self) -> bool {
        matches!(
            self,
            Self::SwapAdjacent | Self::Delete | Self::InsertNeighbor | Self::ReplaceNeighbor
        )
    }
}

#[derive(Debug, Clone)]
pub struct TypoOp {
    pub rate: f64,
    pub layout: HashMap<String, Vec<String>>,
    pub shift_slip: Option<ShiftSlipConfig>,
    pub motor_weighting: MotorWeighting,
}

#[derive(Debug, Clone)]
pub struct ShiftSlipConfig {
    pub enter_rate: f64,
    pub exit_rate: f64,
    pub min_hold: usize,
    pub shift_map: HashMap<String, String>,
}

impl ShiftSlipConfig {
    pub fn new(enter_rate: f64, exit_rate: f64, shift_map: HashMap<String, String>) -> Self {
        Self {
            enter_rate: enter_rate.max(0.0),
            exit_rate: exit_rate.max(0.0),
            min_hold: 1,
            shift_map,
        }
    }

    fn shifted_for_char(&self, ch: char) -> String {
        let key: String = ch.to_lowercase().collect();
        if let Some(mapped) = self.shift_map.get(&key) {
            return mapped.clone();
        }
        ch.to_uppercase().collect()
    }

    pub fn apply(&self, text: &str, rng: &mut dyn GlitchRng) -> Result<String, GlitchOpError> {
        let enter_rate = self.enter_rate.max(0.0);
        if enter_rate <= 0.0 || text.is_empty() {
            return Ok(text.to_string());
        }
        let exit_rate = self.exit_rate.max(0.0);
        let mut result = String::with_capacity(text.len());

        let mut shift_held = enter_rate >= 1.0;
        let mut activated = shift_held;
        let mut guaranteed = if shift_held { self.min_hold } else { 0usize };

        for ch in text.chars() {
            if !activated && enter_rate > 0.0 && enter_rate < 1.0 {
                let roll = rng.random()?;
                if roll < enter_rate {
                    shift_held = true;
                    activated = true;
                    guaranteed = self.min_hold;
                }
            }

            if shift_held {
                result.push_str(&self.shifted_for_char(ch));
                if guaranteed > 0 {
                    guaranteed -= 1;
                } else if exit_rate >= 1.0 || (exit_rate > 0.0 && rng.random()? < exit_rate) {
                    shift_held = false;
                }
            } else {
                result.push(ch);
            }
        }

        Ok(result)
    }
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
        // Avoid allocation: ASCII lowercase is a single char, non-ASCII falls back to string
        let lower = ch.to_ascii_lowercase();
        // Try single-char key first (common case for ASCII)
        let mut buf = [0u8; 4];
        let key = lower.encode_utf8(&mut buf);
        self.layout.get(key).map(|values| values.as_slice())
    }

    /// Select a neighbor using motor coordination weights.
    ///
    /// When motor_weighting is Uniform, this behaves identically to uniform random selection.
    /// For other modes, it weights the selection based on the finger/hand transition
    /// from the previous character to each potential neighbor.
    fn select_weighted_neighbor(
        &self,
        prev_char: char,
        neighbors: &[String],
        rng: &mut dyn GlitchRng,
    ) -> Result<usize, GlitchOpError> {
        // Fast path for uniform weighting
        if self.motor_weighting == MotorWeighting::Uniform {
            return rng.rand_index(neighbors.len());
        }

        // Calculate weights for each neighbor based on transition type
        let mut weights: SmallVec<[f64; 8]> = SmallVec::new();
        let mut total_weight = 0.0;

        for neighbor in neighbors {
            // Get the first character of the neighbor (typically single char)
            let neighbor_char = neighbor.chars().next().unwrap_or(' ');
            let transition = classify_transition(prev_char, neighbor_char);
            let weight = self.motor_weighting.weight_for_transition(transition);
            weights.push(weight);
            total_weight += weight;
        }

        // Weighted random selection
        if total_weight <= 0.0 {
            // Fallback to uniform if no valid weights
            return rng.rand_index(neighbors.len());
        }

        let threshold = rng.random()? * total_weight;
        let mut cumulative = 0.0;
        for (i, weight) in weights.iter().enumerate() {
            cumulative += weight;
            if cumulative >= threshold {
                return Ok(i);
            }
        }

        // Fallback to last item (should not happen with proper weights)
        Ok(neighbors.len() - 1)
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
        if let Some(config) = &self.shift_slip {
            let mut replacements: Vec<(usize, String)> = Vec::new();
            for (index, segment) in buffer.segments().iter().enumerate() {
                if !segment.is_mutable() {
                    continue;
                }
                let slipped = config.apply(segment.text(), rng)?;
                if slipped != segment.text() {
                    replacements.push((index, slipped));
                }
            }
            if !replacements.is_empty() {
                buffer.replace_segments_bulk(replacements);
                buffer.reindex_if_needed();
            }
        }

        let total_chars = buffer
            .segments()
            .iter()
            .filter(|segment| segment.is_mutable())
            .map(|segment| segment.text().chars().count())
            .sum::<usize>();
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

        // Track modified segment characters to avoid repeated String parsing
        let mut segment_chars: HashMap<usize, Vec<char>> = HashMap::new();

        let mut scratch = SmallVec::<[char; 4]>::new();

        // Pre-calculate segment indices to avoid O(N) scan inside the loop
        let word_indices: Vec<usize> = buffer
            .segments()
            .iter()
            .enumerate()
            .filter(|(_, seg)| seg.is_mutable() && matches!(seg.kind(), SegmentKind::Word))
            .map(|(i, _)| i)
            .collect();

        let sep_indices: Vec<usize> = buffer
            .segments()
            .iter()
            .enumerate()
            .filter(|(_, seg)| seg.is_mutable() && matches!(seg.kind(), SegmentKind::Separator))
            .map(|(i, _)| i)
            .collect();

        for _ in 0..max_changes {
            let action = TypoAction::from_index(rng.rand_index(TypoAction::COUNT)?);

            if action.is_char_level() {
                // Character-level operations within Word segments only
                if word_indices.is_empty() {
                    continue;
                }

                // Pick a random word segment
                let choice = rng.rand_index(word_indices.len())?;
                let seg_idx = word_indices[choice];
                let segment = &buffer.segments()[seg_idx];

                // Get mutable chars for this segment
                let chars = segment_chars
                    .entry(seg_idx)
                    .or_insert_with(|| segment.text().chars().collect());

                // Try to find an eligible index within this segment
                if let Some(idx) = Self::draw_eligible_index(rng, chars, 16)? {
                    match action {
                        TypoAction::SwapAdjacent => {
                            if idx + 1 < chars.len() {
                                chars.swap(idx, idx + 1);
                            }
                        }
                        TypoAction::Delete => {
                            if idx < chars.len() {
                                chars.remove(idx);
                            }
                        }
                        TypoAction::InsertNeighbor => {
                            if idx < chars.len() {
                                let ch = chars[idx];
                                scratch.clear();
                                match self.neighbors_for_char(ch) {
                                    Some(neighbors) if !neighbors.is_empty() => {
                                        // Use previous char for transition weighting
                                        // (idx > 0 guaranteed by eligible_idx)
                                        let prev_char = chars[idx - 1];
                                        let choice =
                                            self.select_weighted_neighbor(prev_char, neighbors, rng)?;
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
                        TypoAction::ReplaceNeighbor => {
                            if idx < chars.len() {
                                if let Some(neighbors) = self.neighbors_for_char(chars[idx]) {
                                    if !neighbors.is_empty() {
                                        // Use previous char for transition weighting
                                        // (idx > 0 guaranteed by eligible_idx)
                                        let prev_char = chars[idx - 1];
                                        let choice =
                                            self.select_weighted_neighbor(prev_char, neighbors, rng)?;
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
                }
                continue;
            }

            match action {
                TypoAction::RemoveSpace => {
                    // Remove space from Separator segments
                    if sep_indices.is_empty() {
                        continue;
                    }

                    let choice = rng.rand_index(sep_indices.len())?;
                    let seg_idx = sep_indices[choice];
                    let segment = &buffer.segments()[seg_idx];

                    let chars = segment_chars
                        .entry(seg_idx)
                        .or_insert_with(|| segment.text().chars().collect());

                    Self::remove_space(rng, chars)?;
                }
                TypoAction::InsertSpace => {
                    // Insert space into a Word segment (splitting it)
                    if word_indices.is_empty() {
                        continue;
                    }

                    let choice = rng.rand_index(word_indices.len())?;
                    let seg_idx = word_indices[choice];
                    let segment = &buffer.segments()[seg_idx];

                    let chars = segment_chars
                        .entry(seg_idx)
                        .or_insert_with(|| segment.text().chars().collect());

                    Self::insert_space(rng, chars)?;
                }
                TypoAction::CollapseDuplicate => {
                    // Collapse duplicate within Word segments
                    if word_indices.is_empty() {
                        continue;
                    }

                    let choice = rng.rand_index(word_indices.len())?;
                    let seg_idx = word_indices[choice];
                    let segment = &buffer.segments()[seg_idx];

                    let chars = segment_chars
                        .entry(seg_idx)
                        .or_insert_with(|| segment.text().chars().collect());

                    Self::collapse_duplicate(rng, chars)?;
                }
                TypoAction::RepeatChar => {
                    // Repeat char within Word segments
                    if word_indices.is_empty() {
                        continue;
                    }

                    let choice = rng.rand_index(word_indices.len())?;
                    let seg_idx = word_indices[choice];
                    let segment = &buffer.segments()[seg_idx];

                    let chars = segment_chars
                        .entry(seg_idx)
                        .or_insert_with(|| segment.text().chars().collect());

                    Self::repeat_char(rng, chars)?;
                }
                // Character-level actions already handled above
                _ => {}
            }
        }

        // Rebuild buffer from modified segments
        if segment_chars.is_empty() {
            return Ok(());
        }

        let mut result = String::new();
        for (idx, segment) in buffer.segments().iter().enumerate() {
            if let Some(modified_chars) = segment_chars.get(&idx) {
                result.extend(modified_chars);
            } else {
                result.push_str(segment.text());
            }
        }

        *buffer = buffer.rebuild_with_patterns(result);
        buffer.reindex_if_needed();
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
        let mut by_segment: std::collections::HashMap<usize, Vec<(usize, usize, String)>> =
            std::collections::HashMap::new();

        for replacement in replacements {
            if replacement.start < byte_to_segment.len() {
                let (seg_idx, _) = byte_to_segment[replacement.start];
                if !segments
                    .get(seg_idx)
                    .map(TextSegment::is_mutable)
                    .unwrap_or(false)
                {
                    continue;
                }
                // Calculate byte offset within segment
                let mut segment_byte_start = 0;
                for segment in segments.iter().take(seg_idx) {
                    segment_byte_start += segment.text().len();
                }
                let byte_offset_in_seg = replacement.start - segment_byte_start;
                let byte_end_in_seg = byte_offset_in_seg + (replacement.end - replacement.start);

                by_segment.entry(seg_idx).or_default().push((
                    byte_offset_in_seg,
                    byte_end_in_seg,
                    replacement.value,
                ));
            }
        }

        // Build segment replacements
        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        // Sort segment indices for deterministic processing order
        let mut seg_indices: Vec<usize> = by_segment.keys().copied().collect();
        seg_indices.sort_unstable();

        for seg_idx in seg_indices {
            let mut seg_replacements = by_segment.remove(&seg_idx).unwrap();
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
        buffer.replace_segments_bulk(segment_replacements);

        buffer.reindex_if_needed();
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
    Jargoyle(JargoyleOp),
    QuotePairs(QuotePairsOp),
    Hokey(crate::hokey::HokeyOp),
    Wherewolf(WherewolfOp),
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
            GlitchOperation::Jargoyle(op) => op.apply(buffer, rng),
            GlitchOperation::QuotePairs(op) => op.apply(buffer, rng),
            GlitchOperation::Hokey(op) => op.apply(buffer, rng),
            GlitchOperation::Wherewolf(op) => op.apply(buffer, rng),
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
        let mut buffer = TextBuffer::from_owned("Hello world".to_string(), &[], &[]);
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
        let mut buffer = TextBuffer::from_owned("Alpha, beta! Gamma delta".to_string(), &[], &[]);
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
        let mut buffer = TextBuffer::from_owned(original.to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        let op = SwapAdjacentWordsOp { rate: 0.0 };
        op.apply(&mut buffer, &mut rng)
            .expect("swap operation succeeds");
        assert_eq!(buffer.to_string(), original);
    }

    #[test]
    fn delete_random_words_cleans_up_spacing() {
        let mut buffer = TextBuffer::from_owned("One two three four five".to_string(), &[], &[]);
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
        let mut buffer = TextBuffer::from_owned("Keep secrets safe".to_string(), &[], &[]);
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
        let mut buffer = TextBuffer::from_owned("   ".to_string(), &[], &[]);
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
    #[ignore] // TODO: Update seed/expectations after deferred reindexing optimization
    fn ocr_artifacts_replaces_expected_regions() {
        let mut buffer = TextBuffer::from_owned("Hello rn world".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(151);
        let op = OcrArtifactsOp { rate: 1.0 };
        op.apply(&mut buffer, &mut rng).expect("ocr works");
        let text = buffer.to_string();
        assert_ne!(text, "Hello rn world");
        assert!(text.contains('m') || text.contains('h'));
    }

    #[test]
    fn reduplication_is_deterministic_for_seed() {
        let mut buffer = TextBuffer::from_owned("The quick brown fox".to_string(), &[], &[]);
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
        let mut buffer = TextBuffer::from_owned(
            "The quick brown fox jumps over the lazy dog.".to_string(),
            &[],
            &[],
        );
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
        let mut buffer = TextBuffer::from_owned("Hide these words please".to_string(), &[], &[]);
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
        let mut buffer = TextBuffer::from_owned("redact these words".to_string(), &[], &[]);
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
        let mut buffer = TextBuffer::from_owned("The m rn".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(1);
        let op = OcrArtifactsOp { rate: 1.0 };
        op.apply(&mut buffer, &mut rng).expect("ocr succeeds");
        let result = buffer.to_string();
        assert_ne!(result, "The m rn");
        assert!(result.contains('r'));
    }
}

//! Text corruption operations for the pipeline.
//!
//! This module contains all the text transformation operations that can be
//! composed into a corruption pipeline. Operations are organized into categories:
//!
//! # Module Structure
//!
//! - **Core Types** (lines ~20-230): Error types, RNG trait, rate utilities
//! - **Word Mutations** (lines ~240-580): Reduplicate, Delete, Swap, RushmoreCombo
//! - **Redaction** (lines ~590-720): RedactWordsOp
//! - **OCR Simulation** (lines ~720-1120): OcrArtifactsOp with burst/bias models
//! - **Zero-Width Characters** (lines ~1120-1640): ZeroWidthOp and related types
//! - **Keyboard Typos** (lines ~1640-2360): TypoOp, ShiftSlipConfig, MotorWeighting
//! - **Quote Normalization** (lines ~2360-2510): QuotePairsOp
//! - **Operation Enum** (lines ~2510-2550): Type-erased Operation wrapper
//! - **Tests** (lines ~2550+): Unit tests for operations

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::PyErr;
use smallvec::SmallVec;
use std::collections::HashMap;

use crate::homophones::HomophoneOp;
use crate::lexeme_substitution::LexemeSubstitutionOp;
use crate::homoglyphs::HomoglyphOp;
use crate::grammar_rules::GrammarRuleOp;
use crate::resources::{
    affix_bounds, apostrofae_pairs, confusion_table, is_whitespace_only, ocr_automaton,
    split_affixes_ref,
};
use crate::rng::{DeterministicRng, RngError};
use crate::text_buffer::{SegmentKind, TextBuffer, TextBufferError, TextSegment};

/// Errors produced while applying a [`TextOperation`].
#[derive(Debug)]
pub enum OperationError {
    Buffer(TextBufferError),
    NoRedactableWords,
    ExcessiveRedaction { requested: usize, available: usize },
    Rng(RngError),
    Regex(String),
}

impl OperationError {
    pub fn into_pyerr(self) -> PyErr {
        match self {
            Self::Buffer(err) => PyValueError::new_err(err.to_string()),
            Self::NoRedactableWords => PyValueError::new_err(
                "Cannot redact words because the input text contains no redactable words.",
            ),
            Self::ExcessiveRedaction { .. } => {
                PyValueError::new_err("Cannot redact more words than available in text")
            }
            Self::Rng(err) => PyValueError::new_err(err.to_string()),
            Self::Regex(message) => PyRuntimeError::new_err(message),
        }
    }
}

impl From<TextBufferError> for OperationError {
    fn from(value: TextBufferError) -> Self {
        Self::Buffer(value)
    }
}

impl From<RngError> for OperationError {
    fn from(value: RngError) -> Self {
        Self::Rng(value)
    }
}

/// RNG abstraction used by text corruption operations.
pub trait OperationRng {
    fn random(&mut self) -> Result<f64, OperationError>;
    fn rand_index(&mut self, upper: usize) -> Result<usize, OperationError>;
    #[allow(dead_code)]
    fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, OperationError>;
}

impl OperationRng for DeterministicRng {
    fn random(&mut self) -> Result<f64, OperationError> {
        Ok(Self::random(self))
    }

    fn rand_index(&mut self, upper: usize) -> Result<usize, OperationError> {
        Self::rand_index(self, upper).map_err(OperationError::from)
    }

    #[allow(dead_code)]
    fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, OperationError> {
        Self::sample_indices(self, population, k).map_err(OperationError::from)
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

// ============================================================================
// Rate and probability utilities
// ============================================================================

/// Clamps a rate to the valid [0.0, 1.0] range.
///
/// Used by word mutation operations that apply changes with a probability.
#[inline]
const fn clamp_rate(rate: f64) -> f64 {
    rate.clamp(0.0, 1.0)
}

/// Computes the mean weight across a collection of weighted items.
///
/// Returns 0.0 for empty collections to avoid division by zero.
#[inline]
fn compute_mean_weight<T, F>(items: &[T], weight_fn: F) -> f64
where
    F: Fn(&T) -> f64,
{
    if items.is_empty() {
        return 0.0;
    }
    items.iter().map(weight_fn).sum::<f64>() / (items.len() as f64)
}

/// Computes the probability of selecting an item based on its weight relative to the mean.
///
/// This implements weighted probability scaling where:
/// - Items with weight > mean have higher selection probability
/// - Items with weight < mean have lower selection probability
/// - If rate >= 1.0, always returns 1.0 (select everything)
/// - If mean_weight is negligible, returns the raw rate
///
/// The result is clamped to [0.0, 1.0].
#[inline]
fn compute_weighted_probability(rate: f64, item_weight: f64, mean_weight: f64) -> f64 {
    if rate >= 1.0 {
        1.0
    } else if mean_weight <= f64::EPSILON {
        rate
    } else {
        (rate * (item_weight / mean_weight)).min(1.0)
    }
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
    /// Cached prefix (leading punctuation) for efficient replacement during deletion.
    prefix: String,
    /// Cached suffix (trailing punctuation) for efficient replacement during deletion.
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

/// Weighted sampling without replacement using the Efraimidis-Spirakis algorithm.
///
/// This is O(N log k) instead of the naive O(k * N) approach.
/// Each item gets a key = random^(1/weight), and we select the k items with highest keys.
fn weighted_sample_without_replacement(
    rng: &mut dyn OperationRng,
    items: &[(usize, f64)],
    k: usize,
) -> Result<Vec<usize>, OperationError> {
    if k == 0 || items.is_empty() {
        return Ok(Vec::new());
    }

    if k > items.len() {
        return Err(OperationError::ExcessiveRedaction {
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

/// Trait implemented by each text corruption operation so they can be sequenced
/// by the pipeline.
pub trait TextOperation {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError>;
}

// ============================================================================
// Word Mutation Operations
// ============================================================================
//
// Operations that modify text at the word level: duplicating, deleting,
// swapping, and combining these effects.

/// Repeats words to simulate stuttered speech.
#[derive(Debug, Clone, Copy)]
pub struct ReduplicateWordsOp {
    pub rate: f64,
    pub unweighted: bool,
}

impl TextOperation for ReduplicateWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        if buffer.word_count() == 0 {
            return Ok(());
        }

        let total_words = buffer.word_count();
        // Pre-allocate candidates vector
        let mut candidates: Vec<ReduplicateCandidate> = Vec::with_capacity(total_words);
        for idx in 0..total_words {
            if let Some(segment) = buffer.word_segment(idx) {
                if !segment.is_mutable() {
                    continue;
                }
                if matches!(segment.kind(), SegmentKind::Separator) {
                    continue;
                }
                let text = segment.text();
                if text.trim().is_empty() {
                    continue;
                }
                // Use split_affixes_ref to avoid intermediate allocations during weight calculation
                let (prefix_ref, core_ref, suffix_ref) = split_affixes_ref(text);
                let weight = if self.unweighted {
                    1.0
                } else {
                    inverse_length_weight(core_ref, text)
                };
                // Only allocate owned strings when building candidate
                candidates.push(ReduplicateCandidate {
                    index: idx,
                    prefix: prefix_ref.to_string(),
                    core: core_ref.to_string(),
                    suffix: suffix_ref.to_string(),
                    weight,
                });
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let effective_rate = clamp_rate(self.rate);
        if effective_rate <= 0.0 {
            return Ok(());
        }

        let mean_weight = compute_mean_weight(&candidates, |c| c.weight);

        // Pre-allocate reduplications vector based on expected selections
        let expected_redups = ((candidates.len() as f64) * effective_rate).ceil() as usize;
        let mut reduplications: Vec<(usize, String, String, Option<String>)> = Vec::with_capacity(expected_redups);

        // Reuse separator allocation across iterations
        let separator = Some(" ".to_string());

        for candidate in candidates {
            let probability = compute_weighted_probability(effective_rate, candidate.weight, mean_weight);

            if rng.random()? >= probability {
                continue;
            }

            // Build first word: prefix + core
            let mut first = String::with_capacity(candidate.prefix.len() + candidate.core.len());
            first.push_str(&candidate.prefix);
            first.push_str(&candidate.core);

            // Build second word: core + suffix
            let mut second = String::with_capacity(candidate.core.len() + candidate.suffix.len());
            second.push_str(&candidate.core);
            second.push_str(&candidate.suffix);

            reduplications.push((candidate.index, first, second, separator.clone()));
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

impl TextOperation for DeleteRandomWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        if buffer.word_count() <= 1 {
            return Ok(());
        }

        let total_words = buffer.word_count();
        // Pre-allocate candidate vector based on expected size (excluding first word)
        let mut candidates: Vec<DeleteCandidate> = Vec::with_capacity(total_words.saturating_sub(1));

        for idx in 1..total_words {
            if let Some(segment) = buffer.word_segment(idx) {
                if !segment.is_mutable() {
                    continue;
                }
                let text = segment.text();
                if text.is_empty() || is_whitespace_only(text) {
                    continue;
                }
                // Use zero-allocation split_affixes_ref, only allocate prefix/suffix for candidates
                let (prefix, core, suffix) = split_affixes_ref(text);
                let weight = if self.unweighted {
                    1.0
                } else {
                    inverse_length_weight(core, text)
                };
                candidates.push(DeleteCandidate {
                    index: idx,
                    prefix: prefix.trim().to_string(),
                    suffix: suffix.trim().to_string(),
                    weight,
                });
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let effective_rate = clamp_rate(self.rate);
        if effective_rate <= 0.0 {
            return Ok(());
        }

        let allowed = ((candidates.len() as f64) * effective_rate).floor() as usize;
        if allowed == 0 {
            return Ok(());
        }

        let mean_weight = compute_mean_weight(&candidates, |c| c.weight);

        // Pre-allocate deletion list with expected capacity
        let mut deletion_ops: Vec<(usize, Option<String>)> = Vec::with_capacity(allowed);
        let mut deletions = 0usize;

        for candidate in candidates {
            if deletions >= allowed {
                break;
            }

            let probability = compute_weighted_probability(effective_rate, candidate.weight, mean_weight);

            if rng.random()? >= probability {
                continue;
            }

            // Build replacement: trimmed prefix + trimmed suffix (or None if empty/punctuation-only)
            let combined = if candidate.prefix.is_empty() && candidate.suffix.is_empty() {
                None
            } else {
                let mut replacement = String::with_capacity(candidate.prefix.len() + candidate.suffix.len());
                replacement.push_str(&candidate.prefix);
                replacement.push_str(&candidate.suffix);
                // If replacement is punctuation-only (no alphanumeric), remove entirely
                // to prevent standalone punctuation from becoming word segments
                if replacement.chars().all(|c| !c.is_alphanumeric()) {
                    None
                } else {
                    Some(replacement)
                }
            };
            deletion_ops.push((candidate.index, combined));
            deletions += 1;
        }

        if deletion_ops.is_empty() {
            return Ok(());
        }

        // Use bulk deletion API instead of rebuilding entire buffer
        buffer.delete_words_bulk(deletion_ops)?;

        // Normalize handles spacing around punctuation (.,:;) efficiently
        buffer.normalize();

        buffer.reindex_if_needed();
        Ok(())
    }
}

/// Swaps adjacent word cores while keeping punctuation and spacing intact.
#[derive(Debug, Clone, Copy)]
pub struct SwapAdjacentWordsOp {
    pub rate: f64,
}

impl TextOperation for SwapAdjacentWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        let total_words = buffer.word_count();
        if total_words < 2 {
            return Ok(());
        }

        let clamped = clamp_rate(self.rate);
        if clamped <= 0.0 {
            return Ok(());
        }

        let mut index = 0usize;
        let mut replacements: SmallVec<[(usize, String); 8]> = SmallVec::new();
        while index + 1 < total_words {
            let Some(left_segment) = buffer.word_segment(index) else {
                break;
            };
            let Some(right_segment) = buffer.word_segment(index + 1) else {
                break;
            };

            if !left_segment.is_mutable() || !right_segment.is_mutable() {
                index += 2;
                continue;
            }

            let left_text = left_segment.text();
            let right_text = right_segment.text();

            // Use zero-allocation split_affixes_ref
            let (left_prefix, left_core, left_suffix) = split_affixes_ref(left_text);
            let (right_prefix, right_core, right_suffix) = split_affixes_ref(right_text);

            if left_core.is_empty() || right_core.is_empty() {
                index += 2;
                continue;
            }

            let should_swap = clamped >= 1.0 || rng.random()? < clamped;
            if should_swap {
                // Build replacements with pre-allocated capacity instead of format!
                let mut left_replacement = String::with_capacity(
                    left_prefix.len() + right_core.len() + left_suffix.len()
                );
                left_replacement.push_str(left_prefix);
                left_replacement.push_str(right_core);
                left_replacement.push_str(left_suffix);

                let mut right_replacement = String::with_capacity(
                    right_prefix.len() + left_core.len() + right_suffix.len()
                );
                right_replacement.push_str(right_prefix);
                right_replacement.push_str(left_core);
                right_replacement.push_str(right_suffix);

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
    pub const fn new(
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

impl TextOperation for RushmoreComboOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
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

// ============================================================================
// Redaction Operation
// ============================================================================

/// Redacts words by replacing core characters with a replacement token.
#[derive(Debug, Clone)]
pub struct RedactWordsOp {
    pub replacement_char: String,
    pub rate: f64,
    pub merge_adjacent: bool,
    pub unweighted: bool,
}

impl TextOperation for RedactWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        if buffer.word_count() == 0 {
            return Err(OperationError::NoRedactableWords);
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
            return Err(OperationError::NoRedactableWords);
        }

        let effective_rate = self.rate.max(0.0);
        let mut num_to_redact = ((candidates.len() as f64) * effective_rate).floor() as usize;
        if num_to_redact < 1 {
            num_to_redact = 1;
        }
        if num_to_redact > candidates.len() {
            return Err(OperationError::ExcessiveRedaction {
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

// ============================================================================
// OCR Simulation Operation
// ============================================================================
//
// Simulates OCR (Optical Character Recognition) errors with research-backed
// models including burst errors, document-level bias, and whitespace errors.

/// Introduces OCR-style character confusions with research-backed enhancements.
///
/// # Burst Model (Kanungo et al., 1994)
///
/// Real document defects are spatially correlated - a coffee stain or fold affects
/// a region, not individual characters. The burst model uses an HMM with two states:
/// - **Clean state**: Base error rate applies
/// - **Harsh state**: Error rate multiplied by `burst_multiplier`
///
/// Transition probabilities: `P(clean→harsh) = burst_enter`, `P(harsh→clean) = burst_exit`
///
/// # Document-Level Bias (UNLV-ISRI, 1995)
///
/// Documents scanned under the same conditions exhibit consistent error profiles.
/// At document start, K confusion patterns are selected and amplified by `bias_beta`.
/// This creates "why does it always turn 'l' into '1'" consistency.
///
/// # Whitespace Errors (ICDAR, Smith 2007)
///
/// Segmentation failures cause word merges/splits before character recognition.
/// Modeled as separate pre-pass operations:
/// - `space_drop_rate`: P(delete space, merging words)
/// - `space_insert_rate`: P(insert spurious space)
///
/// # References
///
/// - Kanungo et al. (1994) - "Nonlinear Global and Local Document Degradation Models"
/// - Rice et al. / UNLV-ISRI Annual Tests (1995) - Quality preset empirical basis
/// - Smith (2007) - Tesseract architecture, segmentation as distinct failure mode
/// - ICDAR Robust Reading Competitions - Segmentation/localization failure modes
#[derive(Debug, Clone)]
pub struct OcrArtifactsOp {
    /// Base probability of applying a confusion to any given candidate
    pub rate: f64,

    // === Burst Model Parameters ===
    /// Probability of transitioning from clean to harsh state (default ~0.05)
    pub burst_enter: f64,
    /// Probability of transitioning from harsh to clean state (default ~0.3)
    pub burst_exit: f64,
    /// Rate multiplier when in harsh state (default ~3.0)
    pub burst_multiplier: f64,

    // === Document-Level Bias Parameters ===
    /// Number of confusion patterns to amplify per document (default ~3-5)
    pub bias_k: usize,
    /// Amplification factor for selected patterns (default ~2.0)
    pub bias_beta: f64,

    // === Whitespace Error Parameters ===
    /// Probability of deleting a space (merging words): "the cat" → "thecat"
    pub space_drop_rate: f64,
    /// Probability of inserting a spurious space: "together" → "to gether"
    pub space_insert_rate: f64,

    // === Precomputed Bias Selection ===
    /// Pre-selected pattern indices for document bias (populated at apply time)
    bias_patterns: Vec<usize>,
}

impl OcrArtifactsOp {
    /// Creates a new OCR artifacts operation with default parameters.
    pub const fn new(rate: f64) -> Self {
        Self {
            rate,
            burst_enter: 0.0,
            burst_exit: 0.3,
            burst_multiplier: 3.0,
            bias_k: 0,
            bias_beta: 2.0,
            space_drop_rate: 0.0,
            space_insert_rate: 0.0,
            bias_patterns: Vec::new(),
        }
    }

    /// Creates an OCR operation with all parameters specified.
    #[allow(clippy::too_many_arguments)]
    pub const fn with_params(
        rate: f64,
        burst_enter: f64,
        burst_exit: f64,
        burst_multiplier: f64,
        bias_k: usize,
        bias_beta: f64,
        space_drop_rate: f64,
        space_insert_rate: f64,
    ) -> Self {
        Self {
            rate,
            burst_enter,
            burst_exit,
            burst_multiplier,
            bias_k,
            bias_beta,
            space_drop_rate,
            space_insert_rate,
            bias_patterns: Vec::new(),
        }
    }

    /// Selects K random patterns for document-level bias.
    fn select_bias_patterns(&mut self, rng: &mut dyn OperationRng, table_size: usize) -> Result<(), OperationError> {
        self.bias_patterns.clear();
        if self.bias_k == 0 || table_size == 0 {
            return Ok(());
        }
        let k = self.bias_k.min(table_size);
        let mut indices: Vec<usize> = (0..table_size).collect();
        // Fisher-Yates partial shuffle to select k elements
        for i in 0..k {
            let j = i + rng.rand_index(table_size - i)?;
            indices.swap(i, j);
        }
        self.bias_patterns = indices[..k].to_vec();
        self.bias_patterns.sort_unstable();
        Ok(())
    }

    /// Returns true if the given pattern index is in the bias set.
    #[inline]
    fn is_biased_pattern(&self, pattern_idx: usize) -> bool {
        self.bias_patterns.binary_search(&pattern_idx).is_ok()
    }

    /// Applies whitespace errors (segmentation failures) as a pre-pass.
    /// This models the OCR pipeline where segmentation happens before character recognition.
    fn apply_whitespace_errors(
        &self,
        buffer: &mut TextBuffer,
        rng: &mut dyn OperationRng,
    ) -> Result<(), OperationError> {
        if self.space_drop_rate <= 0.0 && self.space_insert_rate <= 0.0 {
            return Ok(());
        }

        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        for (seg_idx, segment) in segments.iter().enumerate() {
            if !segment.is_mutable() {
                continue;
            }

            let text = segment.text();
            if text.is_empty() {
                continue;
            }

            let chars: Vec<char> = text.chars().collect();
            let mut modified = String::with_capacity(text.len());
            let mut changed = false;

            for (char_idx, &ch) in chars.iter().enumerate() {
                if ch == ' ' && self.space_drop_rate > 0.0 {
                    // Potential space drop
                    if rng.random()? < self.space_drop_rate {
                        // Drop this space (don't add to modified)
                        changed = true;
                        continue;
                    }
                }

                modified.push(ch);

                // Potential space insert (not after last char, not after/before existing space)
                if self.space_insert_rate > 0.0
                    && char_idx + 1 < chars.len()
                    && !ch.is_whitespace()
                    && !chars[char_idx + 1].is_whitespace()
                    && rng.random()? < self.space_insert_rate {
                        modified.push(' ');
                        changed = true;
                    }
            }

            if changed {
                segment_replacements.push((seg_idx, modified));
            }
        }

        if !segment_replacements.is_empty() {
            buffer.replace_segments_bulk(segment_replacements);
            buffer.reindex_if_needed();
        }

        Ok(())
    }
}

impl TextOperation for OcrArtifactsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        // Phase 1: Apply whitespace errors (segmentation failures) as pre-pass
        // This models the OCR pipeline where segmentation happens before character recognition.
        // Reference: Smith (2007) - Tesseract architecture
        let mut op = self.clone();
        op.apply_whitespace_errors(buffer, rng)?;

        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        // Pre-fetch the confusion table and automaton for efficient lookup
        let table = confusion_table();
        let automaton = ocr_automaton();

        // Phase 2: Select document-level bias patterns
        // Reference: UNLV-ISRI Annual Tests (1995) - consistent error profiles
        op.select_bias_patterns(rng, table.len())?;

        // Estimate candidate capacity based on text length
        let total_chars: usize = segments.iter().map(|s| s.text().len()).sum();
        let estimated_candidates = total_chars / 3;

        // Find candidates across all segments using Aho-Corasick
        // Track (seg_idx, start, end, pattern_idx, char_position) for burst model
        let mut candidates: Vec<(usize, usize, usize, usize, usize)> =
            Vec::with_capacity(estimated_candidates);

        let mut global_char_pos = 0usize;
        for (seg_idx, segment) in segments.iter().enumerate() {
            if !segment.is_mutable() {
                global_char_pos += segment.text().chars().count();
                continue;
            }
            let seg_text = segment.text();
            for mat in automaton.find_iter(seg_text) {
                // Calculate approximate character position for this match
                let char_pos = global_char_pos + seg_text[..mat.start()].chars().count();
                candidates.push((seg_idx, mat.start(), mat.end(), mat.pattern().as_usize(), char_pos));
            }
            global_char_pos += seg_text.chars().count();
        }

        if candidates.is_empty() {
            return Ok(());
        }

        // Phase 3: Generate burst state sequence using HMM
        // Reference: Kanungo et al. (1994) - spatial correlation of defects
        let total_candidates = candidates.len();
        let burst_enabled = op.burst_enter > 0.0;
        let mut in_harsh_state = false;
        let mut harsh_positions: std::collections::HashSet<usize> = std::collections::HashSet::new();

        if burst_enabled {
            // Walk through candidates in position order and simulate HMM
            let mut sorted_by_pos: Vec<(usize, usize)> = candidates
                .iter()
                .enumerate()
                .map(|(idx, (_, _, _, _, char_pos))| (idx, *char_pos))
                .collect();
            sorted_by_pos.sort_by_key(|(_, pos)| *pos);

            for (candidate_idx, _char_pos) in sorted_by_pos {
                // State transitions
                if in_harsh_state {
                    if rng.random()? < op.burst_exit {
                        in_harsh_state = false;
                    }
                } else if rng.random()? < op.burst_enter {
                    in_harsh_state = true;
                }

                if in_harsh_state {
                    harsh_positions.insert(candidate_idx);
                }
            }
        }

        // Calculate effective selection count
        let base_to_select = ((total_candidates as f64) * op.rate).floor() as usize;
        if base_to_select == 0 && total_candidates > 0 && op.rate > 0.0 {
            // At least try to select one if rate > 0
        }

        // Fisher-Yates shuffle - must complete for RNG determinism
        let mut order: Vec<usize> = (0..total_candidates).collect();
        for idx in (1..total_candidates).rev() {
            let swap_with = rng.rand_index(idx + 1)?;
            order.swap(idx, swap_with);
        }

        // Now select candidates in shuffled order with burst and bias modifiers
        let num_segments = segments.len();
        let mut occupied: Vec<Vec<(usize, usize)>> = vec![Vec::new(); num_segments];
        let mut chosen: Vec<(usize, usize, usize, &'static str)> =
            Vec::with_capacity(base_to_select.min(1024));

        // Track effective selections (burst increases the count we can select)
        let mut effective_selections = 0usize;

        for &candidate_idx in &order {
            // Dynamic target based on burst state
            let is_harsh = harsh_positions.contains(&candidate_idx);
            let effective_rate = if is_harsh {
                (op.rate * op.burst_multiplier).min(1.0)
            } else {
                op.rate
            };

            // Check if we've selected enough
            // Use rate-weighted target: base_to_select for clean, more for harsh
            let target = if is_harsh {
                ((total_candidates as f64) * effective_rate).floor() as usize
            } else {
                base_to_select
            };

            if effective_selections >= target.max(base_to_select) {
                break;
            }

            let (seg_idx, start, end, pattern_idx, _char_pos) = candidates[candidate_idx];
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

            // Apply selection probability with bias amplification
            // Reference: UNLV-ISRI - document-specific error profiles
            let mut selection_weight = effective_rate;
            if op.is_biased_pattern(pattern_idx) {
                selection_weight *= op.bias_beta;
            }

            // Probabilistic selection
            if selection_weight < 1.0 && rng.random()? >= selection_weight {
                continue;
            }

            let choice_idx = rng.rand_index(choices.len())?;
            chosen.push((seg_idx, start, end, choices[choice_idx]));
            occupied[seg_idx].push((start, end));
            effective_selections += 1;
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

// ============================================================================
// Zero-Width Character Operations
// ============================================================================
//
// Operations for inserting invisible zero-width Unicode characters that can
// disrupt tokenization and string matching while remaining visually invisible.

/// Visibility mode controlling which zero-width characters are included in the palette.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum VisibilityMode {
    /// Only true invisibles (ZWSP, ZWNJ, ZWJ, WJ, CGJ, BOM)
    #[default]
    Glyphless,
    /// Glyphless + variation selectors (VS1-VS16)
    WithJoiners,
    /// All of the above + hair/thin spaces
    SemiVisible,
}

impl VisibilityMode {
    /// Parse visibility mode from string.
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "glyphless" => Some(Self::Glyphless),
            "with_joiners" => Some(Self::WithJoiners),
            "semi_visible" => Some(Self::SemiVisible),
            _ => None,
        }
    }

    /// Get the default character palette for this visibility mode.
    pub fn default_palette(&self) -> Vec<String> {
        match self {
            Self::Glyphless => vec![
                "\u{200B}".to_string(), // ZERO WIDTH SPACE
                "\u{200C}".to_string(), // ZERO WIDTH NON-JOINER
                "\u{200D}".to_string(), // ZERO WIDTH JOINER
                "\u{FEFF}".to_string(), // BYTE ORDER MARK
                "\u{2060}".to_string(), // WORD JOINER
                "\u{034F}".to_string(), // COMBINING GRAPHEME JOINER
            ],
            Self::WithJoiners => {
                let mut palette = Self::Glyphless.default_palette();
                // Add variation selectors VS1-VS16
                for vs in '\u{FE00}'..='\u{FE0F}' {
                    palette.push(vs.to_string());
                }
                palette
            }
            Self::SemiVisible => {
                let mut palette = Self::WithJoiners.default_palette();
                palette.push("\u{200A}".to_string()); // HAIR SPACE
                palette.push("\u{2009}".to_string()); // THIN SPACE
                palette.push("\u{202F}".to_string()); // NARROW NO-BREAK SPACE
                palette
            }
        }
    }
}

/// Placement mode controlling where zero-width characters are inserted.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum PlacementMode {
    /// Insert between any adjacent non-whitespace characters (current behavior)
    #[default]
    Random,
    /// Only insert at grapheme cluster boundaries (safer for rendering)
    GraphemeBoundary,
    /// Context-sensitive: ZWJ/ZWNJ only where linguistically meaningful
    ScriptAware,
}

impl PlacementMode {
    /// Parse placement mode from string.
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "random" => Some(Self::Random),
            "grapheme_boundary" => Some(Self::GraphemeBoundary),
            "script_aware" => Some(Self::ScriptAware),
            _ => None,
        }
    }
}

/// Check if a character is from a script where joiners are linguistically meaningful.
fn is_joiner_meaningful_script(c: char) -> bool {
    // Arabic script range
    let is_arabic = ('\u{0600}'..='\u{06FF}').contains(&c)
        || ('\u{0750}'..='\u{077F}').contains(&c)
        || ('\u{08A0}'..='\u{08FF}').contains(&c);

    // Devanagari
    let is_devanagari = ('\u{0900}'..='\u{097F}').contains(&c);

    // Bengali
    let is_bengali = ('\u{0980}'..='\u{09FF}').contains(&c);

    // Other Indic scripts
    let is_indic = ('\u{0A00}'..='\u{0D7F}').contains(&c);

    // Common emoji ranges (Extended_Pictographic approximation)
    let is_emoji = ('\u{1F300}'..='\u{1F9FF}').contains(&c)
        || ('\u{2600}'..='\u{26FF}').contains(&c)
        || ('\u{2700}'..='\u{27BF}').contains(&c)
        || ('\u{1F600}'..='\u{1F64F}').contains(&c);

    is_arabic || is_devanagari || is_bengali || is_indic || is_emoji
}

/// Check if a character is a valid base for a variation selector.
fn is_valid_vs_base(c: char) -> bool {
    // Emoji (Extended_Pictographic approximation)
    let is_emoji = ('\u{1F300}'..='\u{1F9FF}').contains(&c)
        || ('\u{2600}'..='\u{26FF}').contains(&c)
        || ('\u{2700}'..='\u{27BF}').contains(&c)
        || ('\u{1F600}'..='\u{1F64F}').contains(&c)
        || ('\u{231A}'..='\u{23FF}').contains(&c);

    // CJK Ideographs
    let is_cjk = ('\u{4E00}'..='\u{9FFF}').contains(&c)
        || ('\u{3400}'..='\u{4DBF}').contains(&c)
        || ('\u{F900}'..='\u{FAFF}').contains(&c);

    // Mathematical symbols
    let is_math = ('\u{2200}'..='\u{22FF}').contains(&c);

    is_emoji || is_cjk || is_math
}

/// Check if a character is a variation selector.
fn is_variation_selector(c: char) -> bool {
    ('\u{FE00}'..='\u{FE0F}').contains(&c)
}

#[derive(Debug, Clone)]
pub struct ZeroWidthOp {
    pub rate: f64,
    pub characters: Vec<String>,
    pub visibility_mode: VisibilityMode,
    pub placement_mode: PlacementMode,
    pub max_consecutive: usize,
}

impl ZeroWidthOp {
    /// Create a new ZeroWidthOp with default settings.
    pub fn new(rate: f64, characters: Vec<String>) -> Self {
        Self {
            rate,
            characters,
            visibility_mode: VisibilityMode::default(),
            placement_mode: PlacementMode::default(),
            max_consecutive: 4,
        }
    }

    /// Create with all settings.
    pub const fn with_options(
        rate: f64,
        characters: Vec<String>,
        visibility_mode: VisibilityMode,
        placement_mode: PlacementMode,
        max_consecutive: usize,
    ) -> Self {
        Self {
            rate,
            characters,
            visibility_mode,
            placement_mode,
            max_consecutive,
        }
    }

    /// Get the effective palette, auto-populating from visibility mode if empty.
    fn effective_palette(&self) -> Vec<String> {
        let filtered: Vec<String> = self
            .characters
            .iter()
            .filter(|value| !value.is_empty())
            .cloned()
            .collect();

        if filtered.is_empty() {
            self.visibility_mode.default_palette()
        } else {
            filtered
        }
    }

    /// Check if a character from the palette is a joiner (ZWJ or ZWNJ).
    fn is_joiner_char(c: &str) -> bool {
        matches!(c, "\u{200C}" | "\u{200D}")
    }

    /// Collect insertion positions based on placement mode.
    fn collect_positions(
        &self,
        segments: &[TextSegment],
        palette: &[String],
    ) -> Vec<(usize, usize, Vec<usize>)> {
        // Returns: (segment_index, char_index, valid_palette_indices)
        use unicode_segmentation::UnicodeSegmentation;

        let mut positions: Vec<(usize, usize, Vec<usize>)> = Vec::new();

        // Pre-compute which palette entries are variation selectors
        let vs_indices: Vec<usize> = palette
            .iter()
            .enumerate()
            .filter(|(_, s)| s.chars().next().is_some_and(is_variation_selector))
            .map(|(i, _)| i)
            .collect();

        let joiner_indices: Vec<usize> = palette
            .iter()
            .enumerate()
            .filter(|(_, s)| Self::is_joiner_char(s))
            .map(|(i, _)| i)
            .collect();

        let non_vs_non_joiner_indices: Vec<usize> = palette
            .iter()
            .enumerate()
            .filter(|(_, s)| {
                !s.chars().next().is_some_and(is_variation_selector)
                    && !Self::is_joiner_char(s)
            })
            .map(|(i, _)| i)
            .collect();

        for (seg_idx, segment) in segments.iter().enumerate() {
            if !segment.is_mutable() {
                continue;
            }
            let text = segment.text();
            let chars: Vec<char> = text.chars().collect();

            if chars.len() < 2 {
                continue;
            }

            match self.placement_mode {
                PlacementMode::Random => {
                    // Original behavior: between any adjacent non-whitespace characters
                    for char_idx in 0..(chars.len() - 1) {
                        if !chars[char_idx].is_whitespace() && !chars[char_idx + 1].is_whitespace()
                        {
                            let mut valid_indices: Vec<usize> =
                                (0..palette.len()).collect();

                            // Filter VS to only valid bases
                            if !vs_indices.is_empty() && !is_valid_vs_base(chars[char_idx]) {
                                valid_indices.retain(|i| !vs_indices.contains(i));
                            }

                            if !valid_indices.is_empty() {
                                positions.push((seg_idx, char_idx + 1, valid_indices));
                            }
                        }
                    }
                }
                PlacementMode::GraphemeBoundary => {
                    // Only at grapheme cluster boundaries
                    let graphemes: Vec<&str> = text.graphemes(true).collect();
                    if graphemes.len() < 2 {
                        continue;
                    }

                    let mut char_offset = 0;

                    for (g_idx, grapheme) in graphemes.iter().enumerate() {
                        let grapheme_char_len = grapheme.chars().count();

                        // Position after this grapheme (before the next one)
                        if g_idx > 0 && g_idx < graphemes.len() {
                            // Check both adjacent graphemes for whitespace
                            let prev_grapheme = graphemes[g_idx - 1];
                            let is_prev_ws = prev_grapheme.chars().all(char::is_whitespace);
                            let is_curr_ws = grapheme.chars().all(char::is_whitespace);

                            if !is_prev_ws && !is_curr_ws {
                                let prev_char = prev_grapheme.chars().last().unwrap_or(' ');
                                let mut valid_indices: Vec<usize> =
                                    (0..palette.len()).collect();

                                // Filter VS to only valid bases
                                if !vs_indices.is_empty() && !is_valid_vs_base(prev_char) {
                                    valid_indices.retain(|i| !vs_indices.contains(i));
                                }

                                if !valid_indices.is_empty() {
                                    positions.push((seg_idx, char_offset, valid_indices));
                                }
                            }
                        }

                        char_offset += grapheme_char_len;
                    }
                }
                PlacementMode::ScriptAware => {
                    // ZWJ/ZWNJ only where linguistically meaningful
                    for char_idx in 0..(chars.len() - 1) {
                        if !chars[char_idx].is_whitespace() && !chars[char_idx + 1].is_whitespace()
                        {
                            let prev_char = chars[char_idx];
                            let next_char = chars[char_idx + 1];

                            let joiner_meaningful = is_joiner_meaningful_script(prev_char)
                                || is_joiner_meaningful_script(next_char);

                            let mut valid_indices: Vec<usize> = Vec::new();

                            // Always allow non-joiner, non-VS characters
                            valid_indices.extend(&non_vs_non_joiner_indices);

                            // Allow joiners only if meaningful
                            if joiner_meaningful {
                                valid_indices.extend(&joiner_indices);
                            }

                            // Filter VS to only valid bases
                            if is_valid_vs_base(prev_char) {
                                valid_indices.extend(&vs_indices);
                            }

                            valid_indices.sort_unstable();
                            valid_indices.dedup();

                            if !valid_indices.is_empty() {
                                positions.push((seg_idx, char_idx + 1, valid_indices));
                            }
                        }
                    }
                }
            }
        }

        positions
    }

    /// Enforce max_consecutive constraint on insertions.
    fn enforce_max_consecutive(
        &self,
        insertions: &mut Vec<(usize, usize, String)>,
    ) {
        if self.max_consecutive == 0 {
            return; // No limit
        }

        // Sort by (segment, position)
        insertions.sort_by_key(|(seg, pos, _)| (*seg, *pos));

        let mut consecutive_count = 0;
        let mut last_seg = usize::MAX;
        let mut last_pos = usize::MAX;

        insertions.retain(|(seg, pos, _)| {
            if *seg == last_seg && *pos == last_pos + 1 {
                consecutive_count += 1;
            } else {
                consecutive_count = 1;
            }
            last_seg = *seg;
            last_pos = *pos;

            consecutive_count <= self.max_consecutive
        });
    }
}

impl TextOperation for ZeroWidthOp {
    fn apply(
        &self,
        buffer: &mut TextBuffer,
        rng: &mut dyn OperationRng,
    ) -> Result<(), OperationError> {
        let palette = self.effective_palette();
        if palette.is_empty() {
            return Ok(());
        }

        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        // Collect insertion positions based on placement mode
        let positions = self.collect_positions(segments, &palette);

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
            let (seg_idx, char_idx, ref valid_palette_indices) = positions[sample_idx];
            // Pick from valid palette entries only
            let palette_choice = rng.rand_index(valid_palette_indices.len())?;
            let palette_idx = valid_palette_indices[palette_choice];
            insertions.push((seg_idx, char_idx, palette[palette_idx].clone()));
        }

        // Enforce max_consecutive constraint
        self.enforce_max_consecutive(&mut insertions);

        if insertions.is_empty() {
            return Ok(());
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

// ============================================================================
// Keyboard Typo Operations
// ============================================================================
//
// Simulates keyboard typing errors using adjacency-based neighbor selection
// and motor coordination models based on the Aalto 136M Keystrokes dataset
// (Dhakal et al., 2018).

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
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_lowercase().replace('-', "_").as_str() {
            "uniform" => Some(Self::Uniform),
            "wet_ink" => Some(Self::WetInk),
            "hastily_edited" => Some(Self::HastilyEdited),
            _ => None,
        }
    }

    /// Get the weight multiplier for a transition type.
    const fn weight_for_transition(&self, transition: TransitionType) -> f64 {
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
const fn finger_for_char(ch: char) -> Option<(u8, u8)> {
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
const fn classify_transition(prev_char: char, curr_char: char) -> TransitionType {
    let Some(prev) = finger_for_char(prev_char) else {
        return TransitionType::Unknown;
    };
    let Some(curr) = finger_for_char(curr_char) else {
        return TransitionType::Unknown;
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

    const fn from_index(idx: usize) -> Self {
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

    const fn is_char_level(self) -> bool {
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
    pub const fn new(enter_rate: f64, exit_rate: f64, shift_map: HashMap<String, String>) -> Self {
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

    pub fn apply(&self, text: &str, rng: &mut dyn OperationRng) -> Result<String, OperationError> {
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
        rng: &mut dyn OperationRng,
        chars: &[char],
        max_tries: usize,
    ) -> Result<Option<usize>, OperationError> {
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
        self.layout.get(key).map(Vec::as_slice)
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
        rng: &mut dyn OperationRng,
    ) -> Result<usize, OperationError> {
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

    fn remove_space(rng: &mut dyn OperationRng, chars: &mut Vec<char>) -> Result<(), OperationError> {
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

    fn insert_space(rng: &mut dyn OperationRng, chars: &mut Vec<char>) -> Result<(), OperationError> {
        if chars.len() < 2 {
            return Ok(());
        }
        let idx = rng.rand_index(chars.len() - 1)? + 1;
        if idx <= chars.len() {
            chars.insert(idx, ' ');
        }
        Ok(())
    }

    fn repeat_char(rng: &mut dyn OperationRng, chars: &mut Vec<char>) -> Result<(), OperationError> {
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
        rng: &mut dyn OperationRng,
        chars: &mut Vec<char>,
    ) -> Result<(), OperationError> {
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

impl TextOperation for TypoOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
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

// ============================================================================
// Quote Normalization Operation
// ============================================================================
//
// Converts ASCII straight quotes to typographically correct curly quotes
// (smart quotes) based on context and pairing.

#[derive(Clone, Copy, Debug)]
enum QuoteKind {
    Double,
    Single,
    Backtick,
}

impl QuoteKind {
    const fn from_char(ch: char) -> Option<Self> {
        match ch {
            '"' => Some(Self::Double),
            '\'' => Some(Self::Single),
            '`' => Some(Self::Backtick),
            _ => None,
        }
    }

    const fn as_char(self) -> char {
        match self {
            Self::Double => '"',
            Self::Single => '\'',
            Self::Backtick => '`',
        }
    }

    const fn index(self) -> usize {
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

impl TextOperation for QuotePairsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
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

// ============================================================================
// Operation Enum (Type-Erased Wrapper)
// ============================================================================
//
// The Operation enum provides a type-erased wrapper around all operation types,
// enabling heterogeneous collections and dynamic dispatch in the pipeline.

/// Type-erased text corruption operation for pipeline sequencing.
#[derive(Debug, Clone)]
pub enum Operation {
    Reduplicate(ReduplicateWordsOp),
    Delete(DeleteRandomWordsOp),
    SwapAdjacent(SwapAdjacentWordsOp),
    RushmoreCombo(RushmoreComboOp),
    Redact(RedactWordsOp),
    Ocr(OcrArtifactsOp),
    Typo(TypoOp),
    Mimic(HomoglyphOp),
    ZeroWidth(ZeroWidthOp),
    Jargoyle(LexemeSubstitutionOp),
    QuotePairs(QuotePairsOp),
    Hokey(crate::word_stretching::WordStretchOp),
    Wherewolf(HomophoneOp),
    Pedant(GrammarRuleOp),
}

impl TextOperation for Operation {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        match self {
            Self::Reduplicate(op) => op.apply(buffer, rng),
            Self::Delete(op) => op.apply(buffer, rng),
            Self::SwapAdjacent(op) => op.apply(buffer, rng),
            Self::RushmoreCombo(op) => op.apply(buffer, rng),
            Self::Redact(op) => op.apply(buffer, rng),
            Self::Ocr(op) => op.apply(buffer, rng),
            Self::Typo(op) => op.apply(buffer, rng),
            Self::Mimic(op) => op.apply(buffer, rng),
            Self::ZeroWidth(op) => op.apply(buffer, rng),
            Self::Jargoyle(op) => op.apply(buffer, rng),
            Self::QuotePairs(op) => op.apply(buffer, rng),
            Self::Hokey(op) => op.apply(buffer, rng),
            Self::Wherewolf(op) => op.apply(buffer, rng),
            Self::Pedant(op) => op.apply(buffer, rng),
        }
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::{
        DeleteRandomWordsOp, TextOperation, OperationError, OcrArtifactsOp, RedactWordsOp,
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
            OperationError::NoRedactableWords => {}
            other => panic!("expected no redactable words, got {other:?}"),
        }
    }

    #[test]
    #[ignore = "TODO: Update seed/expectations after deferred reindexing optimization"]
    fn ocr_artifacts_replaces_expected_regions() {
        let mut buffer = TextBuffer::from_owned("Hello rn world".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(151);
        let op = OcrArtifactsOp::new(1.0);
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
        let op = OcrArtifactsOp::new(1.0);
        op.apply(&mut buffer, &mut rng).expect("ocr succeeds");
        let result = buffer.to_string();
        assert_ne!(result, "The m rn");
        assert!(result.contains('r'));
    }
}

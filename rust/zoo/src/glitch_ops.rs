use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::PyErr;
use regex::{Captures, Regex};

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

    fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, GlitchOpError> {
        PyRng::sample_indices(self, population, k).map_err(GlitchOpError::from)
    }
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
}

impl GlitchOp for ReduplicateWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        if buffer.word_count() == 0 {
            return Ok(());
        }

        let mut word_index = 0;
        while word_index < buffer.word_count() {
            let Some(segment) = buffer.word_segment(word_index) else {
                break;
            };
            if matches!(segment.kind(), SegmentKind::Separator) {
                word_index += 1;
                continue;
            }
            let original = segment.text().to_string();
            if original.trim().is_empty() {
                word_index += 1;
                continue;
            }

            if rng.random()? < self.reduplication_rate {
                let (prefix, core, suffix) = split_affixes(&original);
                if core.is_empty() {
                    word_index += 1;
                    continue;
                }
                let first = format!("{prefix}{core}");
                let second = format!("{core}{suffix}");
                buffer.replace_word(word_index, &first)?;
                buffer.insert_word_after(word_index, &second, Some(" "))?;
                word_index += 2;
            } else {
                word_index += 1;
            }
        }

        Ok(())
    }
}

/// Deletes random words while preserving punctuation cleanup semantics.
#[derive(Debug, Clone, Copy)]
pub struct DeleteRandomWordsOp {
    pub max_deletion_rate: f64,
}

impl GlitchOp for DeleteRandomWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        if buffer.word_count() <= 1 {
            return Ok(());
        }

        let mut candidates: Vec<(usize, String)> = Vec::new();
        for idx in 1..buffer.word_count() {
            if let Some(segment) = buffer.word_segment(idx) {
                let text = segment.text();
                if !text.is_empty() && !is_whitespace_only(text) {
                    candidates.push((idx, text.to_string()));
                }
            }
        }

        if candidates.is_empty() {
            return Ok(());
        }

        let allowed = ((candidates.len() as f64) * self.max_deletion_rate).floor() as usize;
        if allowed == 0 {
            return Ok(());
        }

        let mut deletions = 0usize;
        for (word_index, original) in candidates {
            if deletions >= allowed {
                break;
            }

            if rng.random()? < self.max_deletion_rate {
                let (prefix, _, suffix) = split_affixes(&original);
                let replacement = format!("{}{}", prefix.trim(), suffix.trim());
                buffer.replace_word(word_index, &replacement)?;
                deletions += 1;
            }
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

/// Redacts words by replacing core characters with a replacement token.
#[derive(Debug, Clone)]
pub struct RedactWordsOp {
    pub replacement_char: String,
    pub redaction_rate: f64,
    pub merge_adjacent: bool,
}

impl GlitchOp for RedactWordsOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        if buffer.word_count() == 0 {
            return Err(GlitchOpError::NoRedactableWords);
        }

        let mut word_indices: Vec<(usize, String)> = Vec::new();
        for idx in 0..buffer.word_count() {
            if let Some(segment) = buffer.word_segment(idx) {
                let text = segment.text();
                if !text.trim().is_empty() {
                    word_indices.push((idx, text.to_string()));
                }
            }
        }

        if word_indices.is_empty() {
            return Err(GlitchOpError::NoRedactableWords);
        }

        let mut num_to_redact =
            ((word_indices.len() as f64) * self.redaction_rate).floor() as usize;
        if num_to_redact < 1 {
            num_to_redact = 1;
        }
        if num_to_redact > word_indices.len() {
            return Err(GlitchOpError::ExcessiveRedaction {
                requested: num_to_redact,
                available: word_indices.len(),
            });
        }

        let mut selections = rng.sample_indices(word_indices.len(), num_to_redact)?;
        selections.sort_unstable();

        for selection in selections {
            let (word_index, original) = &word_indices[selection];
            let (prefix, core, suffix) = split_affixes(original);
            if core.is_empty() {
                continue;
            }
            let repeat = core.chars().count();
            let mut replacement = String::with_capacity(
                prefix.len() + suffix.len() + self.replacement_char.len() * repeat,
            );
            replacement.push_str(&prefix);
            for _ in 0..repeat {
                replacement.push_str(&self.replacement_char);
            }
            replacement.push_str(&suffix);
            buffer.replace_word(*word_index, &replacement)?;
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

/// Type-erased glitchling operation for pipeline sequencing.
#[derive(Debug, Clone)]
pub enum GlitchOperation {
    Reduplicate(ReduplicateWordsOp),
    Delete(DeleteRandomWordsOp),
    Redact(RedactWordsOp),
    Ocr(OcrArtifactsOp),
}

impl GlitchOp for GlitchOperation {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        match self {
            GlitchOperation::Reduplicate(op) => op.apply(buffer, rng),
            GlitchOperation::Delete(op) => op.apply(buffer, rng),
            GlitchOperation::Redact(op) => op.apply(buffer, rng),
            GlitchOperation::Ocr(op) => op.apply(buffer, rng),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        DeleteRandomWordsOp, GlitchOp, GlitchOpError, OcrArtifactsOp, RedactWordsOp,
        ReduplicateWordsOp,
    };
    use crate::rng::PyRng;
    use crate::text_buffer::TextBuffer;

    #[test]
    fn reduplication_inserts_duplicate_with_space() {
        let mut buffer = TextBuffer::from_str("Hello world");
        let mut rng = PyRng::new(151);
        let op = ReduplicateWordsOp {
            reduplication_rate: 1.0,
        };
        op.apply(&mut buffer, &mut rng)
            .expect("reduplication works");
        assert_eq!(buffer.to_string(), "Hello Hello world world");
    }

    #[test]
    fn delete_random_words_cleans_up_spacing() {
        let mut buffer = TextBuffer::from_str("One two three four five");
        let mut rng = PyRng::new(151);
        let op = DeleteRandomWordsOp {
            max_deletion_rate: 0.75,
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
        };
        op.apply(&mut buffer, &mut rng)
            .expect("reduplication succeeds");
        assert_eq!(
            buffer.to_string(),
            "The The quick quick brown brown fox fox"
        );
    }

    #[test]
    fn delete_matches_python_reference_seed_123() {
        let mut buffer = TextBuffer::from_str("The quick brown fox jumps over the lazy dog.");
        let mut rng = PyRng::new(123);
        let op = DeleteRandomWordsOp {
            max_deletion_rate: 0.5,
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
        };
        op.apply(&mut buffer, &mut rng).expect("redaction succeeds");
        assert_eq!(buffer.to_string(), "████ these words ██████");
    }

    #[test]
    fn redact_merge_matches_python_reference_seed_7() {
        let mut buffer = TextBuffer::from_str("redact these words");
        let mut rng = PyRng::new(7);
        let op = RedactWordsOp {
            replacement_char: "█".to_string(),
            redaction_rate: 1.0,
            merge_adjacent: true,
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
        assert_eq!(buffer.to_string(), "Tlie rn m");
    }
}

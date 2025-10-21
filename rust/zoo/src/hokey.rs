use pyo3::prelude::*;
use pyo3::types::PyAny;
use pyo3::Bound;
use regex::Regex;
use std::collections::HashSet;
use std::sync::OnceLock;

use crate::glitch_ops::{GlitchOp, GlitchOpError, GlitchRng};
use crate::text_buffer::TextBuffer;

static WORD_TOKEN_REGEX: OnceLock<Regex> = OnceLock::new();

fn word_token_regex() -> &'static Regex {
    WORD_TOKEN_REGEX.get_or_init(|| Regex::new(r"\w+|\W+").unwrap())
}

/// Hokey operation that extends vowels in short words for emphasis.
#[derive(Debug, Clone)]
pub struct HokeyOp {
    pub rate: f64,
    pub extension_min: i32,
    pub extension_max: i32,
    pub word_length_threshold: usize,
}

impl HokeyOp {
    fn is_vowel(c: char) -> bool {
        matches!(c, 'a' | 'e' | 'i' | 'o' | 'u' | 'A' | 'E' | 'I' | 'O' | 'U')
    }

    fn find_vowel_positions(word: &str) -> Vec<usize> {
        word.char_indices()
            .filter(|(_, c)| Self::is_vowel(*c))
            .map(|(i, _)| i)
            .collect()
    }

    fn is_word_token(token: &str) -> bool {
        token.chars().any(|c| c.is_alphanumeric())
    }
}

impl GlitchOp for HokeyOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let text = buffer.to_string();
        if text.is_empty() {
            return Ok(());
        }

        let regex = word_token_regex();
        let mut tokens: Vec<String> = regex
            .find_iter(&text)
            .map(|m| m.as_str().to_string())
            .collect();

        // First pass: identify eligible word positions
        let mut eligible_positions = Vec::new();
        for (i, token) in tokens.iter().enumerate() {
            if Self::is_word_token(token) {
                if token.len() <= self.word_length_threshold {
                    // Check if word has any vowels
                    if token.chars().any(Self::is_vowel) {
                        eligible_positions.push(i);
                    }
                }
            }
        }

        if eligible_positions.is_empty() {
            return Ok(());
        }

        // Determine how many words to affect based on rate
        let num_to_affect = (eligible_positions.len() as f64 * self.rate) as usize;

        if num_to_affect == 0 {
            return Ok(());
        }

        // Sort positions to ensure determinism, then shuffle
        eligible_positions.sort_unstable();

        // Fisher-Yates shuffle
        for i in (1..eligible_positions.len()).rev() {
            let j = rng.rand_index(i + 1)?;
            eligible_positions.swap(i, j);
        }

        // Select positions to extend
        let positions_to_extend: HashSet<usize> =
            eligible_positions.into_iter().take(num_to_affect).collect();

        // Second pass: apply extensions
        for (i, token) in tokens.iter_mut().enumerate() {
            if positions_to_extend.contains(&i) {
                // Find all vowel positions in the word
                let vowel_positions = Self::find_vowel_positions(token);

                if !vowel_positions.is_empty() {
                    // Extend the last vowel (like "cool" -> "cooool")
                    let vowel_idx = vowel_positions[vowel_positions.len() - 1];

                    // Get the vowel character
                    let vowel_char = token.chars().nth(vowel_idx).unwrap();

                    // Determine how many times to repeat the vowel
                    let num_extra = if self.extension_max > self.extension_min {
                        self.extension_min
                            + (rng.rand_index(
                                (self.extension_max - self.extension_min + 1) as usize,
                            )? as i32)
                    } else {
                        self.extension_min
                    };

                    // Build the extended word
                    let chars: Vec<char> = token.chars().collect();
                    let extension: String = std::iter::repeat(vowel_char)
                        .take(num_extra as usize)
                        .collect();

                    // Insert the extension after the vowel
                    let mut extended = String::new();
                    for (idx, &ch) in chars.iter().enumerate() {
                        extended.push(ch);
                        if idx == vowel_idx {
                            extended.push_str(&extension);
                        }
                    }

                    *token = extended;
                }
            }
        }

        // Reconstruct the text
        let result = tokens.join("");
        buffer.clear();
        buffer.push_str(&result)?;

        Ok(())
    }
}

/// Python wrapper for the Hokey operation.
#[pyfunction]
pub fn hokey(
    text: &str,
    rate: f64,
    extension_min: i32,
    extension_max: i32,
    word_length_threshold: usize,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    use crate::PythonRngAdapter;

    let op = HokeyOp {
        rate,
        extension_min,
        extension_max,
        word_length_threshold,
    };

    let mut buffer = TextBuffer::from_str(text);
    let mut adapter = PythonRngAdapter::new(rng.clone());

    op.apply(&mut buffer, &mut adapter)
        .map_err(|err| err.into_pyerr())?;

    Ok(buffer.to_string())
}

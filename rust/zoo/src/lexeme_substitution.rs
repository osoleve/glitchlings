//! Jargoyle: Dictionary-based word drift (synonym/color/jargon substitution).
//!
//! This module implements Jargoyle, which swaps words with alternatives from
//! bundled lexeme dictionaries. It supports multiple dictionary types:
//! - "colors": Color term swapping (formerly Spectroll)
//! - "synonyms": General synonym substitution
//! - "corporate": Business jargon alternatives
//! - "academic": Scholarly word substitutions
//! - "cyberpunk": Neon cyberpunk slang and gadgetry
//! - "lovecraftian": Cosmic horror terminology
//! Additional dictionaries can be dropped into the assets/lexemes directory
//! (or another directory pointed to by the GLITCHLINGS_LEXEME_DIR environment
//! variable) without changing the code.
//!
//! Two modes are supported:
//! - "literal": First entry in each word's alternatives (deterministic mapping)
//! - "drift": Random selection from alternatives (probabilistic)

use aho_corasick::{AhoCorasick, MatchKind};
use crate::operations::{TextOperation, OperationError, OperationRng};
use crate::rng::DeterministicRng;
use crate::text_buffer::TextBuffer;
use once_cell::sync::Lazy;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const RAW_LEXEMES: &str = include_str!(concat!(env!("OUT_DIR"), "/lexemes.json"));

const VALID_MODE_MESSAGE: &str = "drift, literal";
const LEXEME_ENV_VAR: &str = "GLITCHLINGS_LEXEME_DIR";

/// A single dictionary mapping words to their alternatives.
type LexemeDict = HashMap<String, Vec<String>>;

/// Names of lexemes that are embedded at compile time.
static BUNDLED_LEXEME_NAMES: Lazy<Vec<String>> = Lazy::new(|| {
    let raw: HashMap<String, serde_json::Value> =
        serde_json::from_str(RAW_LEXEMES).expect("lexemes.json should be valid JSON");
    raw.keys()
        .filter(|k| !k.starts_with('_'))
        .map(|k| k.to_ascii_lowercase())
        .collect()
});

/// All loaded lexeme dictionaries, keyed by dictionary name.
/// Always includes bundled lexemes; merges with custom lexemes from env dir if present.
static LEXEME_DICTIONARIES: Lazy<HashMap<String, LexemeDict>> = Lazy::new(|| {
    // Always start with bundled lexemes
    let mut dicts = load_bundled_lexemes();

    // Merge any custom lexemes from the environment-specified directory
    if let Some(dir) = lexeme_directory_from_env() {
        if let Ok(custom_dicts) = load_lexemes_from_directory(&dir) {
            for (name, dict) in custom_dicts {
                // Custom lexemes override bundled ones with the same name
                dicts.insert(name, dict);
            }
        }
    }

    dicts
});

/// Sorted lexeme names available for use.
static VALID_LEXEMES: Lazy<Vec<String>> = Lazy::new(|| {
    let mut names: Vec<String> = LEXEME_DICTIONARIES.keys().cloned().collect();
    names.sort();
    names
});

fn lexeme_directory_from_env() -> Option<PathBuf> {
    env::var_os(LEXEME_ENV_VAR)
        .map(PathBuf::from)
        .filter(|path| path.is_dir())
}

fn load_bundled_lexemes() -> HashMap<String, LexemeDict> {
    let raw: HashMap<String, serde_json::Value> =
        serde_json::from_str(RAW_LEXEMES).expect("lexemes.json should be valid JSON");
    load_lexeme_map(raw)
}

fn load_lexemes_from_directory(dir: &Path) -> Result<HashMap<String, LexemeDict>, String> {
    let mut files: Vec<PathBuf> = fs::read_dir(dir)
        .map_err(|err| format!("failed to read lexeme directory: {err}"))?
        .filter_map(|entry| entry.ok().map(|e| e.path()))
        .filter(|path| path.extension().map_or(false, |ext| ext == "json"))
        .collect();

    files.sort();

    let mut dictionaries: HashMap<String, serde_json::Value> = HashMap::new();
    for path in files {
        let name = path
            .file_stem()
            .and_then(|stem| stem.to_str())
            .map(|stem| stem.to_ascii_lowercase())
            .ok_or_else(|| format!("invalid lexeme file name {}", path.display()))?;

        let contents = fs::read_to_string(&path)
            .map_err(|err| format!("failed to read {}: {err}", path.display()))?;
        let value: serde_json::Value = serde_json::from_str(&contents)
            .map_err(|err| format!("invalid JSON in {}: {err}", path.display()))?;
        dictionaries.insert(name, value);
    }

    Ok(load_lexeme_map(dictionaries))
}

fn load_lexeme_map(raw: HashMap<String, serde_json::Value>) -> HashMap<String, LexemeDict> {
    let mut dictionaries: HashMap<String, LexemeDict> = HashMap::new();

    for (dict_name, dict_value) in raw {
        if dict_name.starts_with('_') {
            continue;
        }

        if let serde_json::Value::Object(entries) = dict_value {
            let parsed = parse_dictionary_entries(entries);
            if !parsed.is_empty() {
                dictionaries.insert(dict_name.to_ascii_lowercase(), parsed);
            }
        }
    }

    dictionaries
}

fn parse_dictionary_entries(entries: serde_json::Map<String, serde_json::Value>) -> LexemeDict {
    let mut dict: LexemeDict = HashMap::new();
    for (word, alternatives) in entries {
        if word.starts_with('_') {
            continue;
        }
        if let serde_json::Value::Array(arr) = alternatives {
            let words: Vec<String> = arr
                .into_iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect();
            if !words.is_empty() {
                dict.insert(word.to_ascii_lowercase(), words);
            }
        }
    }
    dict
}

/// Aho-Corasick matcher for each dictionary.
/// Provides O(n+m) matching instead of O(n*k) regex alternation.
struct LexemeMatcher {
    /// The Aho-Corasick automaton for fast multi-pattern matching
    automaton: AhoCorasick,
    /// Mapping from pattern index to the lowercase dictionary key
    pattern_keys: Vec<String>,
}

/// Pre-compiled Aho-Corasick matchers for each dictionary.
static LEXEME_MATCHERS: Lazy<HashMap<String, LexemeMatcher>> = Lazy::new(|| {
    let mut matchers: HashMap<String, LexemeMatcher> = HashMap::new();

    for (dict_name, dict) in LEXEME_DICTIONARIES.iter() {
        let mut words: Vec<&str> = dict.keys().map(|s| s.as_str()).collect();
        // Sort by length descending so longer matches are preferred
        words.sort_by_key(|w| std::cmp::Reverse(w.len()));

        if words.is_empty() {
            continue;
        }

        // Build Aho-Corasick with case-insensitive matching and leftmost-longest semantics
        let automaton = AhoCorasick::builder()
            .ascii_case_insensitive(true)
            .match_kind(MatchKind::LeftmostLongest)
            .build(&words)
            .expect("valid patterns for Aho-Corasick");

        let pattern_keys: Vec<String> = words.iter().map(|s| s.to_string()).collect();

        matchers.insert(dict_name.clone(), LexemeMatcher { automaton, pattern_keys });
    }

    matchers
});

/// Jargoyle operating mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JargoyleMode {
    /// First entry in alternatives (deterministic swap)
    Literal,
    /// Random selection from alternatives
    Drift,
}

impl JargoyleMode {
    pub fn parse(mode: &str) -> Result<Self, String> {
        let normalized = mode.to_ascii_lowercase();
        match normalized.as_str() {
            "" | "literal" => Ok(JargoyleMode::Literal),
            "drift" => Ok(JargoyleMode::Drift),
            _ => Err(format!(
                "Unsupported Jargoyle mode '{mode}'. Expected one of: {VALID_MODE_MESSAGE}"
            )),
        }
    }
}

/// Case pattern detected from a template string.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CasePattern {
    Empty,
    AllUpper,
    AllLower,
    TitleCase,
    Mixed,
}

/// Detect case pattern in a single pass over the string.
fn detect_case_pattern(s: &str) -> CasePattern {
    if s.is_empty() {
        return CasePattern::Empty;
    }

    let mut chars = s.chars();
    let first = chars.next().unwrap();
    let first_upper = first.is_ascii_uppercase();
    let first_lower = first.is_ascii_lowercase();
    let first_alpha = first.is_ascii_alphabetic();

    // Track what we've seen after the first character
    let mut seen_upper = false;
    let mut seen_lower = false;

    for ch in chars {
        if ch.is_ascii_uppercase() {
            seen_upper = true;
        } else if ch.is_ascii_lowercase() {
            seen_lower = true;
        }
        // Early exit if we've seen both cases after first char - it's mixed
        if seen_upper && seen_lower {
            return CasePattern::Mixed;
        }
    }

    // Now determine the pattern based on first char and rest
    if !first_alpha {
        // First char is not alphabetic
        if seen_upper && !seen_lower {
            return CasePattern::AllUpper;
        }
        if seen_lower && !seen_upper {
            return CasePattern::AllLower;
        }
        if !seen_upper && !seen_lower {
            return CasePattern::AllLower; // No alphabetic chars, treat as lowercase
        }
        return CasePattern::Mixed;
    }

    if first_upper {
        if !seen_lower && !seen_upper {
            // Single uppercase letter
            return CasePattern::AllUpper;
        }
        if seen_lower && !seen_upper {
            // First upper, rest all lower
            return CasePattern::TitleCase;
        }
        if seen_upper && !seen_lower {
            // All uppercase
            return CasePattern::AllUpper;
        }
        // Has both after first - but first was upper
        return CasePattern::Mixed;
    }

    // first_lower
    if seen_upper {
        return CasePattern::Mixed;
    }
    CasePattern::AllLower
}

fn capitalize_ascii(value: &str) -> String {
    let mut chars = value.chars();
    let Some(first) = chars.next() else {
        return String::new();
    };
    let mut result = String::with_capacity(value.len());
    result.push(first.to_ascii_uppercase());
    for ch in chars {
        result.push(ch.to_ascii_lowercase());
    }
    result
}

/// Apply mixed case character-by-character.
fn apply_mixed_case(template: &str, replacement: &str) -> String {
    let mut template_chars = template.chars();
    let mut adjusted = String::with_capacity(replacement.len());
    for repl_char in replacement.chars() {
        let mapped = if let Some(template_char) = template_chars.next() {
            if template_char.is_ascii_uppercase() {
                repl_char.to_ascii_uppercase()
            } else if template_char.is_ascii_lowercase() {
                repl_char.to_ascii_lowercase()
            } else {
                repl_char
            }
        } else {
            repl_char
        };
        adjusted.push(mapped);
    }
    adjusted
}

/// Apply case from template to replacement using single-pass detection.
fn apply_case(template: &str, replacement: &str) -> String {
    match detect_case_pattern(template) {
        CasePattern::Empty => replacement.to_string(),
        CasePattern::AllUpper => replacement.to_ascii_uppercase(),
        CasePattern::AllLower => replacement.to_ascii_lowercase(),
        CasePattern::TitleCase => capitalize_ascii(replacement),
        CasePattern::Mixed => apply_mixed_case(template, replacement),
    }
}

/// Handle suffix harmonization (e.g., "reddish" -> "blueish", not "bluereddish").
fn harmonize_suffix(original: &str, replacement: &str, suffix: &str) -> String {
    if suffix.is_empty() {
        return String::new();
    }

    let original_last = original.chars().rev().find(|ch| ch.is_ascii_alphabetic());
    let suffix_first = suffix.chars().next();
    let replacement_last = replacement
        .chars()
        .rev()
        .find(|ch| ch.is_ascii_alphabetic());

    if let (Some(orig), Some(suff), Some(repl)) = (original_last, suffix_first, replacement_last) {
        if orig.eq_ignore_ascii_case(&suff) && !repl.eq_ignore_ascii_case(&suff) {
            return suffix.chars().skip(1).collect();
        }
    }

    suffix.to_string()
}

/// A validated match with word boundary checks and suffix extraction.
struct ValidatedMatch {
    /// Start byte position in text
    start: usize,
    /// End byte position of the base word (before suffix)
    base_end: usize,
    /// End byte position including any suffix
    full_end: usize,
    /// The lowercase dictionary key for lookup
    dict_key: String,
}

/// Check if a character is a word boundary (not alphanumeric).
#[inline]
fn is_word_boundary_char(c: char) -> bool {
    !c.is_alphanumeric()
}

/// Find valid matches with word boundary checks and suffix detection.
fn find_valid_matches(text: &str, matcher: &LexemeMatcher) -> Vec<ValidatedMatch> {
    let text_bytes = text.as_bytes();
    let text_len = text.len();
    let mut matches = Vec::new();
    let mut last_end = 0usize;

    for mat in matcher.automaton.find_iter(text) {
        let start = mat.start();
        let end = mat.end();

        // Skip overlapping matches (Aho-Corasick with LeftmostLongest should handle this,
        // but we double-check to avoid issues)
        if start < last_end {
            continue;
        }

        // Check word boundary before match
        if start > 0 {
            // Get the character before the match
            let before_start = text[..start].chars().next_back();
            if let Some(c) = before_start {
                if !is_word_boundary_char(c) {
                    continue; // Not at word boundary
                }
            }
        }

        // Check for word boundary or suffix after match
        // We need to find where the word actually ends (including any suffix)
        let mut full_end = end;
        let mut has_suffix = false;

        if end < text_len {
            // Check if there are more alphabetic characters (suffix)
            let rest = &text[end..];
            for c in rest.chars() {
                if c.is_ascii_alphabetic() {
                    full_end += c.len_utf8();
                    has_suffix = true;
                } else {
                    break;
                }
            }

            // After consuming any suffix, check we're at a word boundary
            if full_end < text_len {
                let after_char = text[full_end..].chars().next();
                if let Some(c) = after_char {
                    if !is_word_boundary_char(c) {
                        continue; // Not at word boundary
                    }
                }
            }
        }

        let dict_key = matcher.pattern_keys[mat.pattern().as_usize()].clone();

        matches.push(ValidatedMatch {
            start,
            base_end: end,
            full_end,
            dict_key,
        });

        last_end = full_end;
    }

    matches
}

/// Transform text using the specified dictionary and mode.
fn transform_text(
    text: &str,
    dict_name: &str,
    mode: JargoyleMode,
    rate: f64,
    mut rng: Option<&mut dyn OperationRng>,
) -> Result<String, OperationError> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let dict = match LEXEME_DICTIONARIES.get(dict_name) {
        Some(d) => d,
        None => return Ok(text.to_string()), // Unknown dictionary, return unchanged
    };

    let matcher = match LEXEME_MATCHERS.get(dict_name) {
        Some(m) => m,
        None => return Ok(text.to_string()),
    };

    // Find all valid matches with word boundary checks
    let matches = find_valid_matches(text, matcher);
    if matches.is_empty() {
        return Ok(text.to_string());
    }

    // For rate-based selection, determine which matches to transform
    let indices_to_transform: Vec<usize> = if rate >= 1.0 {
        (0..matches.len()).collect()
    } else if let Some(ref mut r) = rng {
        let clamped_rate = rate.max(0.0).min(1.0);
        let expected = (matches.len() as f64) * clamped_rate;
        let mut max_count = expected.floor() as usize;
        let remainder = expected - (max_count as f64);

        if remainder > 0.0 && r.random()? < remainder {
            max_count += 1;
        }

        // Ensure at least 1 replacement if rate > 0 and we have matches
        if max_count == 0 && rate > 0.0 && !matches.is_empty() {
            max_count = 1;
        }

        max_count = max_count.min(matches.len());
        if max_count == 0 {
            return Ok(text.to_string());
        }

        // Sample indices
        let selected = r.sample_indices(matches.len(), max_count)?;
        let mut sorted: Vec<usize> = selected;
        sorted.sort_unstable();
        sorted
    } else {
        // No RNG, literal mode transforms all
        (0..matches.len()).collect()
    };

    // Estimate result capacity: original length + some growth for longer replacements
    let estimated_growth = (indices_to_transform.len() * 4).min(text.len() / 4);
    let mut result = String::with_capacity(text.len() + estimated_growth);
    let mut cursor = 0usize;
    let mut transform_index = 0usize;

    for (match_index, validated) in matches.iter().enumerate() {
        // Check if this match should be transformed
        let should_transform = transform_index < indices_to_transform.len()
            && indices_to_transform[transform_index] == match_index;

        if should_transform {
            transform_index += 1;
        }

        // Copy text before this match
        result.push_str(&text[cursor..validated.start]);

        let base = &text[validated.start..validated.base_end];
        let suffix = &text[validated.base_end..validated.full_end];

        if should_transform {
            // Look up replacement using the pre-lowercased dictionary key
            let replacement_base = match mode {
                JargoyleMode::Literal => {
                    dict.get(&validated.dict_key)
                        .and_then(|alts| alts.first())
                        .map(|s| s.as_str())
                }
                JargoyleMode::Drift => {
                    if let Some(ref mut r) = rng {
                        if let Some(alternatives) = dict.get(&validated.dict_key) {
                            if !alternatives.is_empty() {
                                let index = r.rand_index(alternatives.len())?;
                                Some(alternatives[index].as_str())
                            } else {
                                None
                            }
                        } else {
                            None
                        }
                    } else {
                        dict.get(&validated.dict_key)
                            .and_then(|alts| alts.first())
                            .map(|s| s.as_str())
                    }
                }
            };

            if let Some(replacement_base) = replacement_base {
                let adjusted = apply_case(base, replacement_base);
                let suffix_fragment = harmonize_suffix(base, replacement_base, suffix);
                result.push_str(&adjusted);
                result.push_str(&suffix_fragment);
            } else {
                // No replacement found, keep original
                result.push_str(&text[validated.start..validated.full_end]);
            }
        } else {
            // Not transforming this match, keep original
            result.push_str(&text[validated.start..validated.full_end]);
        }

        cursor = validated.full_end;
    }

    result.push_str(&text[cursor..]);
    Ok(result)
}

/// Jargoyle pipeline operation for the Gaggle system.
#[derive(Debug, Clone)]
pub struct LexemeSubstitutionOp {
    pub lexemes: String,
    pub mode: JargoyleMode,
    pub rate: f64,
}

impl LexemeSubstitutionOp {
    pub fn new(lexemes: &str, mode: JargoyleMode, rate: f64) -> Self {
        Self {
            lexemes: lexemes.to_string(),
            mode,
            rate,
        }
    }
}

impl TextOperation for LexemeSubstitutionOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        // For the pipeline, we operate on the full text
        let text = buffer.to_string();
        let transformed = transform_text(&text, &self.lexemes, self.mode, self.rate, Some(rng))?;

        // Replace the buffer content
        *buffer = buffer.rebuild_with_patterns(transformed);
        Ok(())
    }
}

/// Python-exposed function for lexeme substitution (word drift).
#[pyfunction(name = "substitute_lexeme", signature = (text, lexemes, mode, rate, seed=None))]
pub(crate) fn substitute_lexeme(
    text: &str,
    lexemes: &str,
    mode: &str,
    rate: f64,
    seed: Option<u64>,
) -> PyResult<String> {
    let parsed_mode = JargoyleMode::parse(mode).map_err(PyValueError::new_err)?;
    let normalized_lexemes = lexemes.to_ascii_lowercase();

    // Validate lexemes
    if !LEXEME_DICTIONARIES.contains_key(&normalized_lexemes) {
        let available = VALID_LEXEMES.join(", ");
        return Err(PyValueError::new_err(format!(
            "Unknown lexemes dictionary '{}'. Available: {available}",
            lexemes
        )));
    }

    match parsed_mode {
        JargoyleMode::Literal => transform_text(text, &normalized_lexemes, parsed_mode, rate, None)
            .map_err(|e| e.into_pyerr()),
        JargoyleMode::Drift => {
            let seed_value = seed.unwrap_or(0);
            let mut rng = DeterministicRng::new(seed_value);
            transform_text(text, &normalized_lexemes, parsed_mode, rate, Some(&mut rng))
                .map_err(|e| e.into_pyerr())
        }
    }
}

/// List available lexeme dictionaries.
#[pyfunction]
pub(crate) fn list_lexeme_dictionaries() -> Vec<String> {
    VALID_LEXEMES.clone()
}

/// List bundled (built-in) lexeme dictionaries embedded at compile time.
#[pyfunction]
pub(crate) fn list_bundled_lexeme_dictionaries() -> Vec<String> {
    let mut names = BUNDLED_LEXEME_NAMES.clone();
    names.sort();
    names
}

/// Check if a lexeme dictionary name refers to a bundled (embedded) dictionary.
#[pyfunction]
pub(crate) fn is_bundled_lexeme(name: &str) -> bool {
    let normalized = name.to_ascii_lowercase();
    BUNDLED_LEXEME_NAMES.contains(&normalized)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_colors_literal_mode() {
        let result = transform_text("red balloon", "colors", JargoyleMode::Literal, 1.0, None)
            .expect("transform should succeed");
        assert_eq!(result, "blue balloon");
    }

    #[test]
    fn test_colors_case_preservation() {
        let result = transform_text("RED balloon", "colors", JargoyleMode::Literal, 1.0, None)
            .expect("transform should succeed");
        assert_eq!(result, "BLUE balloon");

        let result = transform_text("Red balloon", "colors", JargoyleMode::Literal, 1.0, None)
            .expect("transform should succeed");
        assert_eq!(result, "Blue balloon");
    }

    #[test]
    fn test_colors_suffix_handling() {
        let result = transform_text("reddish hue", "colors", JargoyleMode::Literal, 1.0, None)
            .expect("transform should succeed");
        assert_eq!(result, "blueish hue");
    }

    #[test]
    fn test_synonyms_literal_mode() {
        // Both "fast" and "car" are in the synonyms dictionary
        // "fast" -> "rapid" (first synonym)
        // "car" -> "vehicle" (first synonym)
        let result = transform_text("fast car", "synonyms", JargoyleMode::Literal, 1.0, None)
            .expect("transform should succeed");
        assert_eq!(result, "rapid vehicle");
    }

    #[test]
    fn test_drift_mode_deterministic() {
        let mut rng1 = DeterministicRng::new(42);
        let mut rng2 = DeterministicRng::new(42);

        let result1 = transform_text(
            "red green blue",
            "colors",
            JargoyleMode::Drift,
            1.0,
            Some(&mut rng1),
        )
        .expect("transform should succeed");
        let result2 = transform_text(
            "red green blue",
            "colors",
            JargoyleMode::Drift,
            1.0,
            Some(&mut rng2),
        )
        .expect("transform should succeed");

        assert_eq!(result1, result2);
    }

    #[test]
    fn test_unknown_dictionary_unchanged() {
        let result = transform_text(
            "hello world",
            "nonexistent",
            JargoyleMode::Literal,
            1.0,
            None,
        )
        .expect("transform should succeed");
        assert_eq!(result, "hello world");
    }

    #[test]
    fn test_rate_filtering() {
        let mut rng = DeterministicRng::new(123);
        // With rate=0.5 on a 4-word text, we expect ~2 replacements
        let result = transform_text(
            "red green blue yellow",
            "colors",
            JargoyleMode::Drift,
            0.5,
            Some(&mut rng),
        )
        .expect("transform should succeed");
        // The result should have some but not all colors changed
        assert_ne!(result, "red green blue yellow");
    }
}

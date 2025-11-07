use crate::glitch_ops::{GlitchOp, GlitchOpError, GlitchRng};
use crate::rng::DeterministicRng;
use crate::text_buffer::TextBuffer;
use once_cell::sync::Lazy;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashMap;

const VALID_MODE_MESSAGE: &str = "drift, literal";

static CANONICAL_COLOR_MAP: Lazy<HashMap<&'static str, &'static str>> = Lazy::new(|| {
    HashMap::from([
        ("red", "blue"),
        ("blue", "red"),
        ("green", "lime"),
        ("lime", "green"),
        ("yellow", "purple"),
        ("purple", "yellow"),
        ("orange", "cyan"),
        ("cyan", "orange"),
        ("magenta", "teal"),
        ("teal", "magenta"),
        ("black", "white"),
        ("white", "black"),
        ("brown", "maroon"),
        ("maroon", "brown"),
        ("navy", "indigo"),
        ("indigo", "navy"),
        ("olive", "chartreuse"),
        ("chartreuse", "olive"),
        ("pink", "peach"),
        ("peach", "pink"),
        ("gray", "silver"),
        ("silver", "gray"),
        ("grey", "silver"),
    ])
});

static COLOR_ADJACENCY: Lazy<HashMap<&'static str, &'static [&'static str]>> = Lazy::new(|| {
    HashMap::from([
        ("red", &["orange", "magenta", "purple"][..]),
        ("blue", &["cyan", "teal", "purple"][..]),
        ("green", &["teal", "cyan", "yellow"][..]),
        ("lime", &["yellow", "white", "cyan"][..]),
        ("yellow", &["orange", "lime", "white"][..]),
        ("purple", &["magenta", "red", "blue"][..]),
        ("orange", &["red", "yellow", "magenta"][..]),
        ("cyan", &["blue", "green", "teal"][..]),
        ("magenta", &["purple", "red", "blue"][..]),
        ("teal", &["cyan", "green", "blue"][..]),
        ("black", &["purple", "blue", "teal"][..]),
        ("white", &["yellow", "lime", "cyan"][..]),
        ("brown", &["maroon", "orange", "olive"][..]),
        ("maroon", &["brown", "purple", "red"][..]),
        ("navy", &["indigo", "blue", "teal"][..]),
        ("indigo", &["navy", "purple", "blue"][..]),
        ("olive", &["chartreuse", "green", "yellow"][..]),
        ("chartreuse", &["olive", "lime", "yellow"][..]),
        ("pink", &["peach", "magenta", "red"][..]),
        ("peach", &["pink", "orange", "yellow"][..]),
        ("gray", &["silver", "white", "black"][..]),
        ("silver", &["gray", "white", "cyan"][..]),
        ("grey", &["silver", "white", "black"][..]),
    ])
});

static COLOR_PATTERN: Lazy<Regex> = Lazy::new(|| {
    let mut names: Vec<&str> = CANONICAL_COLOR_MAP.keys().copied().collect();
    names.sort_by(|left, right| right.len().cmp(&left.len()));
    let joined = names.join("|");
    let pattern = format!(r"(?i)\b(?P<color>{joined})(?P<suffix>[a-zA-Z]*)\b");
    Regex::new(&pattern).expect("valid color regex")
});

#[derive(Debug, Clone, Copy)]
pub enum SpectrollMode {
    Literal,
    Drift,
}

impl SpectrollMode {
    pub fn parse(mode: &str) -> Result<Self, String> {
        let normalized = mode.to_ascii_lowercase();
        match normalized.as_str() {
            "" => Ok(SpectrollMode::Literal),
            "literal" => Ok(SpectrollMode::Literal),
            "drift" => Ok(SpectrollMode::Drift),
            _ => Err(format!(
                "Unsupported Spectroll mode '{mode}'. Expected one of: {VALID_MODE_MESSAGE}"
            )),
        }
    }
}

fn canonical_replacement(color: &str) -> Option<&'static str> {
    CANONICAL_COLOR_MAP.get(color).copied()
}

fn drift_replacement(
    color: &str,
    rng: &mut dyn GlitchRng,
) -> Result<Option<&'static str>, GlitchOpError> {
    if let Some(palette) = COLOR_ADJACENCY.get(color) {
        if palette.is_empty() {
            return Ok(canonical_replacement(color));
        }
        let index = rng.rand_index(palette.len())?;
        return Ok(Some(palette[index]));
    }
    Ok(canonical_replacement(color))
}

fn is_all_ascii_uppercase(value: &str) -> bool {
    if value.is_empty() {
        return false;
    }
    value.chars().all(|ch| {
        !ch.is_ascii_lowercase() && (!ch.is_ascii_alphabetic() || ch.is_ascii_uppercase())
    })
}

fn is_all_ascii_lowercase(value: &str) -> bool {
    if value.is_empty() {
        return false;
    }
    value.chars().all(|ch| {
        !ch.is_ascii_uppercase() && (!ch.is_ascii_alphabetic() || ch.is_ascii_lowercase())
    })
}

fn is_title_case(value: &str) -> bool {
    let mut chars = value.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    if !first.is_ascii_uppercase() {
        return false;
    }
    chars.all(|ch| !ch.is_ascii_alphabetic() || ch.is_ascii_lowercase())
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

fn apply_case(template: &str, replacement: &str) -> String {
    if template.is_empty() {
        return replacement.to_string();
    }
    if is_all_ascii_uppercase(template) {
        return replacement.to_ascii_uppercase();
    }
    if is_all_ascii_lowercase(template) {
        return replacement.to_ascii_lowercase();
    }
    if is_title_case(template) {
        return capitalize_ascii(replacement);
    }

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
        if orig.to_ascii_lowercase() == suff.to_ascii_lowercase()
            && repl.to_ascii_lowercase() != suff.to_ascii_lowercase()
        {
            return suffix.chars().skip(1).collect();
        }
    }

    suffix.to_string()
}

fn transform_text(
    text: &str,
    mode: SpectrollMode,
    mut rng: Option<&mut dyn GlitchRng>,
) -> Result<String, GlitchOpError> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let mut result = String::with_capacity(text.len());
    let mut cursor = 0usize;

    for captures in COLOR_PATTERN.captures_iter(text) {
        let matched = captures.get(0).expect("match with full capture");
        result.push_str(&text[cursor..matched.start()]);

        let base = captures.name("color").map(|m| m.as_str()).unwrap_or("");
        let suffix = captures.name("suffix").map(|m| m.as_str()).unwrap_or("");
        let canonical = base.to_ascii_lowercase();

        let replacement_base = match mode {
            SpectrollMode::Literal => canonical_replacement(&canonical),
            SpectrollMode::Drift => {
                if let Some(rng_ref) = rng.as_mut() {
                    drift_replacement(&canonical, &mut **rng_ref)?
                } else {
                    canonical_replacement(&canonical)
                }
            }
        };

        if let Some(replacement_base) = replacement_base {
            let adjusted = apply_case(base, replacement_base);
            let suffix_fragment = harmonize_suffix(base, replacement_base, suffix);
            result.push_str(&adjusted);
            result.push_str(&suffix_fragment);
        } else {
            result.push_str(matched.as_str());
        }

        cursor = matched.end();
    }

    result.push_str(&text[cursor..]);
    Ok(result)
}

#[derive(Debug, Clone, Copy)]
pub struct SpectrollOp {
    mode: SpectrollMode,
}

impl SpectrollOp {
    pub fn new(mode: SpectrollMode) -> Self {
        Self { mode }
    }
}

impl GlitchOp for SpectrollOp {
    fn apply(
        &self,
        buffer: &mut TextBuffer,
        rng: &mut dyn crate::glitch_ops::GlitchRng,
    ) -> Result<(), GlitchOpError> {
        if buffer.word_count() == 0 {
            return Ok(());
        }

        // Collect all replacements first to avoid index shifting
        let mut replacements: Vec<(usize, String)> = Vec::new();

        for idx in 0..buffer.word_count() {
            let segment = match buffer.word_segment(idx) {
                Some(seg) => seg,
                None => continue,
            };

            let text = segment.text();

            // Check if this word segment contains any color patterns
            let matches: Vec<_> = COLOR_PATTERN.captures_iter(text).collect();
            if matches.is_empty() {
                continue;
            }

            // Build replacement text by iterating over all matches and splicing in replacements
            let mut result = String::with_capacity(text.len());
            let mut cursor = 0usize;

            for captures in matches {
                let matched = captures.get(0).expect("match with full capture");

                // Preserve text before this match
                result.push_str(&text[cursor..matched.start()]);

                let base = captures.name("color").map(|m| m.as_str()).unwrap_or("");
                let suffix = captures.name("suffix").map(|m| m.as_str()).unwrap_or("");
                let canonical = base.to_ascii_lowercase();

                let replacement_base = match self.mode {
                    SpectrollMode::Literal => canonical_replacement(&canonical),
                    SpectrollMode::Drift => drift_replacement(&canonical, rng)?,
                };

                if let Some(replacement_base) = replacement_base {
                    let adjusted = apply_case(base, replacement_base);
                    let suffix_fragment = harmonize_suffix(base, replacement_base, suffix);
                    result.push_str(&adjusted);
                    result.push_str(&suffix_fragment);
                } else {
                    // No replacement found, keep original
                    result.push_str(matched.as_str());
                }

                cursor = matched.end();
            }

            // Preserve text after the last match
            result.push_str(&text[cursor..]);

            // Only add to replacements if the text actually changed
            if result != text {
                replacements.push((idx, result));
            }
        }

        // Apply all replacements using bulk update
        if !replacements.is_empty() {
            buffer.replace_words_bulk(replacements.into_iter())?;
        }

        Ok(())
    }
}

#[pyfunction(signature = (text, mode, seed=None))]
pub(crate) fn swap_colors(text: &str, mode: &str, seed: Option<u64>) -> PyResult<String> {
    let parsed_mode =
        SpectrollMode::parse(mode).map_err(|message| PyValueError::new_err(message))?;
    let result = match parsed_mode {
        SpectrollMode::Literal => transform_text(text, parsed_mode, None),
        SpectrollMode::Drift => {
            let seed_value = seed.unwrap_or(0);
            let mut rng = DeterministicRng::new(seed_value);
            transform_text(text, parsed_mode, Some(&mut rng))
        }
    };

    result.map_err(|error| error.into_pyerr())
}


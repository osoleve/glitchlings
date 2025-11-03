use once_cell::sync::Lazy;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PySequence, PyString};
use pyo3::Bound;
use serde::Deserialize;
use std::collections::{HashMap, HashSet};

use crate::glitch_ops::{GlitchOp, GlitchOpError, GlitchRng};
use crate::text_buffer::TextBuffer;

const RAW_HOMOGLYPHS: &str = include_str!(concat!(env!("OUT_DIR"), "/mim1c_homoglyphs.json"));

#[derive(Debug, Clone, Deserialize)]
struct RawHomoglyphEntry {
    c: String,
    alias: String,
}

#[derive(Debug, Clone)]
struct HomoglyphEntry {
    glyph: char,
    alias: String,
}

static HOMOGLYPH_TABLE: Lazy<HashMap<char, Vec<HomoglyphEntry>>> = Lazy::new(|| {
    let raw: HashMap<String, Vec<RawHomoglyphEntry>> =
        serde_json::from_str(RAW_HOMOGLYPHS).expect("mim1c homoglyph table should be valid JSON");
    let mut table: HashMap<char, Vec<HomoglyphEntry>> = HashMap::new();
    for (key, entries) in raw {
        if let Some(ch) = key.chars().next() {
            let candidates: Vec<HomoglyphEntry> = entries
                .into_iter()
                .filter_map(|entry| {
                    let mut chars = entry.c.chars();
                    let glyph = chars.next()?;
                    if chars.next().is_some() {
                        return None;
                    }
                    Some(HomoglyphEntry {
                        glyph,
                        alias: entry.alias,
                    })
                })
                .collect();
            if !candidates.is_empty() {
                table.insert(ch, candidates);
            }
        }
    }
    table
});

const DEFAULT_CLASSES: &[&str] = &["LATIN", "GREEK", "CYRILLIC"];

#[derive(Debug, Clone)]
pub enum ClassSelection {
    Default,
    All,
    Specific(Vec<String>),
}

impl ClassSelection {
    fn allows(&self, alias: &str) -> bool {
        match self {
            ClassSelection::All => true,
            ClassSelection::Default => DEFAULT_CLASSES.iter().any(|value| value == &alias),
            ClassSelection::Specific(values) => values.iter().any(|value| value == alias),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Mim1cOp {
    rate: f64,
    classes: ClassSelection,
    banned: Vec<String>,
}

impl Mim1cOp {
    pub fn new(rate: f64, classes: ClassSelection, banned: Vec<String>) -> Self {
        Self {
            rate,
            classes,
            banned,
        }
    }
}

impl GlitchOp for Mim1cOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn GlitchRng) -> Result<(), GlitchOpError> {
        let original = buffer.to_string();
        if original.is_empty() {
            return Ok(());
        }

        let mut targets: Vec<char> = original
            .chars()
            .filter(|ch| ch.is_alphanumeric() && HOMOGLYPH_TABLE.contains_key(ch))
            .collect();

        if targets.is_empty() {
            return Ok(());
        }

        let rate = if self.rate.is_nan() {
            0.0
        } else {
            self.rate.max(0.0)
        };
        if rate == 0.0 {
            return Ok(());
        }

        let mut banned: HashSet<String> = HashSet::new();
        for value in &self.banned {
            if !value.is_empty() {
                banned.insert(value.clone());
            }
        }

        let mut replacements = Vec::new();
        let mut available = targets.len();
        let requested = (targets.len() as f64 * rate).trunc() as usize;
        let mut attempts = 0usize;

        while attempts < requested && available > 0 {
            let idx = rng.rand_index(available)?;
            let ch = targets.swap_remove(idx);
            available -= 1;

            let Some(options) = HOMOGLYPH_TABLE.get(&ch) else {
                continue;
            };

            let mut filtered: Vec<&HomoglyphEntry> = options
                .iter()
                .filter(|entry| {
                    self.classes.allows(&entry.alias)
                        && !banned.contains(&entry.glyph.to_string())
                        && entry.glyph != ch
                })
                .collect();

            if filtered.is_empty() {
                continue;
            }

            let choice = rng.rand_index(filtered.len())?;
            replacements.push((ch, filtered.remove(choice).glyph));
            attempts += 1;
        }

        if replacements.is_empty() {
            return Ok(());
        }

        let mut result = original.clone();
        for (target, replacement) in replacements {
            let needle = target.to_string();
            if let Some(pos) = result.find(&needle) {
                let end = pos + target.len_utf8();
                result.replace_range(pos..end, &replacement.to_string());
            }
        }

        if result != original {
            *buffer = TextBuffer::from_owned(result);
        }

        Ok(())
    }
}

pub fn parse_class_selection(value: Option<Bound<'_, PyAny>>) -> PyResult<ClassSelection> {
    let Some(obj) = value else {
        return Ok(ClassSelection::Default);
    };

    if obj.is_none() {
        return Ok(ClassSelection::Default);
    }

    if let Ok(py_str) = obj.downcast::<PyString>() {
        let value = py_str.to_str()?.to_string();
        if value.eq_ignore_ascii_case("all") {
            return Ok(ClassSelection::All);
        }
        return Ok(ClassSelection::Specific(vec![value]));
    }

    if let Ok(seq) = obj.downcast::<PySequence>() {
        let mut classes: Vec<String> = Vec::new();
        for item in seq.try_iter()? {
            let text: String = item?.extract()?;
            if text.eq_ignore_ascii_case("all") {
                return Ok(ClassSelection::All);
            }
            classes.push(text);
        }
        return Ok(ClassSelection::Specific(classes));
    }

    Err(PyValueError::new_err(
        "classes must be a string or iterable of strings",
    ))
}

pub fn parse_banned_characters(value: Option<Bound<'_, PyAny>>) -> PyResult<Vec<String>> {
    let Some(obj) = value else {
        return Ok(Vec::new());
    };

    if obj.is_none() {
        return Ok(Vec::new());
    }

    if let Ok(py_str) = obj.downcast::<PyString>() {
        return Ok(vec![py_str.to_str()?.to_string()]);
    }

    if let Ok(seq) = obj.downcast::<PySequence>() {
        let mut banned = Vec::new();
        for item in seq.try_iter()? {
            banned.push(item?.extract()?);
        }
        return Ok(banned);
    }

    Err(PyValueError::new_err(
        "banned_characters must be a string or iterable of strings",
    ))
}

#[pyfunction(name = "mim1c", signature = (text, rate=None, classes=None, banned_characters=None, rng=None))]
pub(crate) fn swap_homoglyphs(
    text: &str,
    rate: Option<f64>,
    classes: Option<Bound<'_, PyAny>>,
    banned_characters: Option<Bound<'_, PyAny>>,
    rng: Option<Bound<'_, PyAny>>,
) -> PyResult<String> {
    let rng = rng.ok_or_else(|| PyValueError::new_err("Mim1c requires an RNG instance"))?;
    let rate = rate.unwrap_or(0.02);
    let classes = parse_class_selection(classes)?;
    let banned = parse_banned_characters(banned_characters)?;
    let op = Mim1cOp::new(rate, classes, banned);
    crate::apply_operation(text, op, &rng).map_err(crate::glitch_ops::GlitchOpError::into_pyerr)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::PyRng;

    #[test]
    fn replaces_expected_characters() {
        let mut buffer = TextBuffer::from_str("hello");
        let mut rng = PyRng::new(42);
        let op = Mim1cOp::new(1.0, ClassSelection::Default, Vec::new());
        op.apply(&mut buffer, &mut rng)
            .expect("mim1c operation succeeds");
        assert_ne!(buffer.to_string(), "hello");
    }
}

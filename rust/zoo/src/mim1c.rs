use once_cell::sync::Lazy;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PySequence, PyString};
use pyo3::Bound;
use serde::Deserialize;
use std::collections::{BTreeMap, HashMap, HashSet};

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

static HOMOGLYPH_TABLE: Lazy<BTreeMap<char, Vec<HomoglyphEntry>>> = Lazy::new(|| {
    // Parse JSON into a BTreeMap by explicitly specifying the target type.
    // We use BTreeMap here to ensure deterministic key ordering during iteration.
    let raw: BTreeMap<String, Vec<RawHomoglyphEntry>> =
        serde_json::from_str(RAW_HOMOGLYPHS).expect("mim1c homoglyph table should be valid JSON");
    let mut table: BTreeMap<char, Vec<HomoglyphEntry>> = BTreeMap::new();

    // BTreeMap iterates in sorted key order, so we don't need explicit sorting.
    // Multiple JSON keys can map to the same first character (e.g., "E" and "E̸"
    // both map to 'E'), and BTreeMap ensures consistent ordering.
    for (key, entries) in &raw {
        if let Some(ch) = key.chars().next() {
            let candidates: Vec<HomoglyphEntry> = entries
                .iter()
                .filter_map(|entry| {
                    let mut chars = entry.c.chars();
                    let glyph = chars.next()?;
                    if chars.next().is_some() {
                        return None;
                    }
                    Some(HomoglyphEntry {
                        glyph,
                        alias: entry.alias.clone(),
                    })
                })
                .collect();
            if !candidates.is_empty() {
                // Extend rather than replace to accumulate entries from all
                // related keys (e.g., "E" and "E̸" both contribute to 'E').
                table.entry(ch).or_default().extend(candidates);
            }
        }
    }

    // Sort each character's entries by glyph for fully deterministic ordering.
    // This ensures identical RNG behavior across process invocations.
    for entries in table.values_mut() {
        entries.sort_by_key(|e| e.glyph);
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
        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        // Collect all replaceable characters across all segments
        // Track (segment_index, char_offset_in_segment, char)
        let mut targets: Vec<(usize, usize, char)> = Vec::new();

        for (seg_idx, segment) in segments.iter().enumerate() {
            for (byte_offset, ch) in segment.text().char_indices() {
                if ch.is_alphanumeric() && HOMOGLYPH_TABLE.contains_key(&ch) {
                    targets.push((seg_idx, byte_offset, ch));
                }
            }
        }

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

        // Select characters to replace
        let mut replacements: Vec<(usize, usize, char)> = Vec::new();
        let mut available = targets.len();
        let requested = (targets.len() as f64 * rate).trunc() as usize;
        let mut attempts = 0usize;

        while attempts < requested && available > 0 {
            let idx = rng.rand_index(available)?;
            let (seg_idx, char_offset, ch) = targets.swap_remove(idx);
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
            replacements.push((seg_idx, char_offset, filtered.remove(choice).glyph));
            attempts += 1;
        }

        if replacements.is_empty() {
            return Ok(());
        }

        // Group replacements by segment
        let mut by_segment: HashMap<usize, Vec<(usize, char)>> = HashMap::new();
        for (seg_idx, char_offset, replacement_char) in replacements {
            by_segment
                .entry(seg_idx)
                .or_default()
                .push((char_offset, replacement_char));
        }

        // Build replacement map: segment_index -> modified_text
        let mut segment_replacements: Vec<(usize, String)> = Vec::new();

        // Sort segment indices for deterministic processing order
        let mut seg_indices: Vec<usize> = by_segment.keys().copied().collect();
        seg_indices.sort_unstable();

        for seg_idx in seg_indices {
            let mut seg_replacements = by_segment.remove(&seg_idx).unwrap();
            // Sort by offset in reverse to replace from end to start
            seg_replacements.sort_unstable_by_key(|(offset, _)| *offset);

            let original_text = segments[seg_idx].text();
            let mut modified = original_text.to_string();

            for (char_offset, replacement_char) in seg_replacements.into_iter().rev() {
                if let Some(current_char) = modified[char_offset..].chars().next() {
                    let end = char_offset + current_char.len_utf8();
                    let replacement_str = replacement_char.to_string();
                    modified.replace_range(char_offset..end, &replacement_str);
                }
            }

            segment_replacements.push((seg_idx, modified));
        }

        // Apply all segment replacements in bulk without reparsing
        buffer.replace_segments_bulk(segment_replacements);

        buffer.reindex_if_needed();
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

#[pyfunction(name = "mim1c", signature = (text, rate=None, classes=None, banned_characters=None, seed=None))]
pub(crate) fn swap_homoglyphs(
    text: &str,
    rate: Option<f64>,
    classes: Option<Bound<'_, PyAny>>,
    banned_characters: Option<Bound<'_, PyAny>>,
    seed: Option<u64>,
) -> PyResult<String> {
    let rate = rate.unwrap_or(0.02);
    let classes = parse_class_selection(classes)?;
    let banned = parse_banned_characters(banned_characters)?;
    let op = Mim1cOp::new(rate, classes, banned);
    crate::apply_operation(text, op, seed).map_err(crate::glitch_ops::GlitchOpError::into_pyerr)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::DeterministicRng;

    struct ScriptedRng {
        picks: Vec<usize>,
        position: usize,
    }

    impl ScriptedRng {
        fn new(picks: Vec<usize>) -> Self {
            Self { picks, position: 0 }
        }
    }

    impl GlitchRng for ScriptedRng {
        fn random(&mut self) -> Result<f64, GlitchOpError> {
            unreachable!("random should not be called in scripted tests")
        }

        fn rand_index(&mut self, upper: usize) -> Result<usize, GlitchOpError> {
            let value = self
                .picks
                .get(self.position)
                .copied()
                .expect("scripted RNG ran out of values");
            assert!(value < upper, "scripted pick {value} out of range {upper}");
            self.position += 1;
            Ok(value)
        }

        fn sample_indices(
            &mut self,
            _population: usize,
            _k: usize,
        ) -> Result<Vec<usize>, GlitchOpError> {
            unreachable!("sample_indices should not be called in scripted tests")
        }
    }

    #[test]
    fn replaces_expected_characters() {
        let mut buffer = TextBuffer::from_owned("hello".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        let op = Mim1cOp::new(1.0, ClassSelection::Default, Vec::new());
        op.apply(&mut buffer, &mut rng)
            .expect("mim1c operation succeeds");
        assert_ne!(buffer.to_string(), "hello");
    }

    #[test]
    fn repeated_characters_replace_only_selected_positions() {
        assert!(HOMOGLYPH_TABLE.contains_key(&'o'));
        let options = HOMOGLYPH_TABLE
            .get(&'o')
            .expect("homoglyph table should contain options for 'o'");
        assert!(options.iter().any(|entry| entry.glyph != 'o'));

        let original = "oooo";
        let mut buffer = TextBuffer::from_owned(original.to_string(), &[], &[]);
        let mut rng = ScriptedRng::new(vec![2, 0]);
        let op = Mim1cOp::new(0.3, ClassSelection::All, Vec::new());
        op.apply(&mut buffer, &mut rng)
            .expect("mim1c operation succeeds");

        let result = buffer.to_string();
        assert_ne!(result, original);

        let targets: Vec<(usize, char)> = original
            .char_indices()
            .filter(|(_, ch)| ch.is_alphanumeric() && HOMOGLYPH_TABLE.contains_key(ch))
            .collect();
        assert!(
            targets.len() > 2,
            "expected at least three eligible targets"
        );
        let target_byte_index = targets[2].0;
        let target_char_index = original[..target_byte_index].chars().count();

        let original_chars: Vec<char> = original.chars().collect();
        let result_chars: Vec<char> = result.chars().collect();
        assert_eq!(original_chars.len(), result_chars.len());

        let mut differences = Vec::new();
        for (index, (orig, updated)) in original_chars.iter().zip(result_chars.iter()).enumerate() {
            if orig != updated {
                differences.push(index);
            }
        }

        assert_eq!(differences, vec![target_char_index]);
    }

    #[test]
    fn homoglyph_table_is_sorted_by_glyph() {
        // Verify that the homoglyph table entries are sorted by glyph codepoint
        for (ch, entries) in HOMOGLYPH_TABLE.iter() {
            let mut prev_glyph: Option<char> = None;
            for (idx, entry) in entries.iter().enumerate() {
                if let Some(prev) = prev_glyph {
                    assert!(
                        entry.glyph >= prev,
                        "Entries for '{}' not sorted: entry {} (glyph '{}' U+{:04X}) should come after entry at previous position (glyph '{}' U+{:04X})",
                        ch, idx, entry.glyph, entry.glyph as u32, prev, prev as u32
                    );
                }
                prev_glyph = Some(entry.glyph);
            }
        }
    }

    #[test]
    fn e_homoglyphs_have_expected_order() {
        let entries = HOMOGLYPH_TABLE.get(&'E').expect("E should be in table");
        // Filter to LATIN and GREEK only
        let filtered: Vec<_> = entries
            .iter()
            .filter(|e| e.alias == "LATIN" || e.alias == "GREEK")
            .collect();

        // Should include Ɇ (582), Ε (917), Ｅ (65317) in sorted order
        assert!(
            !filtered.is_empty(),
            "Expected some LATIN/GREEK entries for E"
        );

        // Verify sorted order
        for i in 1..filtered.len() {
            assert!(
                filtered[i].glyph >= filtered[i - 1].glyph,
                "Entries not sorted: {} comes after {}",
                filtered[i].glyph as u32,
                filtered[i - 1].glyph as u32
            );
        }
    }
}

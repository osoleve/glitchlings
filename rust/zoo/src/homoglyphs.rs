use once_cell::sync::Lazy;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PySequence, PyString};
use pyo3::Bound;
use serde::Deserialize;
use std::collections::{BTreeMap, HashMap, HashSet};
use unicode_script::{Script, UnicodeScript};

use crate::operations::{TextOperation, OperationError, OperationRng};
use crate::text_buffer::TextBuffer;

const RAW_HOMOGLYPHS: &str = include_str!(concat!(env!("OUT_DIR"), "/mim1c_homoglyphs.json"));

/// Classification of confusable character pairs based on Unicode Technical Standard #39.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfusableType {
    /// Both source and target characters belong to the same script.
    SingleScript,
    /// Source and target characters belong to different scripts (e.g., Latin↔Cyrillic↔Greek).
    MixedScript,
    /// Target is a compatibility variant (fullwidth, math alphanumerics, etc.).
    Compatibility,
}

/// Substitution mode controlling which confusable types are allowed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum HomoglyphMode {
    /// Only same-script confusables (safest option).
    SingleScript,
    /// Allow cross-script substitutions (Latin↔Cyrillic↔Greek) - default for visual similarity.
    #[default]
    MixedScript,
    /// Include Unicode compatibility variants (fullwidth, math alphanumerics).
    Compatibility,
    /// All confusable types allowed (most aggressive).
    Aggressive,
}

impl HomoglyphMode {
    /// Parse a mode string into HomoglyphMode.
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().replace('-', "_").as_str() {
            "single_script" | "singlescript" | "single" => Some(HomoglyphMode::SingleScript),
            "mixed_script" | "mixedscript" | "mixed" => Some(HomoglyphMode::MixedScript),
            "compatibility" | "compat" => Some(HomoglyphMode::Compatibility),
            "aggressive" | "all" => Some(HomoglyphMode::Aggressive),
            _ => None,
        }
    }

    /// Check if this mode allows a given confusable type.
    fn allows(&self, confusable_type: ConfusableType) -> bool {
        match self {
            HomoglyphMode::SingleScript => confusable_type == ConfusableType::SingleScript,
            HomoglyphMode::MixedScript => matches!(
                confusable_type,
                ConfusableType::SingleScript | ConfusableType::MixedScript
            ),
            HomoglyphMode::Compatibility => matches!(
                confusable_type,
                ConfusableType::SingleScript | ConfusableType::Compatibility
            ),
            HomoglyphMode::Aggressive => true,
        }
    }
}

/// Script affinity weights for weighted selection in MixedScript mode.
/// Higher values indicate more visually plausible substitutions.
fn script_affinity(from: Script, to: Script) -> f64 {
    if from == to {
        return 1.0;
    }
    match (from, to) {
        // Latin ↔ Cyrillic is very visually similar
        (Script::Latin, Script::Cyrillic) | (Script::Cyrillic, Script::Latin) => 0.9,
        // Latin ↔ Greek is also quite similar
        (Script::Latin, Script::Greek) | (Script::Greek, Script::Latin) => 0.8,
        // Cyrillic ↔ Greek
        (Script::Cyrillic, Script::Greek) | (Script::Greek, Script::Cyrillic) => 0.7,
        // Common script includes fullwidth, math, etc.
        (Script::Latin, Script::Common) | (Script::Common, Script::Latin) => 0.7,
        (Script::Cyrillic, Script::Common) | (Script::Common, Script::Cyrillic) => 0.6,
        (Script::Greek, Script::Common) | (Script::Common, Script::Greek) => 0.6,
        // Other transitions are less plausible
        _ => 0.3,
    }
}

/// Determine the confusable type based on source and target characters.
fn classify_confusable(source: char, target: char, target_alias: &str) -> ConfusableType {
    // Check for compatibility variants first (fullwidth, math alphanumerics)
    let target_codepoint = target as u32;

    // Fullwidth ASCII variants (U+FF01-U+FF5E)
    if (0xFF01..=0xFF5E).contains(&target_codepoint) {
        return ConfusableType::Compatibility;
    }

    // Mathematical Alphanumeric Symbols (U+1D400-U+1D7FF)
    if (0x1D400..=0x1D7FF).contains(&target_codepoint) {
        return ConfusableType::Compatibility;
    }

    // Enclosed Alphanumerics (U+2460-U+24FF) and Enclosed CJK Letters (U+3200-U+32FF)
    if (0x2460..=0x24FF).contains(&target_codepoint) || (0x3200..=0x32FF).contains(&target_codepoint) {
        return ConfusableType::Compatibility;
    }

    // Check script-based classification
    let source_script = source.script();
    let target_script = target.script();

    // If same script or one is Common/Inherited, consider it SingleScript
    if source_script == target_script
        || target_script == Script::Common
        || target_script == Script::Inherited
    {
        // But check if the alias indicates a different script
        let alias_upper = target_alias.to_uppercase();
        if alias_is_same_script(&alias_upper, source_script) {
            return ConfusableType::SingleScript;
        }
        // If alias indicates different script, it's mixed
        if is_known_script_alias(&alias_upper) && !alias_is_same_script(&alias_upper, source_script) {
            return ConfusableType::MixedScript;
        }
        return ConfusableType::SingleScript;
    }

    // Different scripts
    ConfusableType::MixedScript
}

/// Check if an alias string indicates the same script as the given script.
fn alias_is_same_script(alias: &str, script: Script) -> bool {
    match script {
        Script::Latin => alias == "LATIN",
        Script::Cyrillic => alias == "CYRILLIC",
        Script::Greek => alias == "GREEK",
        Script::Common => alias == "COMMON",
        Script::Arabic => alias == "ARABIC",
        Script::Hebrew => alias == "HEBREW",
        Script::Han => alias == "HAN" || alias == "CJK",
        Script::Hiragana => alias == "HIRAGANA",
        Script::Katakana => alias == "KATAKANA",
        Script::Hangul => alias == "HANGUL",
        Script::Devanagari => alias == "DEVANAGARI",
        Script::Bengali => alias == "BENGALI",
        Script::Tamil => alias == "TAMIL",
        Script::Thai => alias == "THAI",
        Script::Georgian => alias == "GEORGIAN",
        Script::Armenian => alias == "ARMENIAN",
        Script::Coptic => alias == "COPTIC",
        Script::Ethiopic => alias == "ETHIOPIC",
        Script::Cherokee => alias == "CHEROKEE",
        Script::Runic => alias == "RUNIC",
        Script::Ogham => alias == "OGHAM",
        _ => false,
    }
}

/// Check if an alias is a known script name.
fn is_known_script_alias(alias: &str) -> bool {
    matches!(
        alias,
        "LATIN" | "CYRILLIC" | "GREEK" | "COMMON" | "ARABIC" | "HEBREW" | "HAN" | "CJK"
        | "HIRAGANA" | "KATAKANA" | "HANGUL" | "DEVANAGARI" | "BENGALI" | "TAMIL"
        | "THAI" | "GEORGIAN" | "ARMENIAN" | "COPTIC" | "ETHIOPIC" | "CHEROKEE"
        | "RUNIC" | "OGHAM" | "INHERITED"
    )
}

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

/// Default maximum consecutive substitutions for locality control.
const DEFAULT_MAX_CONSECUTIVE: usize = 3;

#[derive(Debug, Clone)]
pub struct HomoglyphOp {
    rate: f64,
    classes: ClassSelection,
    banned: Vec<String>,
    mode: HomoglyphMode,
    max_consecutive: usize,
}

impl HomoglyphOp {
    pub fn new(rate: f64, classes: ClassSelection, banned: Vec<String>) -> Self {
        Self {
            rate,
            classes,
            banned,
            mode: HomoglyphMode::default(),
            max_consecutive: DEFAULT_MAX_CONSECUTIVE,
        }
    }

    pub fn with_mode(
        rate: f64,
        classes: ClassSelection,
        banned: Vec<String>,
        mode: HomoglyphMode,
        max_consecutive: usize,
    ) -> Self {
        Self {
            rate,
            classes,
            banned,
            mode,
            max_consecutive,
        }
    }
}

impl TextOperation for HomoglyphOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        let segments = buffer.segments();
        if segments.is_empty() {
            return Ok(());
        }

        // Collect all replaceable characters across all segments
        // Track (segment_index, char_offset_in_segment, char, char_position_in_segment)
        let mut targets: Vec<(usize, usize, char, usize)> = Vec::new();

        for (seg_idx, segment) in segments.iter().enumerate() {
            let mut char_pos = 0usize;
            for (byte_offset, ch) in segment.text().char_indices() {
                if ch.is_alphanumeric() && HOMOGLYPH_TABLE.contains_key(&ch) {
                    targets.push((seg_idx, byte_offset, ch, char_pos));
                }
                char_pos += 1;
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
        let mut replacements: Vec<(usize, usize, char, usize)> = Vec::new();
        let mut available = targets.len();
        let requested = (targets.len() as f64 * rate).trunc() as usize;
        let mut attempts = 0usize;

        while attempts < requested && available > 0 {
            let idx = rng.rand_index(available)?;
            let (seg_idx, char_offset, ch, char_pos) = targets.swap_remove(idx);
            available -= 1;

            let Some(options) = HOMOGLYPH_TABLE.get(&ch) else {
                continue;
            };

            // Filter by class selection, banned characters, mode, and confusable type
            let filtered: Vec<(&HomoglyphEntry, ConfusableType)> = options
                .iter()
                .filter_map(|entry| {
                    // Must be allowed by class selection
                    if !self.classes.allows(&entry.alias) {
                        return None;
                    }
                    // Must not be banned
                    if banned.contains(&entry.glyph.to_string()) {
                        return None;
                    }
                    // Must be different from source
                    if entry.glyph == ch {
                        return None;
                    }
                    // Classify and check mode
                    let confusable_type = classify_confusable(ch, entry.glyph, &entry.alias);
                    if !self.mode.allows(confusable_type) {
                        return None;
                    }
                    Some((entry, confusable_type))
                })
                .collect();

            if filtered.is_empty() {
                continue;
            }

            // Select replacement with weighted selection based on script affinity
            let replacement_glyph = if filtered.len() == 1 {
                filtered[0].0.glyph
            } else {
                self.select_with_affinity(ch, &filtered, rng)?
            };

            replacements.push((seg_idx, char_offset, replacement_glyph, char_pos));
            attempts += 1;
        }

        if replacements.is_empty() {
            return Ok(());
        }

        // Apply locality constraint (max_consecutive)
        // Sort by segment then by char position to identify consecutive runs
        replacements.sort_by_key(|(seg_idx, _, _, char_pos)| (*seg_idx, *char_pos));

        let mut filtered_replacements: Vec<(usize, usize, char)> = Vec::new();
        let mut consecutive_count = 0usize;
        let mut last_seg_idx: Option<usize> = None;
        let mut last_char_pos: Option<usize> = None;

        for (seg_idx, char_offset, replacement_char, char_pos) in replacements {
            // Check if this is consecutive with the previous replacement
            let is_consecutive = match (last_seg_idx, last_char_pos) {
                (Some(last_seg), Some(last_pos)) => {
                    seg_idx == last_seg && char_pos == last_pos + 1
                }
                _ => false,
            };

            if is_consecutive {
                consecutive_count += 1;
            } else {
                consecutive_count = 1;
            }

            // Only include if within max_consecutive limit (0 means unlimited)
            if self.max_consecutive == 0 || consecutive_count <= self.max_consecutive {
                filtered_replacements.push((seg_idx, char_offset, replacement_char));
            }

            last_seg_idx = Some(seg_idx);
            last_char_pos = Some(char_pos);
        }

        if filtered_replacements.is_empty() {
            return Ok(());
        }

        // Group replacements by segment
        let mut by_segment: HashMap<usize, Vec<(usize, char)>> = HashMap::new();
        for (seg_idx, char_offset, replacement_char) in filtered_replacements {
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

impl HomoglyphOp {
    /// Select a replacement glyph using weighted selection based on script affinity.
    fn select_with_affinity(
        &self,
        source: char,
        candidates: &[(&HomoglyphEntry, ConfusableType)],
        rng: &mut dyn OperationRng,
    ) -> Result<char, OperationError> {
        let source_script = source.script();

        // Calculate weights based on script affinity
        let weights: Vec<f64> = candidates
            .iter()
            .map(|(entry, _)| script_affinity(source_script, entry.glyph.script()))
            .collect();

        let total_weight: f64 = weights.iter().sum();
        if total_weight <= 0.0 {
            // Fall back to uniform selection
            let idx = rng.rand_index(candidates.len())?;
            return Ok(candidates[idx].0.glyph);
        }

        // Weighted random selection
        let threshold = rng.random()? * total_weight;
        let mut cumulative = 0.0;

        for (idx, weight) in weights.iter().enumerate() {
            cumulative += weight;
            if cumulative >= threshold {
                return Ok(candidates[idx].0.glyph);
            }
        }

        // Fallback to last candidate (shouldn't normally reach here)
        Ok(candidates.last().unwrap().0.glyph)
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

/// Parse mode string into HomoglyphMode, returning None for invalid input.
pub fn parse_homoglyph_mode(value: Option<&str>) -> HomoglyphMode {
    match value {
        Some(s) => HomoglyphMode::from_str(s).unwrap_or_default(),
        None => HomoglyphMode::default(),
    }
}

#[pyfunction(name = "swap_homoglyphs", signature = (text, rate=None, classes=None, banned_characters=None, seed=None, mode=None, max_consecutive=None))]
pub(crate) fn swap_homoglyphs(
    text: &str,
    rate: Option<f64>,
    classes: Option<Bound<'_, PyAny>>,
    banned_characters: Option<Bound<'_, PyAny>>,
    seed: Option<u64>,
    mode: Option<&str>,
    max_consecutive: Option<usize>,
) -> PyResult<String> {
    let rate = rate.unwrap_or(0.02);
    let classes = parse_class_selection(classes)?;
    let banned = parse_banned_characters(banned_characters)?;
    let mode = parse_homoglyph_mode(mode);
    let max_consecutive = max_consecutive.unwrap_or(DEFAULT_MAX_CONSECUTIVE);
    let op = HomoglyphOp::with_mode(rate, classes, banned, mode, max_consecutive);
    crate::apply_operation(text, op, seed).map_err(crate::operations::OperationError::into_pyerr)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::DeterministicRng;

    struct ScriptedRng {
        picks: Vec<usize>,
        randoms: Vec<f64>,
        pick_position: usize,
        random_position: usize,
    }

    impl ScriptedRng {
        fn new(picks: Vec<usize>) -> Self {
            Self {
                picks,
                randoms: Vec::new(),
                pick_position: 0,
                random_position: 0,
            }
        }
    }

    impl OperationRng for ScriptedRng {
        fn random(&mut self) -> Result<f64, OperationError> {
            let value = self
                .randoms
                .get(self.random_position)
                .copied()
                .unwrap_or(0.5); // Default to 0.5 if not specified
            self.random_position += 1;
            Ok(value)
        }

        fn rand_index(&mut self, upper: usize) -> Result<usize, OperationError> {
            let value = self
                .picks
                .get(self.pick_position)
                .copied()
                .expect("scripted RNG ran out of values");
            assert!(value < upper, "scripted pick {value} out of range {upper}");
            self.pick_position += 1;
            Ok(value)
        }

        fn sample_indices(
            &mut self,
            _population: usize,
            _k: usize,
        ) -> Result<Vec<usize>, OperationError> {
            unreachable!("sample_indices should not be called in scripted tests")
        }
    }

    #[test]
    fn replaces_expected_characters() {
        let mut buffer = TextBuffer::from_owned("hello".to_string(), &[], &[]);
        let mut rng = DeterministicRng::new(42);
        let op = HomoglyphOp::new(1.0, ClassSelection::Default, Vec::new());
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
        let op = HomoglyphOp::new(0.3, ClassSelection::All, Vec::new());
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

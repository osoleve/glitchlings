use std::collections::HashSet;
use std::fmt::Write;

use std::sync::LazyLock;
use pyo3::exceptions::PyValueError;
use pyo3::PyErr;
use regex::{Captures, Regex};
use sha2::{Digest, Sha256};

use crate::operations::{TextOperation, OperationError, OperationRng, QuotePairsOp};
use crate::rng::DeterministicRng;
use crate::text_buffer::TextBuffer;

#[derive(Debug, Clone, Copy)]
enum PedantStone {
    Andi,       // Coordinate pronoun hypercorrection
    Infinitoad, // Split infinitive correction
    Aetheria,   // Archaic ligatures/diaeresis
    Apostrofae, // Curly quotes
    Commama,    // Oxford comma insertion
}

impl PedantStone {
    fn try_from_name(name: &str) -> Option<Self> {
        match name {
            "Hypercorrectite" => Some(Self::Andi),
            "Unsplittium" => Some(Self::Infinitoad),
            "Coeurite" => Some(Self::Aetheria),
            "Curlite" => Some(Self::Apostrofae),
            "Oxfordium" => Some(Self::Commama),
            _ => None,
        }
    }

    fn stone_name(self) -> &'static str {
        match self {
            Self::Andi => "Hypercorrectite",
            Self::Infinitoad => "Unsplittium",
            Self::Aetheria => "Coeurite",
            Self::Apostrofae => "Curlite",
            Self::Commama => "Oxfordium",
        }
    }

    fn form_name(self) -> &'static str {
        match self {
            Self::Andi => "Andi",
            Self::Infinitoad => "Infinitoad",
            Self::Aetheria => "Aetheria",
            Self::Apostrofae => "Apostrofae",
            Self::Commama => "Commama",
        }
    }
}

#[derive(Debug, Clone)]
pub struct GrammarRuleOp {
    root_seed: i128,
    stone: PedantStone,
}

impl GrammarRuleOp {
    pub fn new(seed: i128, stone_name: &str) -> Result<Self, PyErr> {
        let stone = PedantStone::try_from_name(stone_name)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown pedant stone: {stone_name}")))?;
        Ok(Self {
            root_seed: seed,
            stone,
        })
    }

    fn lineage(&self) -> [&'static str; 3] {
        ["Pedant", self.stone.stone_name(), self.stone.form_name()]
    }
}

impl TextOperation for GrammarRuleOp {
    fn apply(
        &self,
        buffer: &mut TextBuffer,
        _rng: &mut dyn OperationRng,
    ) -> Result<(), OperationError> {
        let original = buffer.to_string();
        let lineage = self.lineage();
        let transformed = match self.stone {
            PedantStone::Andi => apply_andi(&original),
            PedantStone::Infinitoad => apply_infinitoad(&original, self.root_seed, &lineage)?,
            PedantStone::Aetheria => apply_aetheria(&original, self.root_seed, &lineage)?,
            PedantStone::Apostrofae => apply_curlite(&original, self.root_seed, &lineage)?,
            PedantStone::Commama => apply_commama(&original),
        };

        if transformed != original {
            *buffer = buffer.rebuild_with_patterns(transformed);
        }

        Ok(())
    }
}

/// Coordinate-structure pronoun hypercorrection.
///
/// Targets "X and me" / "me and X" after prepositions and overcorrects to "I".
/// This mimics a common hypercorrection where speakers, taught that "John and me went"
/// is wrong, overgeneralize to "for John and I" in object position.
fn apply_andi(text: &str) -> String {
    // "X and me" after prepositions → "X and I"
    static COORD_AND_ME: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(
            r"(?i)\b(to|for|with|between|from|at|by|about|against|among|around|behind|beside|into|onto|through|toward|towards|upon|without)\s+(\w+(?:\s+\w+)*?)\s+and\s+(me)\b"
        ).expect("valid regex")
    });

    // "me and X" after prepositions → "I and X"
    static ME_AND_COORD: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(
            r"(?i)\b(to|for|with|between|from|at|by|about|against|among|around|behind|beside|into|onto|through|toward|towards|upon|without)\s+(me)\s+and\s+(\w+)\b"
        ).expect("valid regex")
    });

    // "I" as a pronoun is always uppercase in English
    let result = COORD_AND_ME.replace_all(text, |caps: &Captures<'_>| {
        let prep = caps.get(1).unwrap().as_str();
        let other = caps.get(2).unwrap().as_str();
        format!("{prep} {other} and I")
    });

    ME_AND_COORD
        .replace_all(&result, |caps: &Captures<'_>| {
            let prep = caps.get(1).unwrap().as_str();
            let other = caps.get(3).unwrap().as_str();
            format!("{prep} I and {other}")
        })
        .into_owned()
}

/// Split infinitive "correction".
///
/// Moves adverbs out of split infinitive position. The prohibition on split
/// infinitives originated in the 19th century and is considered pedantic today.
/// This function randomly places the adverb before "to" or after the verb.
fn apply_infinitoad(
    text: &str,
    root_seed: i128,
    lineage: &[&str],
) -> Result<String, OperationError> {
    // Pattern: "to" + adverb ending in -ly + verb
    static SPLIT_INF: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"(?i)\bto\s+(\w+ly)\s+(\w+)").expect("valid regex"));

    let matches: Vec<_> = SPLIT_INF.find_iter(text).collect();
    if matches.is_empty() {
        return Ok(text.to_string());
    }

    let seed = derive_seed(
        root_seed,
        lineage,
        &[ReprArg::Str("infinitoad"), ReprArg::Str(text)],
    );
    let mut rng = DeterministicRng::new(seed);

    let result = SPLIT_INF
        .replace_all(text, |caps: &Captures<'_>| {
            let adverb = caps.get(1).unwrap().as_str();
            let verb = caps.get(2).unwrap().as_str();

            // Randomly choose placement: before "to" or after verb
            if rng.random() < 0.5 {
                format!("{adverb} to {verb}")
            } else {
                format!("to {verb} {adverb}")
            }
        })
        .into_owned();

    Ok(result)
}

fn apply_commama(text: &str) -> String {
    static SERIAL_REGEX: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"(,\s*)([^,]+)\s+and\s+([^,]+)").expect("valid regex"));

    SERIAL_REGEX
        .replace_all(text, |caps: &Captures<'_>| {
            let prefix = caps.get(1).unwrap().as_str();
            let penultimate = caps.get(2).unwrap().as_str();
            if penultimate.trim_end().ends_with(',') {
                return caps.get(0).unwrap().as_str().to_string();
            }
            let last = caps.get(3).unwrap().as_str();
            format!("{prefix}{penultimate}, and {last}")
        })
        .into_owned()
}


fn apply_curlite(text: &str, root_seed: i128, lineage: &[&str]) -> Result<String, OperationError> {
    if text.is_empty() {
        return Ok(text.to_string());
    }

    let seed = derive_seed(
        root_seed,
        lineage,
        &[ReprArg::Str("curlite"), ReprArg::Str(text)],
    );
    let mut rng = DeterministicRng::new(seed);
    let mut buffer = TextBuffer::from_owned(text.to_string(), &[], &[]);
    let op = QuotePairsOp;
    op.apply(&mut buffer, &mut rng)?;
    Ok(buffer.to_string())
}

fn apply_aetheria(text: &str, root_seed: i128, lineage: &[&str]) -> Result<String, OperationError> {
    static COOPERATE_REGEX: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"(?i)cooperate").expect("valid regex"));
    static COORDINATE_REGEX: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"(?i)coordinate").expect("valid regex"));

    let intermediate = COOPERATE_REGEX
        .replace_all(text, |caps: &Captures<'_>| {
            cooperate_replacement(caps.get(0).unwrap().as_str())
        })
        .into_owned();

    let word_count = intermediate.split_whitespace().count();

    let mut coordinated = String::with_capacity(intermediate.len());
    let mut last = 0;
    for mat in COORDINATE_REGEX.find_iter(&intermediate) {
        coordinated.push_str(&intermediate[last..mat.start()]);
        let replacement = coordinate_replacement(
            mat.as_str(),
            mat.start(),
            word_count,
            &intermediate,
            root_seed,
            lineage,
        )?;
        coordinated.push_str(&replacement);
        last = mat.end();
    }
    coordinated.push_str(&intermediate[last..]);

    apply_ligatures(&coordinated, root_seed, lineage)
}

fn cooperate_replacement(word: &str) -> String {
    match_casing(word, "coöperate")
}

fn coordinate_replacement(
    word: &str,
    start: usize,
    word_count: usize,
    text: &str,
    root_seed: i128,
    lineage: &[&str],
) -> Result<String, OperationError> {
    if word_count <= 2 && matches!(detect_casing(word), Casing::Title) {
        return Ok(apply_diaeresis(word));
    }

    let seed = derive_seed(
        root_seed,
        lineage,
        &[
            ReprArg::Str("coordinate"),
            ReprArg::Str(text),
            ReprArg::Int(start as i64),
        ],
    );
    let mut rng = DeterministicRng::new(seed);
    if rng.random() < 0.5 {
        Ok(apply_diaeresis(word))
    } else {
        Ok(word.to_string())
    }
}

fn apply_ligatures(text: &str, root_seed: i128, lineage: &[&str]) -> Result<String, OperationError> {
    static AETHER_REGEX: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)ae").expect("valid regex"));

    let matches: Vec<usize> = AETHER_REGEX.find_iter(text).map(|m| m.start()).collect();
    if matches.is_empty() {
        return Ok(text.to_string());
    }

    let seed = derive_seed(
        root_seed,
        lineage,
        &[ReprArg::Str("aetheria"), ReprArg::Str(text)],
    );
    let mut rng = DeterministicRng::new(seed);

    let mut chosen: HashSet<usize> = HashSet::new();
    for &pos in &matches {
        if rng.random() < 0.6 {
            chosen.insert(pos);
        }
    }
    if chosen.is_empty() {
        let index = rng.rand_index(matches.len())?;
        chosen.insert(matches[index]);
    }

    let mut result = String::with_capacity(text.len());
    let mut i = 0;
    while i < text.len() {
        if chosen.contains(&i) {
            let digraph = &text[i..i + 2];
            let replacement = if digraph.chars().all(char::is_uppercase)
                || digraph
                    .chars()
                    .next()
                    .map(char::is_uppercase)
                    .unwrap_or(false)
            {
                "Æ"
            } else {
                "æ"
            };
            result.push_str(replacement);
            i += 2;
        } else {
            let ch = text[i..].chars().next().unwrap();
            result.push(ch);
            i += ch.len_utf8();
        }
    }

    Ok(result)
}

fn apply_diaeresis(word: &str) -> String {
    let lower = word.to_lowercase();
    if let Some(index) = lower.find("oo") {
        let mut result = String::new();
        result.push_str(&word[..index]);
        let mut chars = word[index..].chars();
        let first = chars.next().unwrap();
        let second = chars.next().unwrap_or('o');
        result.push(first);
        if second.is_uppercase() {
            result.push('Ö');
        } else {
            result.push('ö');
        }
        let advance = first.len_utf8() + second.len_utf8();
        result.push_str(&word[index + advance..]);
        result
    } else {
        word.to_string()
    }
}

enum ReprArg<'a> {
    Str(&'a str),
    Int(i64),
}

fn derive_seed(root_seed: i128, lineage: &[&str], parts: &[ReprArg<'_>]) -> u64 {
    let mut hasher = Sha256::new();
    hasher.update(root_seed.to_string().as_bytes());
    for stage in lineage {
        hasher.update(stage.as_bytes());
    }
    for part in parts {
        match part {
            ReprArg::Str(value) => hasher.update(py_repr_str(value).as_bytes()),
            ReprArg::Int(value) => hasher.update(value.to_string().as_bytes()),
        }
    }
    let digest = hasher.finalize();
    let mut bytes = [0u8; 8];
    bytes.copy_from_slice(&digest[..8]);
    u64::from_be_bytes(bytes)
}

fn py_repr_str(value: &str) -> String {
    let mut result = String::with_capacity(value.len() + 2);
    result.push('\'');
    for ch in value.chars() {
        match ch {
            '\\' => result.push_str("\\\\"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            '\'' => result.push_str("\\'"),
            c if c.is_control() => match c as u32 {
                0..=0xFF => {
                    let _ = write!(result, "\\x{:02x}", c as u32);
                }
                0x100..=0xFFFF => {
                    let _ = write!(result, "\\u{:04x}", c as u32);
                }
                _ => {
                    let _ = write!(result, "\\U{:08x}", c as u32);
                }
            },
            c => result.push(c),
        }
    }
    result.push('\'');
    result
}

fn is_cased(ch: char) -> bool {
    ch.is_uppercase() || ch.is_lowercase()
}

#[derive(Debug, Clone, Copy)]
enum Casing {
    Upper,
    Lower,
    Title,
    Other,
}

fn detect_casing(value: &str) -> Casing {
    let mut has_cased = false;
    let mut upper = 0usize;
    let mut lower = 0usize;
    for ch in value.chars() {
        if ch.is_uppercase() {
            has_cased = true;
            upper += 1;
        } else if ch.is_lowercase() {
            has_cased = true;
            lower += 1;
        }
    }
    if !has_cased {
        return Casing::Other;
    }
    if lower == 0 {
        return Casing::Upper;
    }
    if upper == 0 {
        return Casing::Lower;
    }
    let mut chars = value.chars();
    if let Some(first) = chars.next() {
        if first.is_uppercase() && chars.all(|ch| !is_cased(ch) || ch.is_lowercase()) {
            return Casing::Title;
        }
    }
    Casing::Other
}

fn match_casing(source: &str, replacement: &str) -> String {
    match detect_casing(source) {
        Casing::Upper => replacement.to_uppercase(),
        Casing::Lower => replacement.to_lowercase(),
        Casing::Title => {
            let mut chars = replacement.chars();
            if let Some(first) = chars.next() {
                let mut result = String::new();
                result.extend(first.to_uppercase());
                for ch in chars {
                    result.extend(ch.to_lowercase());
                }
                result
            } else {
                String::new()
            }
        }
        Casing::Other => replacement.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cooperate_replacement_respects_casing() {
        assert_eq!(cooperate_replacement("cooperate"), "coöperate");
        assert_eq!(cooperate_replacement("Cooperate"), "Coöperate");
        assert_eq!(cooperate_replacement("COOPERATE"), "COÖPERATE");
    }
}

use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::HashMap;

const RAW_APOSTROFAE_PAIRS: &str = include_str!(concat!(env!("OUT_DIR"), "/apostrofae_pairs.json"));

const RAW_OCR_CONFUSIONS: &str = include_str!(concat!(env!("OUT_DIR"), "/ocr_confusions.tsv"));
const RAW_EKKOKIN_HOMOPHONES: &str =
    include_str!(concat!(env!("OUT_DIR"), "/ekkokin_homophones.json"));

/// Precompiled regex removing spaces before punctuation characters.
pub static SPACE_BEFORE_PUNCTUATION: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\s+([.,;:])").expect("valid punctuation regex"));

/// Precompiled regex collapsing stretches of whitespace into a single space.
pub static MULTIPLE_WHITESPACE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\s{2,}").expect("valid multi-whitespace regex"));

/// Replacement pairs used by the Apostrofae glitchling.
pub static APOSTROFAE_PAIR_TABLE: Lazy<HashMap<char, Vec<(String, String)>>> = Lazy::new(|| {
    let raw: HashMap<String, Vec<[String; 2]>> = serde_json::from_str(RAW_APOSTROFAE_PAIRS)
        .expect("apostrofae pair table should be valid JSON");
    let mut table: HashMap<char, Vec<(String, String)>> = HashMap::new();
    for (key, pairs) in raw {
        if let Some(ch) = key.chars().next() {
            let entries: Vec<(String, String)> = pairs
                .into_iter()
                .map(|pair| (pair[0].to_string(), pair[1].to_string()))
                .collect();
            table.insert(ch, entries);
        }
    }
    table
});

/// Sorted confusion pairs reused by glitchling implementations.
pub static OCR_CONFUSION_TABLE: Lazy<Vec<(&'static str, &'static [&'static str])>> =
    Lazy::new(|| {
        let mut entries: Vec<(usize, (&'static str, &'static [&'static str]))> = Vec::new();

        for (line_number, line) in RAW_OCR_CONFUSIONS.lines().enumerate() {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }

            let mut parts = trimmed.split_whitespace();
            let Some(source) = parts.next() else {
                continue;
            };
            let replacements: Vec<&'static str> = parts.collect();
            if replacements.is_empty() {
                continue;
            }

            let leaked: &'static [&'static str] = Box::leak(replacements.into_boxed_slice());
            entries.push((line_number, (source, leaked)));
        }

        entries.sort_by(|a, b| {
            let a_len = a.1 .0.len();
            let b_len = b.1 .0.len();
            b_len.cmp(&a_len).then_with(|| a.0.cmp(&b.0))
        });

        entries.into_iter().map(|(_, pair)| pair).collect()
    });

/// Parsed homophone sets for the Ekkokin glitchling.
pub static EKKOKIN_HOMOPHONE_SETS: Lazy<Vec<Vec<String>>> = Lazy::new(|| {
    serde_json::from_str(RAW_EKKOKIN_HOMOPHONES)
        .expect("Ekkokin homophone table should be valid JSON")
});

/// Returns the pre-sorted OCR confusion table.
#[inline]
pub fn confusion_table() -> &'static [(&'static str, &'static [&'static str])] {
    OCR_CONFUSION_TABLE.as_slice()
}

/// Returns the parsed homophone sets backing the Ekkokin glitchling.
pub fn ekkokin_homophone_sets() -> &'static [Vec<String>] {
    EKKOKIN_HOMOPHONE_SETS.as_slice()
}

/// Returns the Apostrofae replacement pairs keyed by the straight glyph.
pub fn apostrofae_pairs() -> &'static HashMap<char, Vec<(String, String)>> {
    &APOSTROFAE_PAIR_TABLE
}

#[inline]
pub fn is_whitespace_only(s: &str) -> bool {
    s.chars().all(char::is_whitespace)
}

#[inline]
fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

/// Splits text into alternating word and separator segments while retaining the separators.
pub fn split_with_separators(text: &str) -> Vec<String> {
    // Estimate capacity: roughly one token per 6 characters (average word + separator)
    let estimated_tokens = (text.len() / 6).max(16);
    let mut tokens: Vec<String> = Vec::with_capacity(estimated_tokens);
    let mut last = 0;
    let mut iter = text.char_indices().peekable();

    while let Some((idx, ch)) = iter.next() {
        if ch.is_whitespace() {
            let start = idx;
            let mut end = idx + ch.len_utf8();
            while let Some(&(next_idx, next_ch)) = iter.peek() {
                if next_ch.is_whitespace() {
                    iter.next();
                    end = next_idx + next_ch.len_utf8();
                } else {
                    break;
                }
            }
            tokens.push(text[last..start].to_string());
            tokens.push(text[start..end].to_string());
            last = end;
        }
    }

    if last <= text.len() {
        tokens.push(text[last..].to_string());
    }

    if tokens.is_empty() {
        tokens.push(text.to_string());
    }

    tokens
}

/// Returns the byte bounds of the core token (excluding prefix/suffix punctuation).
pub fn affix_bounds(word: &str) -> Option<(usize, usize)> {
    let mut start_index: Option<usize> = None;
    let mut end_index = 0;

    for (idx, ch) in word.char_indices() {
        if is_word_char(ch) {
            if start_index.is_none() {
                start_index = Some(idx);
            }
            end_index = idx + ch.len_utf8();
        }
    }

    start_index.map(|start| (start, end_index))
}

/// Splits a word into leading punctuation, core token, and trailing punctuation.
pub fn split_affixes(word: &str) -> (String, String, String) {
    match affix_bounds(word) {
        Some((start, end)) => (
            word[..start].to_string(),
            word[start..end].to_string(),
            word[end..].to_string(),
        ),
        None => (word.to_string(), String::new(), String::new()),
    }
}

#[cfg(test)]
mod tests {
    use super::{apostrofae_pairs, confusion_table, split_affixes, split_with_separators};

    #[test]
    fn split_with_separators_matches_expected_boundaries() {
        let parts = split_with_separators(" Hello  world\n");
        assert_eq!(
            parts,
            vec![
                "".to_string(),
                " ".to_string(),
                "Hello".to_string(),
                "  ".to_string(),
                "world".to_string(),
                "\n".to_string(),
                "".to_string()
            ]
        );
    }

    #[test]
    fn split_affixes_retains_punctuation() {
        let (prefix, core, suffix) = split_affixes("(hello)!");
        assert_eq!(prefix, "(");
        assert_eq!(core, "hello");
        assert_eq!(suffix, ")!");
    }

    #[test]
    fn confusion_table_sorted_by_key_length() {
        let table = confusion_table();
        assert!(table.windows(2).all(|pair| {
            let (a_src, _) = pair[0];
            let (b_src, _) = pair[1];
            a_src.len() >= b_src.len()
        }));
    }

    #[test]
    fn apostrofae_pairs_loaded_from_asset() {
        let table = apostrofae_pairs();
        assert!(table.contains_key(&'"'));
        assert!(table.contains_key(&'\''));
        assert!(table.contains_key(&'`'));
        assert!(table.values().all(|entries| !entries.is_empty()));
    }
}

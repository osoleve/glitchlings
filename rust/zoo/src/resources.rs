use once_cell::sync::Lazy;
use regex::Regex;

const RAW_OCR_CONFUSIONS: &str = include_str!(concat!(env!("OUT_DIR"), "/ocr_confusions.tsv"));

/// Precompiled regex removing spaces before punctuation characters.
pub static SPACE_BEFORE_PUNCTUATION: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\s+([.,;:])").expect("valid punctuation regex"));

/// Precompiled regex collapsing stretches of whitespace into a single space.
pub static MULTIPLE_WHITESPACE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\s{2,}").expect("valid multi-whitespace regex"));

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

/// Returns the pre-sorted OCR confusion table.
#[inline]
pub fn confusion_table() -> &'static [(&'static str, &'static [&'static str])] {
    OCR_CONFUSION_TABLE.as_slice()
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
    let mut tokens: Vec<String> = Vec::new();
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

/// Splits a word into leading punctuation, core token, and trailing punctuation.
pub fn split_affixes(word: &str) -> (String, String, String) {
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

    match start_index {
        Some(start) => (
            word[..start].to_string(),
            word[start..end_index].to_string(),
            word[end_index..].to_string(),
        ),
        None => (word.to_string(), String::new(), String::new()),
    }
}

#[cfg(test)]
mod tests {
    use super::{confusion_table, split_affixes, split_with_separators};

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
}

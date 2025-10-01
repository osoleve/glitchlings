use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule};
use pyo3::Bound;
use regex::{Captures, Regex};

#[inline]
fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

fn is_whitespace_only(s: &str) -> bool {
    s.chars().all(char::is_whitespace)
}

fn split_with_separators(text: &str) -> Vec<String> {
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

fn split_affixes(word: &str) -> (String, String, String) {
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

fn random_unit(rng: &Bound<'_, PyAny>) -> PyResult<f64> {
    rng.call_method0("random")?.extract()
}

fn rand_index(rng: &Bound<'_, PyAny>, upper: usize) -> PyResult<usize> {
    rng.call_method1("randrange", (upper,))?.extract()
}

#[pyfunction]
fn reduplicate_words(
    text: &str,
    reduplication_rate: f64,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let mut tokens = split_with_separators(text);
    let mut i = 0;
    while i < tokens.len() {
        let word = tokens[i].clone();
        if word.is_empty() || is_whitespace_only(&word) {
            i += 2;
            continue;
        }
        if random_unit(rng)? < reduplication_rate {
            let (prefix, core, suffix) = split_affixes(&word);
            tokens[i] = format!("{prefix}{core} {core}{suffix}");
        }
        i += 2;
    }

    Ok(tokens.concat())
}

#[pyfunction]
fn delete_random_words(
    text: &str,
    max_deletion_rate: f64,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let mut tokens = split_with_separators(text);
    let mut i = 2;
    while i < tokens.len() {
        let word = tokens[i].clone();
        if word.is_empty() || is_whitespace_only(&word) {
            i += 2;
            continue;
        }
        if random_unit(rng)? < max_deletion_rate {
            let (prefix, _, suffix) = split_affixes(&word);
            let trimmed_prefix = prefix.trim();
            let trimmed_suffix = suffix.trim();
            tokens[i] = format!("{trimmed_prefix}{trimmed_suffix}");
        }
        i += 2;
    }

    let mut joined = tokens.concat();
    if joined.is_empty() {
        return Ok(joined);
    }

    let re_space_punct = Regex::new(r"\s+([.,;:])").unwrap();
    joined = re_space_punct.replace_all(&joined, "$1").into_owned();

    let re_multi_space = Regex::new(r"\s{2,}").unwrap();
    joined = re_multi_space.replace_all(&joined, " ").into_owned();

    Ok(joined.trim().to_string())
}

struct Candidate {
    start: usize,
    end: usize,
    choices: &'static [&'static str],
}

const CONFUSION_TABLE: &[(&str, &[&str])] = &[
    ("li", &["h"]),
    ("h", &["li"]),
    ("rn", &["m"]),
    ("m", &["rn"]),
    ("cl", &["d"]),
    ("d", &["cl"]),
    ("I", &["l"]),
    ("l", &["I", "1"]),
    ("1", &["l", "I"]),
    ("0", &["O"]),
    ("O", &["0"]),
    ("B", &["8"]),
    ("8", &["B"]),
    ("S", &["5"]),
    ("5", &["S"]),
    ("Z", &["2"]),
    ("2", &["Z"]),
    ("G", &["6"]),
    ("6", &["G"]),
    ("“", &["\""]),
    ("”", &["\""]),
    ("‘", &["'"]),
    ("’", &["'"]),
    ("—", &["-"]),
    ("–", &["-"]),
];

#[pyfunction]
fn ocr_artifacts(text: &str, error_rate: f64, rng: &Bound<'_, PyAny>) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let mut table: Vec<(&str, &[&str])> = CONFUSION_TABLE.iter().copied().collect();
    table.sort_by(|a, b| b.0.len().cmp(&a.0.len()));

    let mut candidates: Vec<Candidate> = Vec::new();
    for (src, choices) in table {
        for (start, _) in text.match_indices(src) {
            let end = start + src.len();
            candidates.push(Candidate {
                start,
                end,
                choices,
            });
        }
    }

    if candidates.is_empty() {
        return Ok(text.to_string());
    }

    let mut to_select = (candidates.len() as f64 * error_rate).floor() as usize;
    if to_select == 0 {
        return Ok(text.to_string());
    }

    let mut i = candidates.len();
    while i > 1 {
        i -= 1;
        let j = rand_index(rng, i + 1)?;
        candidates.swap(i, j);
    }

    let mut chosen: Vec<(usize, usize, &'static str)> = Vec::with_capacity(to_select);
    let mut occupied: Vec<(usize, usize)> = Vec::new();

    for candidate in candidates {
        if chosen.len() >= to_select {
            break;
        }
        if occupied
            .iter()
            .any(|&(s, e)| !(candidate.end <= s || e <= candidate.start))
        {
            continue;
        }
        if candidate.choices.is_empty() {
            continue;
        }
        let idx = rand_index(rng, candidate.choices.len())?;
        let replacement = candidate.choices[idx];
        chosen.push((candidate.start, candidate.end, replacement));
        occupied.push((candidate.start, candidate.end));
    }

    if chosen.is_empty() {
        return Ok(text.to_string());
    }

    chosen.sort_by_key(|&(start, _, _)| start);
    let mut output = String::with_capacity(text.len());
    let mut cursor = 0;
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

    Ok(output)
}

#[pyfunction]
fn redact_words(
    text: &str,
    replacement_char: &str,
    redaction_rate: f64,
    merge_adjacent: bool,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let mut tokens = split_with_separators(text);
    let word_indices: Vec<usize> = tokens
        .iter()
        .enumerate()
        .filter_map(|(i, token)| {
            if i % 2 == 0 && !token.trim().is_empty() {
                Some(i)
            } else {
                None
            }
        })
        .collect();

    if word_indices.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "No words found to redact",
        ));
    }

    let mut num_to_redact = (word_indices.len() as f64 * redaction_rate).floor() as usize;
    if num_to_redact < 1 {
        num_to_redact = 1;
    }
    if num_to_redact > word_indices.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Cannot redact more words than available in text",
        ));
    }

    let mut pool = word_indices.clone();
    let mut selected: Vec<usize> = Vec::with_capacity(num_to_redact);
    let mut remaining = pool.len();
    for _ in 0..num_to_redact {
        let idx = rand_index(rng, remaining)?;
        selected.push(pool[idx]);
        pool.swap(idx, remaining - 1);
        remaining -= 1;
    }
    selected.sort_unstable();

    for index in selected {
        if index >= tokens.len() {
            continue;
        }
        let original = tokens[index].clone();
        if original.is_empty() || is_whitespace_only(&original) {
            continue;
        }
        let (prefix, core, suffix) = split_affixes(&original);
        let core_len = core.chars().count();
        if core_len == 0 {
            tokens[index] = original;
            continue;
        }
        let mut replacement =
            String::with_capacity(prefix.len() + suffix.len() + replacement_char.len() * core_len);
        replacement.push_str(&prefix);
        for _ in 0..core_len {
            replacement.push_str(replacement_char);
        }
        replacement.push_str(&suffix);
        tokens[index] = replacement;
    }

    let mut result = tokens.concat();

    if merge_adjacent {
        let pattern = format!(
            "{}\\W+{}",
            regex::escape(replacement_char),
            regex::escape(replacement_char)
        );
        let regex = Regex::new(&pattern).unwrap();
        result = regex
            .replace_all(&result, |caps: &Captures| {
                let matched = caps.get(0).unwrap().as_str();
                let repeat = matched.chars().count().saturating_sub(1);
                let mut builder = String::new();
                for _ in 0..repeat {
                    builder.push_str(replacement_char);
                }
                builder
            })
            .into_owned();
    }

    Ok(result)
}

#[pymodule]
fn _zoo_rust(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(reduplicate_words, m)?)?;
    m.add_function(wrap_pyfunction!(delete_random_words, m)?)?;
    m.add_function(wrap_pyfunction!(ocr_artifacts, m)?)?;
    m.add_function(wrap_pyfunction!(redact_words, m)?)?;
    Ok(())
}

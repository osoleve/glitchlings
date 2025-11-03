use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use pyo3::Bound;
use std::collections::HashMap;
use std::sync::{Arc, OnceLock, RwLock};

type CachedLayouts = HashMap<usize, Arc<HashMap<String, Vec<String>>>>;

fn layout_cache() -> &'static RwLock<CachedLayouts> {
    static CACHE: OnceLock<RwLock<CachedLayouts>> = OnceLock::new();
    CACHE.get_or_init(|| RwLock::new(HashMap::new()))
}

fn extract_layout_map(layout: &Bound<'_, PyDict>) -> PyResult<Arc<HashMap<String, Vec<String>>>> {
    let key = layout.as_ptr() as usize;
    if let Some(cached) = layout_cache()
        .read()
        .expect("layout cache poisoned")
        .get(&key)
    {
        return Ok(cached.clone());
    }

    let mut materialised: HashMap<String, Vec<String>> = HashMap::new();
    for (entry_key, entry_value) in layout.iter() {
        materialised.insert(entry_key.extract()?, entry_value.extract()?);
    }
    let arc = Arc::new(materialised);

    let mut guard = layout_cache()
        .write()
        .expect("layout cache poisoned during write");
    let entry = guard.entry(key).or_insert_with(|| arc.clone());
    Ok(entry.clone())
}

#[inline]
fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

fn eligible_idx(chars: &[char], i: usize) -> bool {
    if i >= chars.len() {
        return false;
    }
    let c = chars[i];
    if !is_word_char(c) {
        return false;
    }
    if i == 0 || i + 1 >= chars.len() {
        return false;
    }
    is_word_char(chars[i - 1]) && is_word_char(chars[i + 1])
}

fn draw_eligible_index(
    rng: &Bound<'_, PyAny>,
    chars: &[char],
    max_tries: usize,
) -> PyResult<Option<usize>> {
    let n = chars.len();
    if n == 0 {
        return Ok(None);
    }

    for _ in 0..max_tries {
        let idx = python_rand_index(rng, n)?;
        if eligible_idx(chars, idx) {
            return Ok(Some(idx));
        }
    }

    let start = python_rand_index(rng, n)?;
    if !eligible_idx(chars, start) {
        let mut i = (start + 1) % n;
        while i != start {
            if eligible_idx(chars, i) {
                return Ok(Some(i));
            }
            i = (i + 1) % n;
        }
        Ok(None)
    } else {
        Ok(Some(start))
    }
}

fn neighbors_for_char<'a>(
    layout: &'a HashMap<String, Vec<String>>,
    ch: char,
) -> Option<&'a [String]> {
    let lowered: String = ch.to_lowercase().collect();
    layout.get(lowered.as_str()).map(|values| values.as_slice())
}

fn python_rand_index(rng: &Bound<'_, PyAny>, upper: usize) -> PyResult<usize> {
    rng.call_method1("randrange", (upper,))?.extract()
}

fn python_randrange(rng: &Bound<'_, PyAny>, start: usize, stop: usize) -> PyResult<usize> {
    rng.call_method1("randrange", (start, stop))?.extract()
}

fn remove_space(rng: &Bound<'_, PyAny>, chars: &mut Vec<char>) -> PyResult<()> {
    let positions: Vec<usize> = chars
        .iter()
        .enumerate()
        .filter_map(|(i, &c)| if c == ' ' { Some(i) } else { None })
        .collect();
    if positions.is_empty() {
        return Ok(());
    }
    let choice = python_rand_index(rng, positions.len())?;
    let idx = positions[choice];
    if idx < chars.len() {
        chars.remove(idx);
    }
    Ok(())
}

fn insert_space(rng: &Bound<'_, PyAny>, chars: &mut Vec<char>) -> PyResult<()> {
    if chars.len() < 2 {
        return Ok(());
    }
    let stop = chars.len();
    let idx = python_randrange(rng, 1, stop)?;
    if idx <= chars.len() {
        chars.insert(idx, ' ');
    }
    Ok(())
}

fn repeat_char(rng: &Bound<'_, PyAny>, chars: &mut Vec<char>) -> PyResult<()> {
    let positions: Vec<usize> = chars
        .iter()
        .enumerate()
        .filter_map(|(i, &c)| if c.is_whitespace() { None } else { Some(i) })
        .collect();
    if positions.is_empty() {
        return Ok(());
    }
    let choice = python_rand_index(rng, positions.len())?;
    let idx = positions[choice];
    if idx < chars.len() {
        let c = chars[idx];
        chars.insert(idx, c);
    }
    Ok(())
}

fn collapse_duplicate(rng: &Bound<'_, PyAny>, chars: &mut Vec<char>) -> PyResult<()> {
    if chars.len() < 3 {
        return Ok(());
    }
    let mut matches: Vec<usize> = Vec::new();
    let mut i = 0;
    while i + 1 < chars.len() {
        if chars[i] == chars[i + 1] && i + 2 < chars.len() && is_word_char(chars[i + 2]) {
            matches.push(i);
            i += 2;
        } else {
            i += 1;
        }
    }
    if matches.is_empty() {
        return Ok(());
    }
    let choice = python_rand_index(rng, matches.len())?;
    let start = matches[choice];
    if start + 1 < chars.len() {
        chars.remove(start + 1);
    }
    Ok(())
}

fn positional_action(
    rng: &Bound<'_, PyAny>,
    action: usize,
    chars: &mut Vec<char>,
    layout: &HashMap<String, Vec<String>>,
) -> PyResult<()> {
    let Some(idx) = draw_eligible_index(rng, chars, 16)? else {
        return Ok(());
    };

    match action {
        0 => {
            if idx + 1 < chars.len() {
                chars.swap(idx, idx + 1);
            }
        }
        1 => {
            if eligible_idx(chars, idx) {
                chars.remove(idx);
            }
        }
        2 => {
            if idx < chars.len() {
                let ch = chars[idx];
                let insertion = match neighbors_for_char(layout, ch) {
                    Some(neighbors) if !neighbors.is_empty() => {
                        let choice = python_rand_index(rng, neighbors.len())?;
                        neighbors[choice].clone()
                    }
                    _ => {
                        // Maintain RNG parity with the historical implementation when no neighbours exist.
                        python_rand_index(rng, 1)?;
                        ch.to_string()
                    }
                };
                let insert_chars: Vec<char> = insertion.chars().collect();
                chars.splice(idx..idx, insert_chars);
            }
        }
        3 => {
            if idx < chars.len() {
                let ch = chars[idx];
                if let Some(neighbors) = neighbors_for_char(layout, ch) {
                    if neighbors.is_empty() {
                        return Ok(());
                    }
                    let choice = python_rand_index(rng, neighbors.len())?;
                    let replacement: Vec<char> = neighbors[choice].chars().collect();
                    chars.splice(idx..idx + 1, replacement);
                }
            }
        }
        _ => {}
    }

    Ok(())
}

fn global_action(rng: &Bound<'_, PyAny>, action: &str, chars: &mut Vec<char>) -> PyResult<()> {
    match action {
        "skipped_space" => remove_space(rng, chars)?,
        "random_space" => insert_space(rng, chars)?,
        "unichar" => collapse_duplicate(rng, chars)?,
        "repeated_char" => repeat_char(rng, chars)?,
        _ => {}
    }
    Ok(())
}

#[pyfunction]
pub(crate) fn fatfinger(
    text: &str,
    max_change_rate: f64,
    layout: &Bound<'_, PyDict>,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let mut chars: Vec<char> = text.chars().collect();
    let layout_map = extract_layout_map(layout)?;

    let length = chars.len();
    let mut max_changes = (length as f64 * max_change_rate).ceil() as usize;
    if max_changes < 1 {
        max_changes = 1;
    }

    const POSITIONAL_COUNT: usize = 4;
    const TOTAL_ACTIONS: usize = 8;
    let mut actions: Vec<u8> = Vec::with_capacity(max_changes);
    for _ in 0..max_changes {
        let action_idx = python_rand_index(rng, TOTAL_ACTIONS)?;
        actions.push(action_idx as u8);
    }

    for action_idx in actions {
        let action_idx = action_idx as usize;
        if action_idx < POSITIONAL_COUNT {
            positional_action(rng, action_idx, &mut chars, layout_map.as_ref())?;
        } else {
            let action = match action_idx {
                4 => "skipped_space",
                5 => "random_space",
                6 => "unichar",
                7 => "repeated_char",
                _ => unreachable!("action index out of range"),
            };
            global_action(rng, action, &mut chars)?;
        }
    }

    Ok(chars.into_iter().collect())
}

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};
use pyo3::Bound;
use std::collections::HashMap;

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
        let idx: usize = rng.call_method1("randrange", (n,))?.extract()?;
        if eligible_idx(chars, idx) {
            return Ok(Some(idx));
        }
    }

    let start: usize = rng.call_method1("randrange", (n,))?.extract()?;
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

fn neighbors_for_char(layout: &HashMap<String, Vec<String>>, ch: char) -> Vec<String> {
    let lowered: String = ch.to_lowercase().collect();
    layout.get(&lowered).cloned().unwrap_or_default()
}

fn python_choice<'py, T>(rng: &Bound<'py, PyAny>, candidates: &[T]) -> PyResult<Py<PyAny>>
where
    T: ToPyObject,
{
    let list = PyList::new_bound(rng.py(), candidates);
    Ok(rng.call_method1("choice", (&list,))?.into())
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
    let idx_obj = python_choice(rng, &positions)?;
    let idx: usize = idx_obj.extract(rng.py())?;
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
    let idx: usize = rng.call_method1("randrange", (1, stop))?.extract()?;
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
    let idx_obj = python_choice(rng, &positions)?;
    let idx: usize = idx_obj.extract(rng.py())?;
    if idx <= chars.len() {
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
    let idx_obj = python_choice(rng, &matches)?;
    let start: usize = idx_obj.extract(rng.py())?;
    if start + 1 < chars.len() {
        chars.remove(start + 1);
    }
    Ok(())
}

fn positional_action(
    rng: &Bound<'_, PyAny>,
    action: &str,
    chars: &mut Vec<char>,
    layout: &HashMap<String, Vec<String>>,
) -> PyResult<()> {
    let Some(idx) = draw_eligible_index(rng, chars, 16)? else {
        return Ok(());
    };

    match action {
        "char_swap" => {
            if idx + 1 < chars.len() {
                chars.swap(idx, idx + 1);
            }
        }
        "missing_char" => {
            if eligible_idx(chars, idx) {
                chars.remove(idx);
            }
        }
        "extra_char" => {
            if idx <= chars.len() {
                let ch = chars[idx];
                let mut neighbors = neighbors_for_char(layout, ch);
                if neighbors.is_empty() {
                    neighbors.push(ch.to_string());
                }
                let choice = python_choice(rng, &neighbors)?;
                let ins: String = choice.extract(rng.py())?;
                let insert_chars: Vec<char> = ins.chars().collect();
                chars.splice(idx..idx, insert_chars);
            }
        }
        "nearby_char" => {
            let ch = chars[idx];
            let neighbors = neighbors_for_char(layout, ch);
            if !neighbors.is_empty() {
                let choice = python_choice(rng, &neighbors)?;
                let replacement: String = choice.extract(rng.py())?;
                let rep_chars: Vec<char> = replacement.chars().collect();
                if idx < chars.len() {
                    chars.splice(idx..idx + 1, rep_chars);
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
fn fatfinger(
    text: &str,
    max_change_rate: f64,
    layout: &Bound<'_, PyDict>,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let mut chars: Vec<char> = text.chars().collect();
    let mut layout_map: HashMap<String, Vec<String>> = HashMap::new();
    for (key, value) in layout.iter() {
        let key: String = key.extract()?;
        let values: Vec<String> = value.extract()?;
        layout_map.insert(key, values);
    }

    let length = chars.len();
    let mut max_changes = (length as f64 * max_change_rate).floor() as usize;
    if max_changes < 1 {
        max_changes = 1;
    }

    let positional = ["char_swap", "missing_char", "extra_char", "nearby_char"];
    let global = ["skipped_space", "random_space", "unichar", "repeated_char"];
    let mut all_actions = Vec::with_capacity(positional.len() + global.len());
    all_actions.extend_from_slice(&positional);
    all_actions.extend_from_slice(&global);

    let mut actions = Vec::with_capacity(max_changes);
    for _ in 0..max_changes {
        let action_obj = python_choice(rng, &all_actions)?;
        let action: String = action_obj.extract(rng.py())?;
        actions.push(action);
    }

    for action in actions {
        if positional.contains(&action.as_str()) {
            positional_action(rng, &action, &mut chars, &layout_map)?;
        } else {
            global_action(rng, &action, &mut chars)?;
        }
    }

    Ok(chars.into_iter().collect())
}

#[pymodule]
fn _typogre_rust(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fatfinger, m)?)?;
    Ok(())
}

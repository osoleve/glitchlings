use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3::Bound;

#[pyfunction]
pub(crate) fn inject_zero_widths(
    text: &str,
    rate: f64,
    characters: &Bound<'_, PyAny>,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let mut palette: Vec<String> = characters.extract()?;
    palette.retain(|entry| !entry.is_empty());
    if palette.is_empty() {
        return Ok(text.to_string());
    }

    let chars: Vec<char> = text.chars().collect();
    if chars.len() < 2 {
        return Ok(text.to_string());
    }

    let mut positions: Vec<usize> = Vec::new();
    for index in 0..(chars.len() - 1) {
        if !chars[index].is_whitespace() && !chars[index + 1].is_whitespace() {
            positions.push(index + 1);
        }
    }

    if positions.is_empty() {
        return Ok(text.to_string());
    }

    let clamped_rate = if rate.is_nan() { 0.0 } else { rate.max(0.0) };
    if clamped_rate <= 0.0 {
        return Ok(text.to_string());
    }

    let total = positions.len();
    let target = clamped_rate * total as f64;
    let mut count = target.floor() as usize;
    let remainder = target - count as f64;

    if remainder > 0.0 {
        let draw: f64 = rng.call_method0("random")?.extract()?;
        if draw < remainder {
            count += 1;
        }
    }

    if count > total {
        count = total;
    }

    if count == 0 {
        return Ok(text.to_string());
    }

    let py = rng.py();
    let positions_list = PyList::new_bound(py, &positions);
    let sample_obj = rng.call_method1("sample", (&positions_list, count))?;
    let mut chosen: Vec<usize> = sample_obj.extract()?;
    chosen.sort_unstable();

    let palette_list = PyList::new_bound(py, &palette);

    let mut result = String::with_capacity(text.len() + count);
    let mut iter = chosen.into_iter();
    let mut next_insert = iter.next();

    for (index, ch) in chars.iter().enumerate() {
        result.push(*ch);
        let insert_pos = index + 1;
        if let Some(pos) = next_insert {
            if pos == insert_pos {
                let choice_obj = rng.call_method1("choice", (&palette_list,))?;
                let insertion: String = choice_obj.extract()?;
                result.push_str(&insertion);
                next_insert = iter.next();
            }
        }
    }

    Ok(result)
}

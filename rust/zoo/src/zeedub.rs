use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3::Bound;

fn python_rand_index(rng: &Bound<'_, PyAny>, upper: usize) -> PyResult<usize> {
    rng.call_method1("randrange", (upper,))?.extract()
}

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
    let positions_list = PyList::new(py, &positions)?;
    let sample_obj = rng.call_method1("sample", (&positions_list, count))?;
    let mut chosen: Vec<usize> = sample_obj.extract()?;
    chosen.sort_unstable();

    let mut inserts: Vec<(usize, String)> = Vec::with_capacity(chosen.len());
    for &position in chosen.iter().rev() {
        let index = python_rand_index(rng, palette.len())?;
        inserts.push((position, palette[index].clone()));
    }
    inserts.sort_unstable_by_key(|(position, _)| *position);

    let mut result = String::with_capacity(text.len() + count);
    let mut iter = inserts.into_iter().peekable();

    for (index, ch) in chars.iter().enumerate() {
        result.push(*ch);
        let insert_pos = index + 1;
        if let Some((target_index, insertion)) = iter.peek() {
            if *target_index == insert_pos {
                result.push_str(insertion);
                iter.next();
            }
        }
    }

    Ok(result)
}

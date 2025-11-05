use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3::Bound;

#[pyfunction(signature = (text, rate, characters, seed=None))]
pub(crate) fn inject_zero_widths(
    text: &str,
    rate: f64,
    characters: &Bound<'_, PyAny>,
    seed: Option<u64>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let list = characters.downcast::<PyList>()?;
    let palette: Vec<String> = list
        .iter()
        .map(|item| item.extract())
        .collect::<PyResult<_>>()?;
    if palette.is_empty() {
        return Ok(text.to_string());
    }

    let op = crate::glitch_ops::ZeroWidthOp {
        rate,
        characters: palette,
    };
    crate::apply_operation(text, op, seed).map_err(crate::glitch_ops::GlitchOpError::into_pyerr)
}

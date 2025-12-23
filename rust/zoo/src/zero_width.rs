use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3::Bound;

use crate::operations::{PlacementMode, VisibilityMode, ZeroWidthOp};

#[pyfunction(signature = (text, rate, characters, seed=None, visibility=None, placement=None, max_consecutive=None))]
pub(crate) fn inject_zero_widths(
    text: &str,
    rate: f64,
    characters: &Bound<'_, PyAny>,
    seed: Option<u64>,
    visibility: Option<&str>,
    placement: Option<&str>,
    max_consecutive: Option<usize>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let list = characters.downcast::<PyList>()?;
    let palette: Vec<String> = list
        .iter()
        .map(|item| item.extract())
        .collect::<PyResult<_>>()?;

    let visibility_mode = visibility
        .map(|s| {
            VisibilityMode::from_str(s).ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Invalid visibility mode: '{s}'. Expected 'glyphless', 'with_joiners', or 'semi_visible'"
                ))
            })
        })
        .transpose()?
        .unwrap_or_default();

    let placement_mode = placement
        .map(|s| {
            PlacementMode::from_str(s).ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Invalid placement mode: '{s}'. Expected 'random', 'grapheme_boundary', or 'script_aware'"
                ))
            })
        })
        .transpose()?
        .unwrap_or_default();

    let max_consec = max_consecutive.unwrap_or(4);

    let op = ZeroWidthOp::with_options(rate, palette, visibility_mode, placement_mode, max_consec);
    crate::apply_operation(text, op, seed).map_err(crate::operations::OperationError::into_pyerr)
}

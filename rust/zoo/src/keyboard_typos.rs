use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::Bound;
use std::collections::HashMap;
use std::sync::Arc;

use crate::cache::{hash_layout_map, hash_shift_map, ContentCache};
use crate::operations::{MotorWeighting, ShiftSlipConfig};

fn layout_cache() -> &'static ContentCache<HashMap<String, Vec<String>>> {
    static CACHE: std::sync::OnceLock<ContentCache<HashMap<String, Vec<String>>>> =
        std::sync::OnceLock::new();
    CACHE.get_or_init(ContentCache::new)
}

fn shift_map_cache() -> &'static ContentCache<HashMap<String, String>> {
    static CACHE: std::sync::OnceLock<ContentCache<HashMap<String, String>>> =
        std::sync::OnceLock::new();
    CACHE.get_or_init(ContentCache::new)
}

fn extract_layout_map(layout: &Bound<'_, PyDict>) -> PyResult<Arc<HashMap<String, Vec<String>>>> {
    // Materialize to compute content hash
    let mut materialised: HashMap<String, Vec<String>> = HashMap::new();
    for (entry_key, entry_value) in layout.iter() {
        materialised.insert(entry_key.extract()?, entry_value.extract()?);
    }

    // Use content-based caching - returns Arc for cheap access
    let hash = hash_layout_map(&materialised);
    Ok(layout_cache().get_or_insert_with(hash, || materialised))
}

pub(crate) fn extract_shift_map(
    shift_map: &Bound<'_, PyDict>,
) -> PyResult<Arc<HashMap<String, String>>> {
    // Materialize to compute content hash
    let mut materialised: HashMap<String, String> = HashMap::new();
    for (entry_key, entry_value) in shift_map.iter() {
        materialised.insert(entry_key.extract()?, entry_value.extract()?);
    }

    // Use content-based caching - returns Arc for cheap access
    let hash = hash_shift_map(&materialised);
    Ok(shift_map_cache().get_or_insert_with(hash, || materialised))
}

pub(crate) fn build_shift_slip_config(
    shift_slip_rate: f64,
    shift_slip_exit_rate: Option<f64>,
    shift_map: Option<Arc<HashMap<String, String>>>,
) -> PyResult<Option<ShiftSlipConfig>> {
    let enter_rate = shift_slip_rate.max(0.0);
    if enter_rate <= f64::EPSILON {
        return Ok(None);
    }

    let Some(map) = shift_map else {
        return Err(PyValueError::new_err(
            "shift_slip_rate requires a shift_map to be provided",
        ));
    };

    let exit_rate = shift_slip_exit_rate.unwrap_or(enter_rate * 0.5);
    // Clone the inner HashMap - this is efficient because the Arc caching ensures
    // we only ever store one copy of each unique shift map
    Ok(Some(ShiftSlipConfig::new(enter_rate, exit_rate, (*map).clone())))
}

#[allow(clippy::too_many_arguments)]
#[pyfunction(name = "keyboard_typo", signature = (text, max_change_rate, layout, seed=None, shift_slip_rate=None, shift_slip_exit_rate=None, shift_map=None, motor_weighting=None))]
pub(crate) fn keyboard_typo(
    text: &str,
    max_change_rate: f64,
    layout: &Bound<'_, PyDict>,
    seed: Option<u64>,
    shift_slip_rate: Option<f64>,
    shift_slip_exit_rate: Option<f64>,
    shift_map: Option<&Bound<'_, PyDict>>,
    motor_weighting: Option<&str>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let layout_arc = extract_layout_map(layout)?;
    let shift_map_arc = match shift_map {
        Some(map) => Some(extract_shift_map(map)?),
        None => None,
    };
    let shift_slip = build_shift_slip_config(
        shift_slip_rate.unwrap_or(0.0),
        shift_slip_exit_rate,
        shift_map_arc,
    )?;

    let motor_weighting = match motor_weighting {
        Some(s) => MotorWeighting::parse(s).unwrap_or_default(),
        None => MotorWeighting::default(),
    };

    let op = crate::operations::TypoOp {
        rate: max_change_rate,
        layout: (*layout_arc).clone(),
        shift_slip,
        motor_weighting,
    };

    crate::apply_operation(text, op, seed).map_err(crate::operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (text, enter_rate, exit_rate, shift_map, seed=None))]
pub(crate) fn slip_modifier(
    text: &str,
    enter_rate: f64,
    exit_rate: f64,
    shift_map: &Bound<'_, PyDict>,
    seed: Option<u64>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let shift_map_arc = extract_shift_map(shift_map)?;
    let config = ShiftSlipConfig::new(enter_rate, exit_rate, (*shift_map_arc).clone());
    let mut rng = crate::DeterministicRng::new(crate::resolve_seed(seed));
    config
        .apply(text, &mut rng)
        .map_err(crate::operations::OperationError::into_pyerr)
}

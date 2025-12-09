use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::Bound;
use std::collections::HashMap;
use std::sync::{Arc, OnceLock, RwLock};

use crate::glitch_ops::{MotorWeighting, ShiftSlipConfig};

type CachedLayouts = HashMap<usize, Arc<HashMap<String, Vec<String>>>>;
type CachedShiftMaps = HashMap<usize, Arc<HashMap<String, String>>>;

fn layout_cache() -> &'static RwLock<CachedLayouts> {
    static CACHE: OnceLock<RwLock<CachedLayouts>> = OnceLock::new();
    CACHE.get_or_init(|| RwLock::new(HashMap::new()))
}

fn shift_map_cache() -> &'static RwLock<CachedShiftMaps> {
    static CACHE: OnceLock<RwLock<CachedShiftMaps>> = OnceLock::new();
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

pub(crate) fn extract_shift_map(
    shift_map: &Bound<'_, PyDict>,
) -> PyResult<Arc<HashMap<String, String>>> {
    let key = shift_map.as_ptr() as usize;
    if let Some(cached) = shift_map_cache()
        .read()
        .expect("shift map cache poisoned")
        .get(&key)
    {
        return Ok(cached.clone());
    }

    let mut materialised: HashMap<String, String> = HashMap::new();
    for (entry_key, entry_value) in shift_map.iter() {
        materialised.insert(entry_key.extract()?, entry_value.extract()?);
    }
    let arc = Arc::new(materialised);

    let mut guard = shift_map_cache()
        .write()
        .expect("shift map cache poisoned during write");
    let entry = guard.entry(key).or_insert_with(|| arc.clone());
    Ok(entry.clone())
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
    Ok(Some(ShiftSlipConfig::new(
        enter_rate,
        exit_rate,
        (*map).clone(),
    )))
}

#[pyfunction(signature = (text, max_change_rate, layout, seed=None, shift_slip_rate=None, shift_slip_exit_rate=None, shift_map=None, motor_weighting=None))]
pub(crate) fn fatfinger(
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

    let layout_map = extract_layout_map(layout)?;
    let shift_map = match shift_map {
        Some(map) => Some(extract_shift_map(map)?),
        None => None,
    };
    let shift_slip = build_shift_slip_config(
        shift_slip_rate.unwrap_or(0.0),
        shift_slip_exit_rate,
        shift_map,
    )?;

    let motor_weighting = match motor_weighting {
        Some(s) => MotorWeighting::from_str(s).unwrap_or_default(),
        None => MotorWeighting::default(),
    };

    let op = crate::glitch_ops::TypoOp {
        rate: max_change_rate,
        layout: (*layout_map).clone(),
        shift_slip,
        motor_weighting,
    };

    crate::apply_operation(text, op, seed).map_err(crate::glitch_ops::GlitchOpError::into_pyerr)
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

    let shift_map = extract_shift_map(shift_map)?;
    let config = ShiftSlipConfig::new(enter_rate, exit_rate, (*shift_map).clone());
    let mut rng = crate::DeterministicRng::new(crate::resolve_seed(seed));
    config
        .apply(text, &mut rng)
        .map_err(crate::glitch_ops::GlitchOpError::into_pyerr)
}

use pyo3::prelude::*;
use pyo3::types::PyDict;
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

#[pyfunction(signature = (text, max_change_rate, layout, seed=None))]
pub(crate) fn fatfinger(
    text: &str,
    max_change_rate: f64,
    layout: &Bound<'_, PyDict>,
    seed: Option<u64>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    let layout_map = extract_layout_map(layout)?;
    let op = crate::glitch_ops::TypoOp {
        rate: max_change_rate,
        layout: (*layout_map).clone(),
    };

    crate::apply_operation(text, op, seed).map_err(crate::glitch_ops::GlitchOpError::into_pyerr)
}

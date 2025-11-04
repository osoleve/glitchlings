mod ekkokin;
mod glitch_ops;
mod hokey;
mod mim1c;
mod pedant;
mod pipeline;
mod resources;
mod rng;
mod text_buffer;
mod typogre;
mod zeedub;

use glitch_ops::{GlitchOp, GlitchRng};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};
use pyo3::Bound;
use pyo3::{exceptions::PyValueError, FromPyObject};
use std::collections::HashMap;
use std::sync::{Arc, OnceLock, RwLock};

use ekkokin::{EkkokinOp, HomophoneWeighting};
pub use glitch_ops::{
    DeleteRandomWordsOp, GlitchOpError, GlitchOperation, OcrArtifactsOp, QuotePairsOp,
    RedactWordsOp, ReduplicateWordsOp, RushmoreComboMode, RushmoreComboOp, SwapAdjacentWordsOp,
    TypoOp, ZeroWidthOp,
};
pub use hokey::HokeyOp;
use mim1c::{ClassSelection as MimicClassSelection, Mim1cOp};
use pedant::PedantOp;
pub use pipeline::{derive_seed, GlitchDescriptor, Pipeline, PipelineError};
pub use rng::{PyRng, PyRngError};
pub use text_buffer::{SegmentKind, TextBuffer, TextBufferError, TextSegment, TextSpan};
struct PythonRngAdapter<'py> {
    rng: Bound<'py, PyAny>,
}

impl<'py> PythonRngAdapter<'py> {
    fn new(rng: Bound<'py, PyAny>) -> Self {
        Self { rng }
    }
}

impl<'py> GlitchRng for PythonRngAdapter<'py> {
    fn random(&mut self) -> Result<f64, glitch_ops::GlitchOpError> {
        self.rng
            .call_method0("random")
            .map_err(glitch_ops::GlitchOpError::from_pyerr)?
            .extract()
            .map_err(glitch_ops::GlitchOpError::from_pyerr)
    }

    fn rand_index(&mut self, upper: usize) -> Result<usize, glitch_ops::GlitchOpError> {
        self.rng
            .call_method1("randrange", (upper,))
            .map_err(glitch_ops::GlitchOpError::from_pyerr)?
            .extract()
            .map_err(glitch_ops::GlitchOpError::from_pyerr)
    }

    fn sample_indices(
        &mut self,
        population: usize,
        k: usize,
    ) -> Result<Vec<usize>, glitch_ops::GlitchOpError> {
        let py = self.rng.py();
        let population_list = PyList::new(py, 0..population)
            .map_err(glitch_ops::GlitchOpError::from_pyerr)?
            .unbind();
        self.rng
            .call_method1("sample", (population_list, k))
            .map_err(glitch_ops::GlitchOpError::from_pyerr)?
            .extract()
            .map_err(glitch_ops::GlitchOpError::from_pyerr)
    }
}

#[derive(Debug)]
struct PyGlitchDescriptor {
    name: String,
    seed: u64,
    operation: PyGlitchOperation,
}

impl<'py> FromPyObject<'py> for PyGlitchDescriptor {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        let name = extract_required_field_with_field_suffix(&dict, "descriptor", "name")?;
        let seed = extract_required_field_with_field_suffix(&dict, "descriptor", "seed")?;
        let operation = extract_required_field_with_field_suffix(&dict, "descriptor", "operation")?;
        Ok(Self {
            name,
            seed,
            operation,
        })
    }
}

type LayoutVecCache = HashMap<usize, Arc<Vec<(String, Vec<String>)>>>;

fn layout_vec_cache() -> &'static RwLock<LayoutVecCache> {
    static CACHE: OnceLock<RwLock<LayoutVecCache>> = OnceLock::new();
    CACHE.get_or_init(|| RwLock::new(HashMap::new()))
}

enum MissingFieldSuffix {
    Absent,
    IncludeField,
}

fn extract_required_field_inner<'py, T>(
    dict: &Bound<'py, PyDict>,
    context: &str,
    field: &str,
    suffix: MissingFieldSuffix,
) -> PyResult<T>
where
    T: FromPyObject<'py>,
{
    let message = match suffix {
        MissingFieldSuffix::Absent => format!("{context} missing '{field}'"),
        MissingFieldSuffix::IncludeField => format!("{context} missing '{field}' field"),
    };

    dict.get_item(field)?
        .ok_or_else(|| PyValueError::new_err(message))?
        .extract()
}

fn extract_required_field<'py, T>(
    dict: &Bound<'py, PyDict>,
    context: &str,
    field: &str,
) -> PyResult<T>
where
    T: FromPyObject<'py>,
{
    extract_required_field_inner(dict, context, field, MissingFieldSuffix::Absent)
}

fn extract_required_field_with_field_suffix<'py, T>(
    dict: &Bound<'py, PyDict>,
    context: &str,
    field: &str,
) -> PyResult<T>
where
    T: FromPyObject<'py>,
{
    extract_required_field_inner(dict, context, field, MissingFieldSuffix::IncludeField)
}

fn extract_optional_field<'py, T>(dict: &Bound<'py, PyDict>, field: &str) -> PyResult<Option<T>>
where
    T: FromPyObject<'py>,
{
    dict.get_item(field)?
        .map(|value| value.extract())
        .transpose()
}

fn cached_layout_vec(layout_dict: &Bound<'_, PyDict>) -> PyResult<Arc<Vec<(String, Vec<String>)>>> {
    let key = layout_dict.as_ptr() as usize;
    if let Some(cached) = layout_vec_cache()
        .read()
        .expect("layout vec cache poisoned")
        .get(&key)
    {
        return Ok(cached.clone());
    }

    let mut materialised: Vec<(String, Vec<String>)> = Vec::with_capacity(layout_dict.len());
    for (key_obj, value_obj) in layout_dict.iter() {
        materialised.push((key_obj.extract()?, value_obj.extract()?));
    }
    let arc = Arc::new(materialised);
    let mut guard = layout_vec_cache()
        .write()
        .expect("layout vec cache poisoned during write");
    let entry = guard.entry(key).or_insert_with(|| arc.clone());
    Ok(entry.clone())
}

#[derive(Debug)]
struct PyGagglePlanInput {
    name: String,
    scope: i32,
    order: i32,
}

impl<'py> FromPyObject<'py> for PyGagglePlanInput {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        if let Ok(dict) = obj.downcast::<PyDict>() {
            let name: String =
                extract_required_field_with_field_suffix(&dict, "plan input", "name")?;
            let scope: i32 =
                extract_required_field_with_field_suffix(&dict, "plan input", "scope")?;
            let order: i32 =
                extract_required_field_with_field_suffix(&dict, "plan input", "order")?;
            return Ok(Self { name, scope, order });
        }

        let name = obj
            .getattr("name")
            .map_err(|_| PyValueError::new_err("plan input missing attribute 'name'"))?
            .extract()?;
        let scope = obj
            .getattr("scope")
            .map_err(|_| PyValueError::new_err("plan input missing attribute 'scope'"))?
            .extract()?;
        let order = obj
            .getattr("order")
            .map_err(|_| PyValueError::new_err("plan input missing attribute 'order'"))?
            .extract()?;
        Ok(Self { name, scope, order })
    }
}

#[derive(Debug)]
enum PyGlitchOperation {
    Reduplicate {
        rate: f64,
        unweighted: bool,
    },
    Delete {
        rate: f64,
        unweighted: bool,
    },
    SwapAdjacent {
        rate: f64,
    },
    RushmoreCombo {
        modes: Vec<String>,
        delete: Option<DeleteRandomWordsOp>,
        duplicate: Option<ReduplicateWordsOp>,
        swap: Option<SwapAdjacentWordsOp>,
    },
    Redact {
        replacement_char: String,
        rate: f64,
        merge_adjacent: bool,
        unweighted: bool,
    },
    Ocr {
        rate: f64,
    },
    Typo {
        rate: f64,
        layout: Arc<Vec<(String, Vec<String>)>>,
    },
    Mimic {
        rate: f64,
        classes: MimicClassSelection,
        banned: Vec<String>,
    },
    ZeroWidth {
        rate: f64,
        characters: Vec<String>,
    },
    QuotePairs,
    Hokey {
        rate: f64,
        extension_min: i32,
        extension_max: i32,
        word_length_threshold: usize,
        base_p: f64,
    },
    Ekkokin {
        rate: f64,
        weighting: String,
    },
    Pedant {
        stone: String,
    },
}

impl<'py> FromPyObject<'py> for PyGlitchOperation {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        let op_type: String = extract_required_field_with_field_suffix(&dict, "operation", "type")?;
        match op_type.as_str() {
            "reduplicate" => {
                let rate = extract_required_field(&dict, "reduplicate operation", "rate")?;
                let unweighted = extract_optional_field(&dict, "unweighted")?.unwrap_or(false);
                Ok(PyGlitchOperation::Reduplicate { rate, unweighted })
            }
            "delete" => {
                let rate = extract_required_field(&dict, "delete operation", "rate")?;
                let unweighted = extract_optional_field(&dict, "unweighted")?.unwrap_or(false);
                Ok(PyGlitchOperation::Delete { rate, unweighted })
            }
            "swap_adjacent" => {
                let rate = extract_required_field(&dict, "swap_adjacent operation", "rate")?;
                Ok(PyGlitchOperation::SwapAdjacent { rate })
            }
            "rushmore_combo" => {
                let modes: Vec<String> =
                    extract_required_field(&dict, "rushmore_combo operation", "modes")?;

                let delete = dict
                    .get_item("delete")?
                    .map(|value| -> PyResult<DeleteRandomWordsOp> {
                        let mapping = value.downcast::<PyDict>()?;
                        let rate =
                            extract_required_field(&mapping, "rushmore_combo delete", "rate")?;
                        let unweighted =
                            extract_optional_field(&mapping, "unweighted")?.unwrap_or(false);
                        Ok(DeleteRandomWordsOp { rate, unweighted })
                    })
                    .transpose()?;

                let duplicate = dict
                    .get_item("duplicate")?
                    .map(|value| -> PyResult<ReduplicateWordsOp> {
                        let mapping = value.downcast::<PyDict>()?;
                        let rate =
                            extract_required_field(&mapping, "rushmore_combo duplicate", "rate")?;
                        let unweighted =
                            extract_optional_field(&mapping, "unweighted")?.unwrap_or(false);
                        Ok(ReduplicateWordsOp { rate, unweighted })
                    })
                    .transpose()?;

                let swap = dict
                    .get_item("swap")?
                    .map(|value| -> PyResult<SwapAdjacentWordsOp> {
                        let mapping = value.downcast::<PyDict>()?;
                        let rate = extract_required_field(&mapping, "rushmore_combo swap", "rate")?;
                        Ok(SwapAdjacentWordsOp { rate })
                    })
                    .transpose()?;

                Ok(PyGlitchOperation::RushmoreCombo {
                    modes,
                    delete,
                    duplicate,
                    swap,
                })
            }
            "redact" => {
                let replacement_char =
                    extract_required_field(&dict, "redact operation", "replacement_char")?;
                let rate = extract_required_field(&dict, "redact operation", "rate")?;
                let merge_adjacent =
                    extract_required_field(&dict, "redact operation", "merge_adjacent")?;
                let unweighted = extract_optional_field(&dict, "unweighted")?.unwrap_or(false);
                Ok(PyGlitchOperation::Redact {
                    replacement_char,
                    rate,
                    merge_adjacent,
                    unweighted,
                })
            }
            "ocr" => {
                let rate = extract_required_field(&dict, "ocr operation", "rate")?;
                Ok(PyGlitchOperation::Ocr { rate })
            }
            "typo" => {
                let rate =
                    extract_required_field_with_field_suffix(&dict, "typo operation", "rate")?;
                let layout_obj: Bound<'py, PyAny> =
                    extract_required_field_with_field_suffix(&dict, "typo operation", "layout")?;
                let layout_dict = layout_obj.downcast::<PyDict>()?;
                let layout = cached_layout_vec(layout_dict)?;
                Ok(PyGlitchOperation::Typo { rate, layout })
            }
            "mimic" => {
                let rate =
                    extract_required_field_with_field_suffix(&dict, "mimic operation", "rate")?;
                let classes = mim1c::parse_class_selection(dict.get_item("classes")?)?;
                let banned = mim1c::parse_banned_characters(dict.get_item("banned_characters")?)?;
                Ok(PyGlitchOperation::Mimic {
                    rate,
                    classes,
                    banned,
                })
            }
            "zwj" => {
                let rate =
                    extract_required_field_with_field_suffix(&dict, "zwj operation", "rate")?;
                let characters = extract_optional_field(&dict, "characters")?.unwrap_or_default();
                Ok(PyGlitchOperation::ZeroWidth { rate, characters })
            }
            "ekkokin" => {
                let rate = extract_required_field(&dict, "ekkokin operation", "rate")?;
                let weighting = extract_optional_field(&dict, "weighting")?
                    .unwrap_or_else(|| HomophoneWeighting::Flat.as_str().to_string());
                Ok(PyGlitchOperation::Ekkokin { rate, weighting })
            }
            "pedant" => {
                let stone = extract_required_field(&dict, "pedant operation", "stone")?;
                Ok(PyGlitchOperation::Pedant { stone })
            }
            "apostrofae" | "quote_pairs" => Ok(PyGlitchOperation::QuotePairs),
            "hokey" => {
                let rate = extract_required_field(&dict, "hokey operation", "rate")?;
                let extension_min =
                    extract_required_field(&dict, "hokey operation", "extension_min")?;
                let extension_max =
                    extract_required_field(&dict, "hokey operation", "extension_max")?;
                let word_length_threshold =
                    extract_required_field(&dict, "hokey operation", "word_length_threshold")?;
                let base_p = extract_optional_field(&dict, "base_p")?.unwrap_or(0.45);
                Ok(PyGlitchOperation::Hokey {
                    rate,
                    extension_min,
                    extension_max,
                    word_length_threshold,
                    base_p,
                })
            }
            other => Err(PyValueError::new_err(format!(
                "unsupported operation type: {other}"
            ))),
        }
    }
}

impl PyGlitchOperation {
    fn into_glitch_operation(self, seed: u64) -> PyResult<GlitchOperation> {
        let operation = match self {
            PyGlitchOperation::Reduplicate { rate, unweighted } => {
                GlitchOperation::Reduplicate(glitch_ops::ReduplicateWordsOp { rate, unweighted })
            }
            PyGlitchOperation::Delete { rate, unweighted } => {
                GlitchOperation::Delete(glitch_ops::DeleteRandomWordsOp { rate, unweighted })
            }
            PyGlitchOperation::SwapAdjacent { rate } => {
                GlitchOperation::SwapAdjacent(glitch_ops::SwapAdjacentWordsOp { rate })
            }
            PyGlitchOperation::RushmoreCombo {
                modes,
                delete,
                duplicate,
                swap,
            } => {
                let rushmore_modes = modes
                    .into_iter()
                    .map(|mode| match mode.as_str() {
                        "delete" => Ok(glitch_ops::RushmoreComboMode::Delete),
                        "duplicate" => Ok(glitch_ops::RushmoreComboMode::Duplicate),
                        "swap" => Ok(glitch_ops::RushmoreComboMode::Swap),
                        other => Err(PyValueError::new_err(format!(
                            "unsupported Rushmore mode: {other}"
                        ))),
                    })
                    .collect::<Result<Vec<_>, PyErr>>()?;
                GlitchOperation::RushmoreCombo(glitch_ops::RushmoreComboOp::new(
                    rushmore_modes,
                    delete,
                    duplicate,
                    swap,
                ))
            }
            PyGlitchOperation::Redact {
                replacement_char,
                rate,
                merge_adjacent,
                unweighted,
            } => GlitchOperation::Redact(glitch_ops::RedactWordsOp {
                replacement_char,
                rate,
                merge_adjacent,
                unweighted,
            }),
            PyGlitchOperation::Ocr { rate } => {
                GlitchOperation::Ocr(glitch_ops::OcrArtifactsOp { rate })
            }
            PyGlitchOperation::Typo { rate, layout } => {
                let layout_map: HashMap<String, Vec<String>> =
                    layout.as_ref().iter().cloned().collect();
                GlitchOperation::Typo(glitch_ops::TypoOp {
                    rate,
                    layout: layout_map,
                })
            }
            PyGlitchOperation::Mimic {
                rate,
                classes,
                banned,
            } => GlitchOperation::Mimic(Mim1cOp::new(rate, classes, banned)),
            PyGlitchOperation::ZeroWidth { rate, characters } => {
                GlitchOperation::ZeroWidth(glitch_ops::ZeroWidthOp { rate, characters })
            }
            PyGlitchOperation::Ekkokin { rate, weighting } => {
                let weighting = HomophoneWeighting::try_from_str(&weighting).ok_or_else(|| {
                    PyValueError::new_err(format!("unsupported weighting: {weighting}"))
                })?;
                GlitchOperation::Ekkokin(EkkokinOp { rate, weighting })
            }
            PyGlitchOperation::Pedant { stone } => {
                let op = PedantOp::new(seed as i128, &stone)?;
                GlitchOperation::Pedant(op)
            }
            PyGlitchOperation::QuotePairs => {
                GlitchOperation::QuotePairs(glitch_ops::QuotePairsOp::default())
            }
            PyGlitchOperation::Hokey {
                rate,
                extension_min,
                extension_max,
                word_length_threshold,
                base_p,
            } => GlitchOperation::Hokey(HokeyOp {
                rate,
                extension_min,
                extension_max,
                word_length_threshold,
                base_p,
            }),
        };

        Ok(operation)
    }
}

pub(crate) fn apply_operation<'py, O>(
    text: &str,
    op: O,
    rng: &Bound<'py, PyAny>,
) -> Result<String, glitch_ops::GlitchOpError>
where
    O: GlitchOp,
{
    let mut buffer = TextBuffer::from_str(text);
    let mut adapter = PythonRngAdapter::new(rng.clone());
    op.apply(&mut buffer, &mut adapter)?;
    Ok(buffer.to_string())
}

#[pyfunction]
fn reduplicate_words(
    text: &str,
    rate: f64,
    unweighted: bool,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let op = ReduplicateWordsOp { rate, unweighted };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn delete_random_words(
    text: &str,
    rate: f64,
    unweighted: bool,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let op = DeleteRandomWordsOp { rate, unweighted };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn swap_adjacent_words(text: &str, rate: f64, rng: &Bound<'_, PyAny>) -> PyResult<String> {
    let op = SwapAdjacentWordsOp { rate };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn ekkokin_homophones(
    text: &str,
    rate: f64,
    weighting: &str,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let weighting = HomophoneWeighting::try_from_str(weighting)
        .ok_or_else(|| PyValueError::new_err(format!("unsupported weighting: {weighting}")))?;
    let op = EkkokinOp { rate, weighting };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction(name = "pedant", signature = (text, stone, seed, rng))]
fn pedant_operation(
    text: &str,
    stone: &str,
    seed: i128,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let op = PedantOp::new(seed, stone)?;
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn apostrofae(text: &str, rng: &Bound<'_, PyAny>) -> PyResult<String> {
    let op = QuotePairsOp::default();
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn ocr_artifacts(text: &str, rate: f64, rng: &Bound<'_, PyAny>) -> PyResult<String> {
    let op = OcrArtifactsOp { rate };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn redact_words(
    text: &str,
    replacement_char: &str,
    rate: f64,
    merge_adjacent: bool,
    unweighted: bool,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let op = RedactWordsOp {
        replacement_char: replacement_char.to_string(),
        rate,
        merge_adjacent,
        unweighted,
    };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn plan_glitchlings(
    glitchlings: Vec<PyGagglePlanInput>,
    master_seed: i128,
) -> PyResult<Vec<(usize, u64)>> {
    let plan = pipeline::plan_gaggle(
        glitchlings
            .into_iter()
            .enumerate()
            .map(|(index, input)| pipeline::GagglePlanInput {
                index,
                name: input.name,
                scope: input.scope,
                order: input.order,
            })
            .collect(),
        master_seed,
    );
    Ok(plan
        .into_iter()
        .map(|entry| (entry.index, entry.seed))
        .collect())
}

#[pyfunction]
fn compose_glitchlings(
    text: &str,
    descriptors: Vec<PyGlitchDescriptor>,
    master_seed: i128,
) -> PyResult<String> {
    let operations = descriptors
        .into_iter()
        .map(|descriptor| {
            let operation = descriptor
                .operation
                .into_glitch_operation(descriptor.seed)?;
            Ok(GlitchDescriptor {
                name: descriptor.name,
                seed: descriptor.seed,
                operation,
            })
        })
        .collect::<Result<Vec<_>, PyErr>>()?;

    let pipeline = Pipeline::new(master_seed, operations);
    pipeline.run(text).map_err(|error| error.into_pyerr())
}

#[pymodule]
fn _zoo_rust(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(reduplicate_words, m)?)?;
    m.add_function(wrap_pyfunction!(delete_random_words, m)?)?;
    m.add_function(wrap_pyfunction!(swap_adjacent_words, m)?)?;
    m.add_function(wrap_pyfunction!(mim1c::swap_homoglyphs, m)?)?;
    m.add_function(wrap_pyfunction!(ekkokin_homophones, m)?)?;
    m.add_function(wrap_pyfunction!(pedant_operation, m)?)?;
    m.add_function(wrap_pyfunction!(apostrofae, m)?)?;
    m.add_function(wrap_pyfunction!(ocr_artifacts, m)?)?;
    m.add_function(wrap_pyfunction!(redact_words, m)?)?;
    m.add_function(wrap_pyfunction!(plan_glitchlings, m)?)?;
    m.add_function(wrap_pyfunction!(compose_glitchlings, m)?)?;
    m.add_function(wrap_pyfunction!(typogre::fatfinger, m)?)?;
    m.add_function(wrap_pyfunction!(zeedub::inject_zero_widths, m)?)?;
    m.add_function(wrap_pyfunction!(hokey::hokey, m)?)?;
    Ok(())
}

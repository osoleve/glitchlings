mod homophones;
mod operations;
mod word_stretching;
mod lexeme_substitution;
mod metrics;
mod homoglyphs;
mod grammar_rules;
mod pipeline;
mod resources;
mod rng;
mod text_buffer;
mod keyboard_typos;
mod zero_width;

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyModule};
use pyo3::Bound;
use pyo3::{exceptions::PyValueError, FromPyObject};
use rand::Rng;
use std::collections::HashMap;
use std::sync::{Arc, OnceLock, RwLock};

use homophones::{HomophoneOp, HomophoneWeighting};
pub use operations::{
    DeleteRandomWordsOp, TextOperation, OperationError, Operation, OperationRng, MotorWeighting,
    OcrArtifactsOp, QuotePairsOp, RedactWordsOp, ReduplicateWordsOp, RushmoreComboMode,
    RushmoreComboOp, ShiftSlipConfig, SwapAdjacentWordsOp, TypoOp, ZeroWidthOp,
};
pub use word_stretching::WordStretchOp;
use lexeme_substitution::{JargoyleMode, LexemeSubstitutionOp};
use homoglyphs::{ClassSelection as MimicClassSelection, HomoglyphOp};
use grammar_rules::GrammarRuleOp;
pub use pipeline::{derive_seed, OperationDescriptor, Pipeline, PipelineError};
pub use rng::{DeterministicRng, RngError};
pub use text_buffer::{SegmentKind, TextBuffer, TextBufferError, TextSegment, TextSpan};

fn resolve_seed(seed: Option<u64>) -> u64 {
    seed.unwrap_or_else(|| rand::thread_rng().gen())
}

#[derive(Debug)]
struct PyGlitchDescriptor {
    name: String,
    seed: u64,
    operation: PyOperation,
}

impl<'py> FromPyObject<'py> for PyGlitchDescriptor {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        let name = extract_required_field_with_field_suffix(dict, "descriptor", "name")?;
        let seed = extract_required_field_with_field_suffix(dict, "descriptor", "seed")?;
        let operation = extract_required_field_with_field_suffix(dict, "descriptor", "operation")?;
        Ok(Self {
            name,
            seed,
            operation,
        })
    }
}

type Layout = Vec<(String, Vec<String>)>;
type LayoutVecCache = HashMap<usize, Arc<Layout>>;

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

fn cached_layout_vec(layout_dict: &Bound<'_, PyDict>) -> PyResult<Arc<Layout>> {
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

fn build_operation_descriptors(
    descriptors: Vec<PyGlitchDescriptor>,
) -> PyResult<Vec<OperationDescriptor>> {
    descriptors
        .into_iter()
        .map(|descriptor| {
            let operation = descriptor
                .operation
                .into_glitch_operation(descriptor.seed)?;
            Ok(OperationDescriptor {
                name: descriptor.name,
                seed: descriptor.seed,
                operation,
            })
        })
        .collect()
}

fn build_pipeline_from_py(
    descriptors: Vec<PyGlitchDescriptor>,
    master_seed: i128,
    include_only_patterns: Option<Vec<String>>,
    exclude_patterns: Option<Vec<String>>,
) -> PyResult<Pipeline> {
    let operations = build_operation_descriptors(descriptors)?;
    let include_patterns = include_only_patterns.unwrap_or_default();
    let exclude_patterns = exclude_patterns.unwrap_or_default();
    Pipeline::compile(master_seed, operations, include_patterns, exclude_patterns)
        .map_err(|err| err.into_pyerr())
}

#[pymethods]
impl Pipeline {
    #[new]
    #[pyo3(signature = (descriptors, master_seed, include_only_patterns=None, exclude_patterns=None))]
    fn py_new(
        descriptors: Vec<PyGlitchDescriptor>,
        master_seed: i128,
        include_only_patterns: Option<Vec<String>>,
        exclude_patterns: Option<Vec<String>>,
    ) -> PyResult<Self> {
        build_pipeline_from_py(
            descriptors,
            master_seed,
            include_only_patterns,
            exclude_patterns,
        )
    }

    #[pyo3(name = "run")]
    fn run_py(&self, text: &str) -> PyResult<String> {
        Pipeline::run(self, text).map_err(|error| error.into_pyerr())
    }
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
                extract_required_field_with_field_suffix(dict, "plan input", "name")?;
            let scope: i32 = extract_required_field_with_field_suffix(dict, "plan input", "scope")?;
            let order: i32 = extract_required_field_with_field_suffix(dict, "plan input", "order")?;
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
enum PyOperation {
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
        layout: Arc<Layout>,
        shift_slip: Option<ShiftSlipConfig>,
        motor_weighting: MotorWeighting,
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
    Jargoyle {
        lexemes: String,
        mode: JargoyleMode,
        rate: f64,
    },
    QuotePairs,
    Hokey {
        rate: f64,
        extension_min: i32,
        extension_max: i32,
        word_length_threshold: usize,
        base_p: f64,
    },
    Wherewolf {
        rate: f64,
        weighting: String,
    },
    Pedant {
        stone: String,
    },
}

impl<'py> FromPyObject<'py> for PyOperation {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        let op_type: String = extract_required_field_with_field_suffix(dict, "operation", "type")?;
        match op_type.as_str() {
            "reduplicate" => {
                let rate = extract_required_field(dict, "reduplicate operation", "rate")?;
                let unweighted = extract_optional_field(dict, "unweighted")?.unwrap_or(false);
                Ok(PyOperation::Reduplicate { rate, unweighted })
            }
            "delete" => {
                let rate = extract_required_field(dict, "delete operation", "rate")?;
                let unweighted = extract_optional_field(dict, "unweighted")?.unwrap_or(false);
                Ok(PyOperation::Delete { rate, unweighted })
            }
            "swap_adjacent" => {
                let rate = extract_required_field(dict, "swap_adjacent operation", "rate")?;
                Ok(PyOperation::SwapAdjacent { rate })
            }
            "rushmore_combo" => {
                let modes: Vec<String> =
                    extract_required_field(dict, "rushmore_combo operation", "modes")?;

                let delete = dict
                    .get_item("delete")?
                    .map(|value| -> PyResult<DeleteRandomWordsOp> {
                        let mapping = value.downcast::<PyDict>()?;
                        let rate =
                            extract_required_field(mapping, "rushmore_combo delete", "rate")?;
                        let unweighted =
                            extract_optional_field(mapping, "unweighted")?.unwrap_or(false);
                        Ok(DeleteRandomWordsOp { rate, unweighted })
                    })
                    .transpose()?;

                let duplicate = dict
                    .get_item("duplicate")?
                    .map(|value| -> PyResult<ReduplicateWordsOp> {
                        let mapping = value.downcast::<PyDict>()?;
                        let rate =
                            extract_required_field(mapping, "rushmore_combo duplicate", "rate")?;
                        let unweighted =
                            extract_optional_field(mapping, "unweighted")?.unwrap_or(false);
                        Ok(ReduplicateWordsOp { rate, unweighted })
                    })
                    .transpose()?;

                let swap = dict
                    .get_item("swap")?
                    .map(|value| -> PyResult<SwapAdjacentWordsOp> {
                        let mapping = value.downcast::<PyDict>()?;
                        let rate = extract_required_field(mapping, "rushmore_combo swap", "rate")?;
                        Ok(SwapAdjacentWordsOp { rate })
                    })
                    .transpose()?;

                Ok(PyOperation::RushmoreCombo {
                    modes,
                    delete,
                    duplicate,
                    swap,
                })
            }
            "redact" => {
                let replacement_char =
                    extract_required_field(dict, "redact operation", "replacement_char")?;
                let rate = extract_required_field(dict, "redact operation", "rate")?;
                let merge_adjacent =
                    extract_required_field(dict, "redact operation", "merge_adjacent")?;
                let unweighted = extract_optional_field(dict, "unweighted")?.unwrap_or(false);
                Ok(PyOperation::Redact {
                    replacement_char,
                    rate,
                    merge_adjacent,
                    unweighted,
                })
            }
            "ocr" => {
                let rate = extract_required_field(dict, "ocr operation", "rate")?;
                Ok(PyOperation::Ocr { rate })
            }
            "typo" => {
                let rate =
                    extract_required_field_with_field_suffix(dict, "typo operation", "rate")?;
                let layout_obj: Bound<'py, PyAny> =
                    extract_required_field_with_field_suffix(dict, "typo operation", "layout")?;
                let layout_dict = layout_obj.downcast::<PyDict>()?;
                let layout = cached_layout_vec(layout_dict)?;
                let shift_slip_rate =
                    extract_optional_field(dict, "shift_slip_rate")?.unwrap_or(0.0);
                let shift_slip_exit_rate = extract_optional_field(dict, "shift_slip_exit_rate")?;
                let shift_map = dict
                    .get_item("shift_map")?
                    .map(|value| -> PyResult<Arc<HashMap<String, String>>> {
                        let mapping = value.downcast::<PyDict>()?;
                        keyboard_typos::extract_shift_map(mapping)
                    })
                    .transpose()?;
                let shift_slip = keyboard_typos::build_shift_slip_config(
                    shift_slip_rate,
                    shift_slip_exit_rate,
                    shift_map,
                )?;
                let motor_weighting_str: Option<String> =
                    extract_optional_field(dict, "motor_weighting")?;
                let motor_weighting = motor_weighting_str
                    .as_deref()
                    .and_then(MotorWeighting::from_str)
                    .unwrap_or_default();

                Ok(PyOperation::Typo {
                    rate,
                    layout,
                    shift_slip,
                    motor_weighting,
                })
            }
            "mimic" => {
                let rate =
                    extract_required_field_with_field_suffix(dict, "mimic operation", "rate")?;
                let classes = homoglyphs::parse_class_selection(dict.get_item("classes")?)?;
                let banned = homoglyphs::parse_banned_characters(dict.get_item("banned_characters")?)?;
                Ok(PyOperation::Mimic {
                    rate,
                    classes,
                    banned,
                })
            }
            "zwj" => {
                let rate = extract_required_field_with_field_suffix(dict, "zwj operation", "rate")?;
                let characters = extract_optional_field(dict, "characters")?.unwrap_or_default();
                Ok(PyOperation::ZeroWidth { rate, characters })
            }
            "jargoyle" => {
                let lexemes = extract_optional_field(dict, "lexemes")?
                    .unwrap_or_else(|| "synonyms".to_string());
                let mode =
                    extract_optional_field(dict, "mode")?.unwrap_or_else(|| "drift".to_string());
                let parsed_mode = JargoyleMode::parse(&mode).map_err(PyValueError::new_err)?;
                let rate = extract_required_field(dict, "jargoyle operation", "rate")?;
                Ok(PyOperation::Jargoyle {
                    lexemes,
                    mode: parsed_mode,
                    rate,
                })
            }
            "wherewolf" => {
                let rate = extract_required_field(dict, "wherewolf operation", "rate")?;
                let weighting = extract_optional_field(dict, "weighting")?
                    .unwrap_or_else(|| HomophoneWeighting::Flat.as_str().to_string());
                Ok(PyOperation::Wherewolf { rate, weighting })
            }
            "pedant" => {
                let stone = extract_required_field(dict, "pedant operation", "stone")?;
                Ok(PyOperation::Pedant { stone })
            }
            "apostrofae" | "quote_pairs" => Ok(PyOperation::QuotePairs),
            "hokey" => {
                let rate = extract_required_field(dict, "hokey operation", "rate")?;
                let extension_min =
                    extract_required_field(dict, "hokey operation", "extension_min")?;
                let extension_max =
                    extract_required_field(dict, "hokey operation", "extension_max")?;
                let word_length_threshold =
                    extract_required_field(dict, "hokey operation", "word_length_threshold")?;
                let base_p = extract_optional_field(dict, "base_p")?.unwrap_or(0.45);
                Ok(PyOperation::Hokey {
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

impl PyOperation {
    fn into_glitch_operation(self, seed: u64) -> PyResult<Operation> {
        let operation = match self {
            PyOperation::Reduplicate { rate, unweighted } => {
                Operation::Reduplicate(operations::ReduplicateWordsOp { rate, unweighted })
            }
            PyOperation::Delete { rate, unweighted } => {
                Operation::Delete(operations::DeleteRandomWordsOp { rate, unweighted })
            }
            PyOperation::SwapAdjacent { rate } => {
                Operation::SwapAdjacent(operations::SwapAdjacentWordsOp { rate })
            }
            PyOperation::RushmoreCombo {
                modes,
                delete,
                duplicate,
                swap,
            } => {
                let rushmore_modes = modes
                    .into_iter()
                    .map(|mode| match mode.as_str() {
                        "delete" => Ok(operations::RushmoreComboMode::Delete),
                        "duplicate" => Ok(operations::RushmoreComboMode::Duplicate),
                        "swap" => Ok(operations::RushmoreComboMode::Swap),
                        other => Err(PyValueError::new_err(format!(
                            "unsupported Rushmore mode: {other}"
                        ))),
                    })
                    .collect::<Result<Vec<_>, PyErr>>()?;
                Operation::RushmoreCombo(operations::RushmoreComboOp::new(
                    rushmore_modes,
                    delete,
                    duplicate,
                    swap,
                ))
            }
            PyOperation::Redact {
                replacement_char,
                rate,
                merge_adjacent,
                unweighted,
            } => Operation::Redact(operations::RedactWordsOp {
                replacement_char,
                rate,
                merge_adjacent,
                unweighted,
            }),
            PyOperation::Ocr { rate } => {
                Operation::Ocr(operations::OcrArtifactsOp { rate })
            }
            PyOperation::Typo {
                rate,
                layout,
                shift_slip,
                motor_weighting,
            } => {
                let layout_map: HashMap<String, Vec<String>> =
                    layout.as_ref().iter().cloned().collect();
                Operation::Typo(operations::TypoOp {
                    rate,
                    layout: layout_map,
                    shift_slip,
                    motor_weighting,
                })
            }
            PyOperation::Mimic {
                rate,
                classes,
                banned,
            } => Operation::Mimic(HomoglyphOp::new(rate, classes, banned)),
            PyOperation::ZeroWidth { rate, characters } => {
                Operation::ZeroWidth(operations::ZeroWidthOp { rate, characters })
            }
            PyOperation::Jargoyle {
                lexemes,
                mode,
                rate,
            } => Operation::Jargoyle(LexemeSubstitutionOp::new(&lexemes, mode, rate)),
            PyOperation::Wherewolf { rate, weighting } => {
                let weighting = HomophoneWeighting::try_from_str(&weighting).ok_or_else(|| {
                    PyValueError::new_err(format!("unsupported weighting: {weighting}"))
                })?;
                Operation::Wherewolf(HomophoneOp { rate, weighting })
            }
            PyOperation::Pedant { stone } => {
                let op = GrammarRuleOp::new(seed as i128, &stone)?;
                Operation::Pedant(op)
            }
            PyOperation::QuotePairs => Operation::QuotePairs(operations::QuotePairsOp),
            PyOperation::Hokey {
                rate,
                extension_min,
                extension_max,
                word_length_threshold,
                base_p,
            } => Operation::Hokey(WordStretchOp {
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

pub(crate) fn apply_operation<O>(
    text: &str,
    op: O,
    seed: Option<u64>,
) -> Result<String, operations::OperationError>
where
    O: TextOperation,
{
    let mut buffer = TextBuffer::from_owned(text.to_string(), &[], &[]);
    let mut rng = DeterministicRng::new(resolve_seed(seed));
    op.apply(&mut buffer, &mut rng)?;
    Ok(buffer.to_string())
}

#[pyfunction(signature = (text, rate, unweighted, seed=None))]
fn reduplicate_words(
    text: &str,
    rate: f64,
    unweighted: bool,
    seed: Option<u64>,
) -> PyResult<String> {
    let op = ReduplicateWordsOp { rate, unweighted };
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (text, rate, unweighted, seed=None))]
fn delete_random_words(
    text: &str,
    rate: f64,
    unweighted: bool,
    seed: Option<u64>,
) -> PyResult<String> {
    let op = DeleteRandomWordsOp { rate, unweighted };
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (text, rate, seed=None))]
fn swap_adjacent_words(text: &str, rate: f64, seed: Option<u64>) -> PyResult<String> {
    let op = SwapAdjacentWordsOp { rate };
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (text, rate, weighting, seed=None))]
fn wherewolf_homophones(
    text: &str,
    rate: f64,
    weighting: &str,
    seed: Option<u64>,
) -> PyResult<String> {
    let weighting = HomophoneWeighting::try_from_str(weighting)
        .ok_or_else(|| PyValueError::new_err(format!("unsupported weighting: {weighting}")))?;
    let op = HomophoneOp { rate, weighting };
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(name = "pedant", signature = (text, stone, seed))]
fn pedant_operation(text: &str, stone: &str, seed: i128) -> PyResult<String> {
    let op = GrammarRuleOp::new(seed, stone)?;
    apply_operation(text, op, None).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (text, seed=None))]
fn apostrofae(text: &str, seed: Option<u64>) -> PyResult<String> {
    let op = QuotePairsOp;
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (text, rate, seed=None))]
fn ocr_artifacts(text: &str, rate: f64, seed: Option<u64>) -> PyResult<String> {
    let op = OcrArtifactsOp { rate };
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (text, replacement_char, rate, merge_adjacent, unweighted, seed=None))]
fn redact_words(
    text: &str,
    replacement_char: &str,
    rate: f64,
    merge_adjacent: bool,
    unweighted: bool,
    seed: Option<u64>,
) -> PyResult<String> {
    let op = RedactWordsOp {
        replacement_char: replacement_char.to_string(),
        rate,
        merge_adjacent,
        unweighted,
    };
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
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

#[pyfunction(signature = (text, descriptors, master_seed, include_only_patterns=None, exclude_patterns=None))]
fn compose_glitchlings(
    text: &str,
    descriptors: Vec<PyGlitchDescriptor>,
    master_seed: i128,
    include_only_patterns: Option<Vec<String>>,
    exclude_patterns: Option<Vec<String>>,
) -> PyResult<String> {
    let pipeline = build_pipeline_from_py(
        descriptors,
        master_seed,
        include_only_patterns,
        exclude_patterns,
    )?;
    pipeline.run(text).map_err(|error| error.into_pyerr())
}

#[pymodule]
fn _zoo_rust(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(reduplicate_words, m)?)?;
    m.add_function(wrap_pyfunction!(delete_random_words, m)?)?;
    m.add_function(wrap_pyfunction!(swap_adjacent_words, m)?)?;
    m.add_function(wrap_pyfunction!(homoglyphs::swap_homoglyphs, m)?)?;
    m.add_function(wrap_pyfunction!(wherewolf_homophones, m)?)?;
    m.add_function(wrap_pyfunction!(pedant_operation, m)?)?;
    m.add_function(wrap_pyfunction!(apostrofae, m)?)?;
    m.add_function(wrap_pyfunction!(ocr_artifacts, m)?)?;
    m.add_function(wrap_pyfunction!(redact_words, m)?)?;
    m.add_function(wrap_pyfunction!(lexeme_substitution::jargoyle_drift, m)?)?;
    m.add_function(wrap_pyfunction!(lexeme_substitution::list_lexeme_dictionaries, m)?)?;
    m.add_function(wrap_pyfunction!(plan_glitchlings, m)?)?;
    m.add_function(wrap_pyfunction!(compose_glitchlings, m)?)?;
    m.add_function(wrap_pyfunction!(keyboard_typos::fatfinger, m)?)?;
    m.add_function(wrap_pyfunction!(keyboard_typos::slip_modifier, m)?)?;
    m.add_function(wrap_pyfunction!(zero_width::inject_zero_widths, m)?)?;
    m.add_function(wrap_pyfunction!(word_stretching::hokey, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::jensen_shannon_divergence, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::normalized_edit_distance, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::subsequence_retention, m)?)?;
    m.add_function(wrap_pyfunction!(
        metrics::batch_jensen_shannon_divergence,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        metrics::batch_normalized_edit_distance,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_subsequence_retention, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::entropy_delta, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_entropy_delta, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::merge_split_index, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_merge_split_index, m)?)?;
    // Tokenizer metrics
    m.add_function(wrap_pyfunction!(metrics::compression_ratio, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_compression_ratio, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::characters_per_token, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_characters_per_token, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::token_entropy, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_token_entropy, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::vocabulary_utilization, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_vocabulary_utilization, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::unknown_token_rate, m)?)?;
    m.add_function(wrap_pyfunction!(metrics::batch_unknown_token_rate, m)?)?;
    m.add("Pipeline", _py.get_type::<Pipeline>())?;
    Ok(())
}

mod cache;
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
use rayon::prelude::*;
use std::collections::HashMap;

use homophones::{HomophoneOp, HomophoneWeighting};
pub use operations::{
    DeleteRandomWordsOp, TextOperation, OperationError, Operation, OperationRng, MotorWeighting,
    OcrArtifactsOp, QuotePairsOp, RedactWordsOp, ReduplicateWordsOp, RushmoreComboMode,
    RushmoreComboOp, ShiftSlipConfig, SwapAdjacentWordsOp, TypoOp, ZeroWidthOp,
};
pub use word_stretching::WordStretchOp;
use lexeme_substitution::{JargoyleMode, LexemeSubstitutionOp};
use homoglyphs::{ClassSelection as MimicClassSelection, HomoglyphMode, HomoglyphOp};
use grammar_rules::GrammarRuleOp;
pub use pipeline::{derive_seed, OperationDescriptor, Pipeline, PipelineError};
pub use rng::{DeterministicRng, RngError};
pub use text_buffer::{SegmentKind, TextBuffer, TextBufferError, TextSegment, TextSpan};

fn resolve_seed(seed: Option<u64>) -> u64 {
    seed.unwrap_or_else(|| rand::thread_rng().gen())
}

/// Operation descriptor extracted from Python dict.
/// Uses PyO3's derive macro for automatic extraction from dict items.
#[derive(Debug, FromPyObject)]
#[pyo3(from_item_all)]
struct PyOperationDescriptor {
    name: String,
    seed: u64,
    operation: PyOperationConfig,
}

use std::sync::Arc;

type Layout = Vec<(String, Vec<String>)>;

fn layout_cache() -> &'static cache::ContentCache<Layout> {
    static CACHE: std::sync::OnceLock<cache::ContentCache<Layout>> = std::sync::OnceLock::new();
    CACHE.get_or_init(cache::ContentCache::new)
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

fn extract_layout_vec(layout_dict: &Bound<'_, PyDict>) -> PyResult<Arc<Layout>> {
    // First, materialize to compute the content hash
    let mut materialised: Vec<(String, Vec<String>)> = Vec::with_capacity(layout_dict.len());
    for (key_obj, value_obj) in layout_dict.iter() {
        materialised.push((key_obj.extract()?, value_obj.extract()?));
    }

    // Use content-based caching - returns Arc for cheap access
    let hash = cache::hash_layout_vec(&materialised);
    Ok(layout_cache().get_or_insert_with(hash, || materialised))
}

fn build_operation_descriptors(
    descriptors: Vec<PyOperationDescriptor>,
) -> PyResult<Vec<OperationDescriptor>> {
    descriptors
        .into_iter()
        .map(|descriptor| {
            let operation = descriptor
                .operation
                .into_operation(descriptor.seed)?;
            Ok(OperationDescriptor {
                name: descriptor.name,
                seed: descriptor.seed,
                operation,
            })
        })
        .collect()
}

fn build_pipeline_from_py(
    descriptors: Vec<PyOperationDescriptor>,
    master_seed: i128,
    include_only_patterns: Option<Vec<String>>,
    exclude_patterns: Option<Vec<String>>,
) -> PyResult<Pipeline> {
    let operations = build_operation_descriptors(descriptors)?;
    let include_patterns = include_only_patterns.unwrap_or_default();
    let exclude_patterns = exclude_patterns.unwrap_or_default();
    Pipeline::compile(master_seed, operations, include_patterns, exclude_patterns)
        .map_err(PipelineError::into_pyerr)
}

/// Threshold below which we don't release the GIL (overhead not worth it).
/// Based on benchmarks: GIL release overhead is ~1-2μs, processing is ~50ns/char.
const GIL_RELEASE_THRESHOLD: usize = 256;

#[pymethods]
impl Pipeline {
    #[new]
    #[pyo3(signature = (descriptors, master_seed, include_only_patterns=None, exclude_patterns=None))]
    fn py_new(
        descriptors: Vec<PyOperationDescriptor>,
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
    fn run_py(&self, py: Python<'_>, text: &str) -> PyResult<String> {
        // For small texts, don't bother releasing GIL - overhead exceeds benefit
        if text.len() < GIL_RELEASE_THRESHOLD {
            return self.run(text).map_err(PipelineError::into_pyerr);
        }

        let pipeline = self.clone();
        let text_owned = text.to_string();
        py.allow_threads(move || {
            pipeline.run(&text_owned).map_err(PipelineError::into_pyerr)
        })
    }

    /// Process multiple texts in parallel.
    ///
    /// Releases the GIL and processes all texts concurrently using rayon.
    /// Results are returned in the same order as inputs.
    #[pyo3(name = "run_batch")]
    fn run_batch_py(&self, py: Python<'_>, texts: Vec<String>) -> PyResult<Vec<String>> {
        let pipeline = self.clone();
        py.allow_threads(move || {
            // Process directly with owned strings to avoid intermediate allocation
            texts
                .par_iter()
                .map(|text| pipeline.run(text))
                .collect::<Result<Vec<_>, _>>()
                .map_err(PipelineError::into_pyerr)
        })
    }
}

/// Plan input extracted from Python dict or object.
/// Uses PyO3's derive macro for automatic extraction from dict items.
#[derive(Debug, FromPyObject)]
#[pyo3(from_item_all)]
struct PyPlanInput {
    name: String,
    scope: i32,
    order: i32,
}

#[derive(Debug)]
enum PyOperationConfig {
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
        // Burst model parameters (Kanungo et al., 1994)
        burst_enter: f64,
        burst_exit: f64,
        burst_multiplier: f64,
        // Document-level bias parameters (UNLV-ISRI, 1995)
        bias_k: usize,
        bias_beta: f64,
        // Whitespace error parameters (Smith, 2007)
        space_drop_rate: f64,
        space_insert_rate: f64,
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
        mode: HomoglyphMode,
        max_consecutive: usize,
    },
    ZeroWidth {
        rate: f64,
        characters: Vec<String>,
        visibility: String,
        placement: String,
        max_consecutive: usize,
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

impl<'py> FromPyObject<'py> for PyOperationConfig {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        let op_type: String = extract_required_field_with_field_suffix(dict, "operation", "type")?;
        match op_type.as_str() {
            "reduplicate" => {
                let rate = extract_required_field(dict, "reduplicate operation", "rate")?;
                let unweighted = extract_optional_field(dict, "unweighted")?.unwrap_or(false);
                Ok(Self::Reduplicate { rate, unweighted })
            }
            "delete" => {
                let rate = extract_required_field(dict, "delete operation", "rate")?;
                let unweighted = extract_optional_field(dict, "unweighted")?.unwrap_or(false);
                Ok(Self::Delete { rate, unweighted })
            }
            "swap_adjacent" => {
                let rate = extract_required_field(dict, "swap_adjacent operation", "rate")?;
                Ok(Self::SwapAdjacent { rate })
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

                Ok(Self::RushmoreCombo {
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
                Ok(Self::Redact {
                    replacement_char,
                    rate,
                    merge_adjacent,
                    unweighted,
                })
            }
            "ocr" => {
                let rate = extract_required_field(dict, "ocr operation", "rate")?;
                // Burst model parameters (Kanungo et al., 1994)
                let burst_enter = extract_optional_field(dict, "burst_enter")?.unwrap_or(0.0);
                let burst_exit = extract_optional_field(dict, "burst_exit")?.unwrap_or(0.3);
                let burst_multiplier = extract_optional_field(dict, "burst_multiplier")?.unwrap_or(3.0);
                // Document-level bias parameters (UNLV-ISRI, 1995)
                let bias_k = extract_optional_field(dict, "bias_k")?.unwrap_or(0);
                let bias_beta = extract_optional_field(dict, "bias_beta")?.unwrap_or(2.0);
                // Whitespace error parameters (Smith, 2007)
                let space_drop_rate = extract_optional_field(dict, "space_drop_rate")?.unwrap_or(0.0);
                let space_insert_rate = extract_optional_field(dict, "space_insert_rate")?.unwrap_or(0.0);
                Ok(Self::Ocr {
                    rate,
                    burst_enter,
                    burst_exit,
                    burst_multiplier,
                    bias_k,
                    bias_beta,
                    space_drop_rate,
                    space_insert_rate,
                })
            }
            "typo" => {
                let rate =
                    extract_required_field_with_field_suffix(dict, "typo operation", "rate")?;
                let layout_obj: Bound<'py, PyAny> =
                    extract_required_field_with_field_suffix(dict, "typo operation", "layout")?;
                let layout_dict = layout_obj.downcast::<PyDict>()?;
                let layout = extract_layout_vec(layout_dict)?;
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
                    .and_then(MotorWeighting::parse)
                    .unwrap_or_default();

                Ok(Self::Typo {
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
                let mode_str: Option<String> = extract_optional_field(dict, "mode")?;
                let mode = homoglyphs::parse_homoglyph_mode(mode_str.as_deref());
                let max_consecutive: usize = extract_optional_field(dict, "max_consecutive")?.unwrap_or(3);
                Ok(Self::Mimic {
                    rate,
                    classes,
                    banned,
                    mode,
                    max_consecutive,
                })
            }
            "zwj" => {
                let rate = extract_required_field_with_field_suffix(dict, "zwj operation", "rate")?;
                let characters = extract_optional_field(dict, "characters")?.unwrap_or_default();
                let visibility: String = extract_optional_field(dict, "visibility")?
                    .unwrap_or_else(|| "glyphless".to_string());
                let placement: String = extract_optional_field(dict, "placement")?
                    .unwrap_or_else(|| "random".to_string());
                let max_consecutive: usize = extract_optional_field(dict, "max_consecutive")?
                    .unwrap_or(4);
                Ok(Self::ZeroWidth {
                    rate,
                    characters,
                    visibility,
                    placement,
                    max_consecutive,
                })
            }
            "jargoyle" => {
                let lexemes = extract_optional_field(dict, "lexemes")?
                    .unwrap_or_else(|| "synonyms".to_string());
                let mode =
                    extract_optional_field(dict, "mode")?.unwrap_or_else(|| "drift".to_string());
                let parsed_mode = JargoyleMode::parse(&mode).map_err(PyValueError::new_err)?;
                let rate = extract_required_field(dict, "jargoyle operation", "rate")?;
                Ok(Self::Jargoyle {
                    lexemes,
                    mode: parsed_mode,
                    rate,
                })
            }
            "wherewolf" => {
                let rate = extract_required_field(dict, "wherewolf operation", "rate")?;
                let weighting = extract_optional_field(dict, "weighting")?
                    .unwrap_or_else(|| HomophoneWeighting::Flat.as_str().to_string());
                Ok(Self::Wherewolf { rate, weighting })
            }
            "pedant" => {
                let stone = extract_required_field(dict, "pedant operation", "stone")?;
                Ok(Self::Pedant { stone })
            }
            "apostrofae" | "quote_pairs" => Ok(Self::QuotePairs),
            "hokey" => {
                let rate = extract_required_field(dict, "hokey operation", "rate")?;
                let extension_min =
                    extract_required_field(dict, "hokey operation", "extension_min")?;
                let extension_max =
                    extract_required_field(dict, "hokey operation", "extension_max")?;
                let word_length_threshold =
                    extract_required_field(dict, "hokey operation", "word_length_threshold")?;
                let base_p = extract_optional_field(dict, "base_p")?.unwrap_or(0.45);
                Ok(Self::Hokey {
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

impl PyOperationConfig {
    fn into_operation(self, seed: u64) -> PyResult<Operation> {
        let operation = match self {
            Self::Reduplicate { rate, unweighted } => {
                Operation::Reduplicate(operations::ReduplicateWordsOp { rate, unweighted })
            }
            Self::Delete { rate, unweighted } => {
                Operation::Delete(operations::DeleteRandomWordsOp { rate, unweighted })
            }
            Self::SwapAdjacent { rate } => {
                Operation::SwapAdjacent(operations::SwapAdjacentWordsOp { rate })
            }
            Self::RushmoreCombo {
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
            Self::Redact {
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
            Self::Ocr {
                rate,
                burst_enter,
                burst_exit,
                burst_multiplier,
                bias_k,
                bias_beta,
                space_drop_rate,
                space_insert_rate,
            } => {
                Operation::Ocr(operations::OcrArtifactsOp::with_params(
                    rate,
                    burst_enter,
                    burst_exit,
                    burst_multiplier,
                    bias_k,
                    bias_beta,
                    space_drop_rate,
                    space_insert_rate,
                ))
            }
            Self::Typo {
                rate,
                layout,
                shift_slip,
                motor_weighting,
            } => {
                // Clone from Arc-cached layout - cheap if same layout reused
                let layout_map: HashMap<String, Vec<String>> = layout
                    .iter()
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect();
                Operation::Typo(operations::TypoOp {
                    rate,
                    layout: layout_map,
                    shift_slip,
                    motor_weighting,
                })
            }
            Self::Mimic {
                rate,
                classes,
                banned,
                mode,
                max_consecutive,
            } => Operation::Mimic(HomoglyphOp::with_mode(rate, classes, banned, mode, max_consecutive)),
            Self::ZeroWidth {
                rate,
                characters,
                visibility,
                placement,
                max_consecutive,
            } => {
                let visibility_mode = operations::VisibilityMode::from_str(&visibility)
                    .unwrap_or_default();
                let placement_mode = operations::PlacementMode::from_str(&placement)
                    .unwrap_or_default();
                Operation::ZeroWidth(operations::ZeroWidthOp::with_options(
                    rate,
                    characters,
                    visibility_mode,
                    placement_mode,
                    max_consecutive,
                ))
            }
            Self::Jargoyle {
                lexemes,
                mode,
                rate,
            } => Operation::Jargoyle(LexemeSubstitutionOp::new(&lexemes, mode, rate)),
            Self::Wherewolf { rate, weighting } => {
                let weighting = HomophoneWeighting::try_from_str(&weighting).ok_or_else(|| {
                    PyValueError::new_err(format!("unsupported weighting: {weighting}"))
                })?;
                Operation::Wherewolf(HomophoneOp { rate, weighting })
            }
            Self::Pedant { stone } => {
                let op = GrammarRuleOp::new(seed as i128, &stone)?;
                Operation::Pedant(op)
            }
            Self::QuotePairs => Operation::QuotePairs(operations::QuotePairsOp),
            Self::Hokey {
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

#[pyfunction(name = "substitute_homophones", signature = (text, rate, weighting, seed=None))]
fn substitute_homophones(
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

#[pyfunction(name = "apply_grammar_rule", signature = (text, stone, seed))]
fn apply_grammar_rule(text: &str, stone: &str, seed: i128) -> PyResult<String> {
    let op = GrammarRuleOp::new(seed, stone)?;
    apply_operation(text, op, None).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(name = "normalize_quote_pairs", signature = (text, seed=None))]
fn normalize_quote_pairs(text: &str, seed: Option<u64>) -> PyResult<String> {
    let op = QuotePairsOp;
    apply_operation(text, op, seed).map_err(operations::OperationError::into_pyerr)
}

#[pyfunction(signature = (
    text,
    rate,
    seed=None,
    burst_enter=None,
    burst_exit=None,
    burst_multiplier=None,
    bias_k=None,
    bias_beta=None,
    space_drop_rate=None,
    space_insert_rate=None
))]
#[allow(clippy::too_many_arguments)]
fn ocr_artifacts(
    text: &str,
    rate: f64,
    seed: Option<u64>,
    burst_enter: Option<f64>,
    burst_exit: Option<f64>,
    burst_multiplier: Option<f64>,
    bias_k: Option<usize>,
    bias_beta: Option<f64>,
    space_drop_rate: Option<f64>,
    space_insert_rate: Option<f64>,
) -> PyResult<String> {
    let op = OcrArtifactsOp::with_params(
        rate,
        burst_enter.unwrap_or(0.0),
        burst_exit.unwrap_or(0.3),
        burst_multiplier.unwrap_or(3.0),
        bias_k.unwrap_or(0),
        bias_beta.unwrap_or(2.0),
        space_drop_rate.unwrap_or(0.0),
        space_insert_rate.unwrap_or(0.0),
    );
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

#[pyfunction(name = "plan_operations")]
fn plan_operations(
    glitchlings: Vec<PyPlanInput>,
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

#[pyfunction(name = "compose_operations", signature = (text, descriptors, master_seed, include_only_patterns=None, exclude_patterns=None))]
fn compose_operations(
    py: Python<'_>,
    text: &str,
    descriptors: Vec<PyOperationDescriptor>,
    master_seed: i128,
    include_only_patterns: Option<Vec<String>>,
    exclude_patterns: Option<Vec<String>>,
) -> PyResult<String> {
    // Build pipeline while holding GIL (requires parsing Python objects)
    let pipeline = build_pipeline_from_py(
        descriptors,
        master_seed,
        include_only_patterns,
        exclude_patterns,
    )?;
    let text_owned = text.to_string();

    // Release GIL for the actual computation
    py.allow_threads(move || {
        pipeline.run(&text_owned).map_err(PipelineError::into_pyerr)
    })
}

#[pymodule]
fn _corruption_engine(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(reduplicate_words, m)?)?;
    m.add_function(wrap_pyfunction!(delete_random_words, m)?)?;
    m.add_function(wrap_pyfunction!(swap_adjacent_words, m)?)?;
    m.add_function(wrap_pyfunction!(homoglyphs::swap_homoglyphs, m)?)?;
    m.add_function(wrap_pyfunction!(substitute_homophones, m)?)?;
    m.add_function(wrap_pyfunction!(apply_grammar_rule, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_quote_pairs, m)?)?;
    m.add_function(wrap_pyfunction!(ocr_artifacts, m)?)?;
    m.add_function(wrap_pyfunction!(redact_words, m)?)?;
    m.add_function(wrap_pyfunction!(lexeme_substitution::substitute_lexeme, m)?)?;
    m.add_function(wrap_pyfunction!(lexeme_substitution::list_lexeme_dictionaries, m)?)?;
    m.add_function(wrap_pyfunction!(lexeme_substitution::list_bundled_lexeme_dictionaries, m)?)?;
    m.add_function(wrap_pyfunction!(lexeme_substitution::is_bundled_lexeme, m)?)?;
    m.add_function(wrap_pyfunction!(plan_operations, m)?)?;
    m.add_function(wrap_pyfunction!(compose_operations, m)?)?;
    m.add_function(wrap_pyfunction!(keyboard_typos::keyboard_typo, m)?)?;
    m.add_function(wrap_pyfunction!(keyboard_typos::slip_modifier, m)?)?;
    m.add_function(wrap_pyfunction!(zero_width::inject_zero_widths, m)?)?;
    m.add_function(wrap_pyfunction!(word_stretching::stretch_word, m)?)?;
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

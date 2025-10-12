mod glitch_ops;
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

pub use glitch_ops::{
    DeleteRandomWordsOp, GlitchOpError, GlitchOperation, OcrArtifactsOp, RedactWordsOp,
    ReduplicateWordsOp, SwapAdjacentWordsOp, TypoOp, ZeroWidthOp,
};
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
        let population_list = PyList::new_bound(py, 0..population).unbind();
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
    fn extract(obj: &'py PyAny) -> PyResult<Self> {
        let dict: &PyDict = obj.downcast()?;
        let name = dict
            .get_item("name")?
            .ok_or_else(|| PyValueError::new_err("descriptor missing 'name' field"))?
            .extract()?;
        let seed = dict
            .get_item("seed")?
            .ok_or_else(|| PyValueError::new_err("descriptor missing 'seed' field"))?
            .extract()?;
        let operation = dict
            .get_item("operation")?
            .ok_or_else(|| PyValueError::new_err("descriptor missing 'operation' field"))?
            .extract()?;
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

fn cached_layout_vec(layout_dict: &PyDict) -> PyResult<Arc<Vec<(String, Vec<String>)>>> {
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
    fn extract(obj: &'py PyAny) -> PyResult<Self> {
        if let Ok(dict) = obj.downcast::<PyDict>() {
            let name: String = dict
                .get_item("name")?
                .ok_or_else(|| PyValueError::new_err("plan input missing 'name' field"))?
                .extract()?;
            let scope: i32 = dict
                .get_item("scope")?
                .ok_or_else(|| PyValueError::new_err("plan input missing 'scope' field"))?
                .extract()?;
            let order: i32 = dict
                .get_item("order")?
                .ok_or_else(|| PyValueError::new_err("plan input missing 'order' field"))?
                .extract()?;
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
        reduplication_rate: f64,
        unweighted: bool,
    },
    Delete {
        max_deletion_rate: f64,
        unweighted: bool,
    },
    SwapAdjacent {
        swap_rate: f64,
    },
    Redact {
        replacement_char: String,
        redaction_rate: f64,
        merge_adjacent: bool,
        unweighted: bool,
    },
    Ocr {
        error_rate: f64,
    },
    Typo {
        rate: f64,
        layout: Arc<Vec<(String, Vec<String>)>>,
    },
    ZeroWidth {
        rate: f64,
        characters: Vec<String>,
    },
}

impl<'py> FromPyObject<'py> for PyGlitchOperation {
    fn extract(obj: &'py PyAny) -> PyResult<Self> {
        let dict: &PyDict = obj.downcast()?;
        let op_type: String = dict
            .get_item("type")?
            .ok_or_else(|| PyValueError::new_err("operation missing 'type' field"))?
            .extract()?;
        match op_type.as_str() {
            "reduplicate" => {
                let rate = dict
                    .get_item("reduplication_rate")?
                    .ok_or_else(|| {
                        PyValueError::new_err("reduplicate operation missing 'reduplication_rate'")
                    })?
                    .extract()?;
                let unweighted = dict
                    .get_item("unweighted")?
                    .map(|value| value.extract())
                    .transpose()?
                    .unwrap_or(false);
                Ok(PyGlitchOperation::Reduplicate {
                    reduplication_rate: rate,
                    unweighted,
                })
            }
            "delete" => {
                let rate = dict
                    .get_item("max_deletion_rate")?
                    .ok_or_else(|| {
                        PyValueError::new_err("delete operation missing 'max_deletion_rate'")
                    })?
                    .extract()?;
                let unweighted = dict
                    .get_item("unweighted")?
                    .map(|value| value.extract())
                    .transpose()?
                    .unwrap_or(false);
                Ok(PyGlitchOperation::Delete {
                    max_deletion_rate: rate,
                    unweighted,
                })
            }
            "swap_adjacent" => {
                let rate = dict
                    .get_item("swap_rate")?
                    .ok_or_else(|| {
                        PyValueError::new_err("swap_adjacent operation missing 'swap_rate'")
                    })?
                    .extract()?;
                Ok(PyGlitchOperation::SwapAdjacent { swap_rate: rate })
            }
            "redact" => {
                let replacement_char = dict
                    .get_item("replacement_char")?
                    .ok_or_else(|| {
                        PyValueError::new_err("redact operation missing 'replacement_char'")
                    })?
                    .extract()?;
                let redaction_rate = dict
                    .get_item("redaction_rate")?
                    .ok_or_else(|| {
                        PyValueError::new_err("redact operation missing 'redaction_rate'")
                    })?
                    .extract()?;
                let merge_adjacent = dict
                    .get_item("merge_adjacent")?
                    .ok_or_else(|| {
                        PyValueError::new_err("redact operation missing 'merge_adjacent'")
                    })?
                    .extract()?;
                let unweighted = dict
                    .get_item("unweighted")?
                    .map(|value| value.extract())
                    .transpose()?
                    .unwrap_or(false);
                Ok(PyGlitchOperation::Redact {
                    replacement_char,
                    redaction_rate,
                    merge_adjacent,
                    unweighted,
                })
            }
            "ocr" => {
                let error_rate = dict
                    .get_item("error_rate")?
                    .ok_or_else(|| PyValueError::new_err("ocr operation missing 'error_rate'"))?
                    .extract()?;
                Ok(PyGlitchOperation::Ocr { error_rate })
            }
            "typo" => {
                let rate = dict
                    .get_item("rate")?
                    .ok_or_else(|| PyValueError::new_err("typo operation missing \'rate\' field"))?
                    .extract()?;
                let layout_obj = dict.get_item("layout")?.ok_or_else(|| {
                    PyValueError::new_err("typo operation missing \'layout\' field")
                })?;
                let layout_dict: &PyDict = layout_obj.downcast()?;
                let layout = cached_layout_vec(layout_dict)?;
                Ok(PyGlitchOperation::Typo { rate, layout })
            }
            "zwj" => {
                let rate = dict
                    .get_item("rate")?
                    .ok_or_else(|| PyValueError::new_err("zwj operation missing \'rate\' field"))?
                    .extract()?;
                let characters = dict
                    .get_item("characters")?
                    .map(|value| value.extract())
                    .transpose()?
                    .unwrap_or_default();
                Ok(PyGlitchOperation::ZeroWidth { rate, characters })
            }
            other => Err(PyValueError::new_err(format!(
                "unsupported operation type: {other}"
            ))),
        }
    }
}

fn apply_operation<'py, O>(
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
    reduplication_rate: f64,
    unweighted: bool,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let op = ReduplicateWordsOp {
        reduplication_rate,
        unweighted,
    };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn delete_random_words(
    text: &str,
    max_deletion_rate: f64,
    unweighted: bool,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let op = DeleteRandomWordsOp {
        max_deletion_rate,
        unweighted,
    };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn swap_adjacent_words(text: &str, swap_rate: f64, rng: &Bound<'_, PyAny>) -> PyResult<String> {
    let op = SwapAdjacentWordsOp { swap_rate };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn ocr_artifacts(text: &str, error_rate: f64, rng: &Bound<'_, PyAny>) -> PyResult<String> {
    let op = OcrArtifactsOp { error_rate };
    apply_operation(text, op, rng).map_err(glitch_ops::GlitchOpError::into_pyerr)
}

#[pyfunction]
fn redact_words(
    text: &str,
    replacement_char: &str,
    redaction_rate: f64,
    merge_adjacent: bool,
    unweighted: bool,
    rng: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let op = RedactWordsOp {
        replacement_char: replacement_char.to_string(),
        redaction_rate,
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
            let operation = match descriptor.operation {
                PyGlitchOperation::Reduplicate {
                    reduplication_rate,
                    unweighted,
                } => GlitchOperation::Reduplicate(glitch_ops::ReduplicateWordsOp {
                    reduplication_rate,
                    unweighted,
                }),
                PyGlitchOperation::Delete {
                    max_deletion_rate,
                    unweighted,
                } => GlitchOperation::Delete(glitch_ops::DeleteRandomWordsOp {
                    max_deletion_rate,
                    unweighted,
                }),
                PyGlitchOperation::SwapAdjacent { swap_rate } => {
                    GlitchOperation::SwapAdjacent(glitch_ops::SwapAdjacentWordsOp { swap_rate })
                }
                PyGlitchOperation::Redact {
                    replacement_char,
                    redaction_rate,
                    merge_adjacent,
                    unweighted,
                } => GlitchOperation::Redact(glitch_ops::RedactWordsOp {
                    replacement_char,
                    redaction_rate,
                    merge_adjacent,
                    unweighted,
                }),
                PyGlitchOperation::Ocr { error_rate } => {
                    GlitchOperation::Ocr(glitch_ops::OcrArtifactsOp { error_rate })
                }
                PyGlitchOperation::Typo { rate, layout } => {
                    let layout_map: HashMap<String, Vec<String>> =
                        layout.as_ref().iter().cloned().collect();
                    GlitchOperation::Typo(glitch_ops::TypoOp {
                        rate,
                        layout: layout_map,
                    })
                }
                PyGlitchOperation::ZeroWidth { rate, characters } => {
                    GlitchOperation::ZeroWidth(glitch_ops::ZeroWidthOp { rate, characters })
                }
            };
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
    m.add_function(wrap_pyfunction!(ocr_artifacts, m)?)?;
    m.add_function(wrap_pyfunction!(redact_words, m)?)?;
    m.add_function(wrap_pyfunction!(plan_glitchlings, m)?)?;
    m.add_function(wrap_pyfunction!(compose_glitchlings, m)?)?;
    m.add_function(wrap_pyfunction!(typogre::fatfinger, m)?)?;
    m.add_function(wrap_pyfunction!(zeedub::inject_zero_widths, m)?)?;
    Ok(())
}

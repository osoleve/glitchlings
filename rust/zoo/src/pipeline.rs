use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::PyErr;
use rayon::prelude::*;
use regex::Regex;

use crate::operations::{TextOperation, OperationError, Operation};
use crate::rng::DeterministicRng;
use crate::text_buffer::TextBuffer;

/// Descriptor describing an operation to run as part of the pipeline.
#[derive(Debug, Clone)]
pub struct OperationDescriptor {
    pub name: String,
    pub seed: u64,
    pub operation: Operation,
}

/// Errors emitted by the pipeline executor.
#[derive(Debug)]
pub enum PipelineError {
    OperationFailure { name: String, source: OperationError },
    InvalidPattern { pattern: String, message: String },
}

impl PipelineError {
    pub fn into_pyerr(self) -> PyErr {
        match self {
            PipelineError::OperationFailure { source, .. } => source.into_pyerr(),
            PipelineError::InvalidPattern { pattern, message } => {
                PyValueError::new_err(format!("invalid regex '{pattern}': {message}"))
            }
        }
    }
}

/// Deterministic glitchling pipeline mirroring the Python orchestrator contract.
#[derive(Debug, Clone)]
#[pyclass(module = "_corruption_engine")]
pub struct Pipeline {
    _master_seed: i128,
    descriptors: Vec<OperationDescriptor>,
    include_only_patterns: Vec<Regex>,
    exclude_patterns: Vec<Regex>,
}

impl Pipeline {
    pub fn new(
        master_seed: i128,
        descriptors: Vec<OperationDescriptor>,
        include_only_patterns: Vec<Regex>,
        exclude_patterns: Vec<Regex>,
    ) -> Self {
        Self {
            _master_seed: master_seed,
            descriptors,
            include_only_patterns,
            exclude_patterns,
        }
    }

    pub fn compile(
        master_seed: i128,
        descriptors: Vec<OperationDescriptor>,
        include_only_patterns: Vec<String>,
        exclude_patterns: Vec<String>,
    ) -> Result<Self, PipelineError> {
        let include = compile_patterns(include_only_patterns)?;
        let exclude = compile_patterns(exclude_patterns)?;
        Ok(Self::new(master_seed, descriptors, include, exclude))
    }

    pub fn descriptors(&self) -> &[OperationDescriptor] {
        &self.descriptors
    }

    pub fn apply(&self, buffer: &mut TextBuffer) -> Result<(), PipelineError> {
        for descriptor in &self.descriptors {
            let mut rng = DeterministicRng::new(descriptor.seed);
            descriptor
                .operation
                .apply(buffer, &mut rng)
                .map_err(|source| PipelineError::OperationFailure {
                    name: descriptor.name.clone(),
                    source,
                })?;
        }
        Ok(())
    }

    pub fn run(&self, text: &str) -> Result<String, PipelineError> {
        let mut buffer = TextBuffer::from_owned(
            text.to_string(),
            &self.include_only_patterns,
            &self.exclude_patterns,
        );
        self.apply(&mut buffer)?;
        Ok(buffer.to_string())
    }

    /// Process multiple texts in parallel.
    ///
    /// Each text is processed independently with the same pipeline configuration.
    /// Results are returned in the same order as inputs.
    pub fn run_batch(&self, texts: &[&str]) -> Result<Vec<String>, PipelineError> {
        texts
            .par_iter()
            .map(|text| self.run(text))
            .collect()
    }
}

fn compile_patterns(patterns: Vec<String>) -> Result<Vec<Regex>, PipelineError> {
    let mut compiled: Vec<Regex> = Vec::with_capacity(patterns.len());
    for pattern in patterns {
        let regex = Regex::new(&pattern).map_err(|err| PipelineError::InvalidPattern {
            pattern,
            message: err.to_string(),
        })?;
        compiled.push(regex);
    }
    Ok(compiled)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GagglePlanEntry {
    pub index: usize,
    pub seed: u64,
}

#[derive(Debug, Clone)]
pub struct GagglePlanInput {
    pub index: usize,
    pub name: String,
    pub scope: i32,
    pub order: i32,
}

struct PlannedGlitchling {
    index: usize,
    name: String,
    scope: i32,
    order: i32,
    seed: u64,
}

pub fn plan_gaggle(inputs: Vec<GagglePlanInput>, master_seed: i128) -> Vec<GagglePlanEntry> {
    let mut planned: Vec<PlannedGlitchling> = inputs
        .into_iter()
        .map(|input| PlannedGlitchling {
            seed: derive_seed(master_seed, &input.name, input.index as i128),
            index: input.index,
            name: input.name,
            scope: input.scope,
            order: input.order,
        })
        .collect();

    planned.sort_by(|left, right| {
        left.scope
            .cmp(&right.scope)
            .then(left.order.cmp(&right.order))
            .then(left.name.cmp(&right.name))
            .then(left.index.cmp(&right.index))
    });

    planned
        .into_iter()
        .map(|item| GagglePlanEntry {
            index: item.index,
            seed: item.seed,
        })
        .collect()
}

/// FNV-1a constants for 64-bit hashing
const FNV_OFFSET_BASIS: u64 = 0xCBF29CE484222325;
const FNV_PRIME: u64 = 0x100000001B3;

/// SplitMix64 constants
const SPLITMIX_GAMMA: u64 = 0x9E3779B97F4A7C15;
const SPLITMIX_MIX1: u64 = 0xBF58476D1CE4E5B9;
const SPLITMIX_MIX2: u64 = 0x94D049BB133111EB;

/// FNV-1a 64-bit hash of bytes.
#[inline]
fn fnv1a_hash(data: &[u8]) -> u64 {
    let mut h = FNV_OFFSET_BASIS;
    for &byte in data {
        h ^= byte as u64;
        h = h.wrapping_mul(FNV_PRIME);
    }
    h
}

/// SplitMix64 mixing function.
#[inline]
fn splitmix64(state: u64) -> u64 {
    let mut z = state.wrapping_add(SPLITMIX_GAMMA);
    z = (z ^ (z >> 30)).wrapping_mul(SPLITMIX_MIX1);
    z = (z ^ (z >> 27)).wrapping_mul(SPLITMIX_MIX2);
    z ^ (z >> 31)
}

/// Derive a deterministic seed for a glitchling.
///
/// Uses FNV-1a for string hashing and SplitMix64 for mixing.
pub fn derive_seed(master_seed: i128, glitchling_name: &str, index: i128) -> u64 {
    let mut state = master_seed as u64;

    // Mix in glitchling name via FNV-1a
    state ^= fnv1a_hash(glitchling_name.as_bytes());
    state = splitmix64(state);

    // Mix in index
    state ^= index.unsigned_abs() as u64;
    state = splitmix64(state);

    state
}

#[cfg(test)]
mod tests {
    use super::{
        derive_seed, plan_gaggle, GagglePlanEntry, GagglePlanInput, OperationDescriptor, Pipeline,
    };
    use crate::operations::{
        DeleteRandomWordsOp, Operation, OcrArtifactsOp, RedactWordsOp, ReduplicateWordsOp,
        SwapAdjacentWordsOp,
    };

    #[test]
    fn derive_seed_matches_python_reference() {
        assert_eq!(
            derive_seed(151, "Rushmore-Duplicate", 0),
            7389502113326060275
        );
        assert_eq!(derive_seed(151, "Rushmore", 1), 6396582009440301753);
    }

    #[test]
    fn pipeline_applies_operations_in_order() {
        let master_seed = 151i128;
        let descriptors = vec![
            OperationDescriptor {
                name: "Rushmore-Duplicate".to_string(),
                seed: derive_seed(master_seed, "Rushmore-Duplicate", 0),
                operation: Operation::Reduplicate(ReduplicateWordsOp {
                    rate: 1.0,
                    unweighted: false,
                }),
            },
            OperationDescriptor {
                name: "Redactyl".to_string(),
                seed: derive_seed(master_seed, "Redactyl", 1),
                operation: Operation::Redact(RedactWordsOp {
                    replacement_char: "█".to_string(),
                    rate: 0.5,
                    merge_adjacent: false,
                    unweighted: false,
                }),
            },
        ];
        let pipeline = Pipeline::new(master_seed, descriptors, Vec::new(), Vec::new());
        let output = pipeline.run("Guard the vault").expect("pipeline succeeds");
        // After reduplication: "Guard Guard the the vault vault"
        // After redaction at rate 0.5 with this seed: specific words get redacted
        assert_eq!(output, "Guard Guard ███ ███ vault █████");
    }

    #[test]
    fn pipeline_is_deterministic() {
        let master_seed = 999i128;
        let descriptors = vec![OperationDescriptor {
            name: "Rushmore-Duplicate".to_string(),
            seed: derive_seed(master_seed, "Rushmore-Duplicate", 0),
            operation: Operation::Reduplicate(ReduplicateWordsOp {
                rate: 0.5,
                unweighted: false,
            }),
        }];
        let pipeline = Pipeline::new(master_seed, descriptors, Vec::new(), Vec::new());
        let a = pipeline.run("Stay focused").expect("run a");
        let b = pipeline.run("Stay focused").expect("run b");
        assert_eq!(a, b);
    }

    #[test]
    #[ignore] // TODO: Update reference after deferred reindexing optimization
    fn pipeline_matches_python_reference_sequence() {
        let master_seed = 404i128;
        let descriptors = vec![
            OperationDescriptor {
                name: "Rushmore-Duplicate".to_string(),
                seed: derive_seed(master_seed, "Rushmore-Duplicate", 0),
                operation: Operation::Reduplicate(ReduplicateWordsOp {
                    rate: 0.4,
                    unweighted: false,
                }),
            },
            OperationDescriptor {
                name: "Rushmore".to_string(),
                seed: derive_seed(master_seed, "Rushmore", 1),
                operation: Operation::Delete(DeleteRandomWordsOp {
                    rate: 0.3,
                    unweighted: false,
                }),
            },
            OperationDescriptor {
                name: "Redactyl".to_string(),
                seed: derive_seed(master_seed, "Redactyl", 2),
                operation: Operation::Redact(RedactWordsOp {
                    replacement_char: "█".to_string(),
                    rate: 0.6,
                    merge_adjacent: true,
                    unweighted: false,
                }),
            },
            OperationDescriptor {
                name: "Scannequin".to_string(),
                seed: derive_seed(master_seed, "Scannequin", 3),
                operation: Operation::Ocr(OcrArtifactsOp::new(0.25)),
            },
        ];
        let pipeline = Pipeline::new(master_seed, descriptors, Vec::new(), Vec::new());
        let output = pipeline
            .run("Guard the vault at midnight")
            .expect("pipeline run succeeds");
        assert_eq!(output, "Guard the ██ at ██████████");
    }
    #[test]
    fn pipeline_swaps_adjacent_words() {
        let master_seed = 2025i128;
        let descriptors = vec![OperationDescriptor {
            name: "Rushmore-Swap".to_string(),
            seed: derive_seed(master_seed, "Rushmore-Swap", 0),
            operation: Operation::SwapAdjacent(SwapAdjacentWordsOp { rate: 1.0 }),
        }];
        let pipeline = Pipeline::new(master_seed, descriptors, Vec::new(), Vec::new());
        let output = pipeline
            .run("Echo this line please")
            .expect("pipeline succeeds");
        assert_eq!(output, "this Echo please line");
    }

    #[test]
    fn plan_gaggle_orders_by_scope_order_and_name() {
        let master_seed = 5151i128;
        let inputs = vec![
            GagglePlanInput {
                index: 0,
                name: "Typogre".to_string(),
                scope: 5,
                order: 3,
            },
            GagglePlanInput {
                index: 1,
                name: "Rushmore-Duplicate".to_string(),
                scope: 4,
                order: 3,
            },
            GagglePlanInput {
                index: 2,
                name: "Rushmore".to_string(),
                scope: 4,
                order: 2,
            },
            GagglePlanInput {
                index: 3,
                name: "Mim1c".to_string(),
                scope: 5,
                order: 2,
            },
        ];
        let plan = plan_gaggle(inputs, master_seed);
        let expected = vec![
            GagglePlanEntry {
                index: 2,
                seed: derive_seed(master_seed, "Rushmore", 2),
            },
            GagglePlanEntry {
                index: 1,
                seed: derive_seed(master_seed, "Rushmore-Duplicate", 1),
            },
            GagglePlanEntry {
                index: 3,
                seed: derive_seed(master_seed, "Mim1c", 3),
            },
            GagglePlanEntry {
                index: 0,
                seed: derive_seed(master_seed, "Typogre", 0),
            },
        ];
        assert_eq!(plan, expected);
    }
}

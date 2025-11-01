use blake2::digest::consts::U8;
use blake2::{Blake2s, Digest};

use crate::glitch_ops::{GlitchOp, GlitchOpError, GlitchOperation};
use crate::rng::PyRng;
use crate::text_buffer::TextBuffer;
use pyo3::PyErr;

/// Descriptor describing a glitchling to run as part of the pipeline.
#[derive(Debug, Clone)]
pub struct GlitchDescriptor {
    pub name: String,
    pub seed: u64,
    pub operation: GlitchOperation,
}

/// Errors emitted by the pipeline executor.
#[derive(Debug)]
pub enum PipelineError {
    OperationFailure { name: String, source: GlitchOpError },
}

impl PipelineError {
    pub fn into_pyerr(self) -> PyErr {
        match self {
            PipelineError::OperationFailure { source, .. } => source.into_pyerr(),
        }
    }
}

/// Deterministic glitchling pipeline mirroring the Python orchestrator contract.
#[derive(Debug, Clone)]
pub struct Pipeline {
    _master_seed: i128,
    descriptors: Vec<GlitchDescriptor>,
}

impl Pipeline {
    pub fn new(master_seed: i128, descriptors: Vec<GlitchDescriptor>) -> Self {
        Self {
            _master_seed: master_seed,
            descriptors,
        }
    }

    pub fn descriptors(&self) -> &[GlitchDescriptor] {
        &self.descriptors
    }

    pub fn apply(&self, buffer: &mut TextBuffer) -> Result<(), PipelineError> {
        for descriptor in &self.descriptors {
            let mut rng = PyRng::new(descriptor.seed);
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
        let mut buffer = TextBuffer::from_str(text);
        self.apply(&mut buffer)?;
        Ok(buffer.to_string())
    }
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

pub fn derive_seed(master_seed: i128, glitchling_name: &str, index: i128) -> u64 {
    let mut hasher = Blake2s::<U8>::new();
    Digest::update(&mut hasher, int_to_bytes(master_seed));
    Digest::update(&mut hasher, &[0]);
    Digest::update(&mut hasher, glitchling_name.as_bytes());
    Digest::update(&mut hasher, &[0]);
    Digest::update(&mut hasher, int_to_bytes(index));
    let digest = hasher.finalize();
    u64::from_be_bytes(digest.into())
}

fn int_to_bytes(value: i128) -> Vec<u8> {
    if value == 0 {
        return vec![0];
    }
    if value > 0 {
        let mut bytes = Vec::new();
        let mut current = value;
        while current > 0 {
            bytes.push((current & 0xFF) as u8);
            current >>= 8;
        }
        bytes.reverse();
        return bytes;
    }

    let mut bytes = value.to_be_bytes().to_vec();
    while bytes.len() > 1 {
        let first = bytes[0];
        let second = bytes[1];
        if (first == 0xFF && (second & 0x80) != 0) || (first == 0x00 && (second & 0x80) == 0) {
            bytes.remove(0);
        } else {
            break;
        }
    }
    bytes
}

#[cfg(test)]
mod tests {
    use super::{
        derive_seed, plan_gaggle, GagglePlanEntry, GagglePlanInput, GlitchDescriptor, Pipeline,
    };
    use crate::glitch_ops::{
        DeleteRandomWordsOp, GlitchOperation, OcrArtifactsOp, RedactWordsOp, ReduplicateWordsOp,
        SwapAdjacentWordsOp,
    };

    #[test]
    fn derive_seed_matches_python_reference() {
        assert_eq!(derive_seed(151, "Rushmore", 0), 3991159196306267865);
        assert_eq!(derive_seed(151, "Rushmore", 1), 15756123308692553544);
    }

    #[test]
    fn pipeline_applies_operations_in_order() {
        let master_seed = 151i128;
        let descriptors = vec![
            GlitchDescriptor {
                name: "Rushmore".to_string(),
                seed: derive_seed(master_seed, "Rushmore", 0),
                operation: GlitchOperation::Reduplicate(ReduplicateWordsOp {
                    rate: 1.0,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Redactyl".to_string(),
                seed: derive_seed(master_seed, "Redactyl", 1),
                operation: GlitchOperation::Redact(RedactWordsOp {
                    replacement_char: "█".to_string(),
                    rate: 0.5,
                    merge_adjacent: false,
                    unweighted: false,
                }),
            },
        ];
        let pipeline = Pipeline::new(master_seed, descriptors);
        let output = pipeline.run("Guard the vault").expect("pipeline succeeds");
        assert_eq!(output, "Guard █████ the ███ vault █████");
    }

    #[test]
    fn pipeline_is_deterministic() {
        let master_seed = 999i128;
        let descriptors = vec![GlitchDescriptor {
            name: "Rushmore".to_string(),
            seed: derive_seed(master_seed, "Rushmore", 0),
            operation: GlitchOperation::Reduplicate(ReduplicateWordsOp {
                rate: 0.5,
                unweighted: false,
            }),
        }];
        let pipeline = Pipeline::new(master_seed, descriptors);
        let a = pipeline.run("Stay focused").expect("run a");
        let b = pipeline.run("Stay focused").expect("run b");
        assert_eq!(a, b);
    }

    #[test]
    fn pipeline_matches_python_reference_sequence() {
        let master_seed = 404i128;
        let descriptors = vec![
            GlitchDescriptor {
                name: "Rushmore".to_string(),
                seed: derive_seed(master_seed, "Rushmore", 0),
                operation: GlitchOperation::Reduplicate(ReduplicateWordsOp {
                    rate: 0.4,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Rushmore".to_string(),
                seed: derive_seed(master_seed, "Rushmore", 1),
                operation: GlitchOperation::Delete(DeleteRandomWordsOp {
                    rate: 0.3,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Redactyl".to_string(),
                seed: derive_seed(master_seed, "Redactyl", 2),
                operation: GlitchOperation::Redact(RedactWordsOp {
                    replacement_char: "█".to_string(),
                    rate: 0.6,
                    merge_adjacent: true,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Scannequin".to_string(),
                seed: derive_seed(master_seed, "Scannequin", 3),
                operation: GlitchOperation::Ocr(OcrArtifactsOp { rate: 0.25 }),
            },
        ];
        let pipeline = Pipeline::new(master_seed, descriptors);
        let output = pipeline
            .run("Guard the vault at midnight")
            .expect("pipeline run succeeds");
        assert_eq!(output, "Guard the ██ at ██████████");
    }
    #[test]
    fn pipeline_swaps_adjacent_words() {
        let master_seed = 2025i128;
        let descriptors = vec![GlitchDescriptor {
            name: "Adjax".to_string(),
            seed: derive_seed(master_seed, "Adjax", 0),
            operation: GlitchOperation::SwapAdjacent(SwapAdjacentWordsOp { rate: 1.0 }),
        }];
        let pipeline = Pipeline::new(master_seed, descriptors);
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
                name: "Adjax".to_string(),
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
                seed: derive_seed(master_seed, "Adjax", 1),
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

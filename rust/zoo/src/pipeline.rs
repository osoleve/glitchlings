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
    use super::{derive_seed, GlitchDescriptor, Pipeline};
    use crate::glitch_ops::{
        DeleteRandomWordsOp, GlitchOperation, OcrArtifactsOp, RedactWordsOp, ReduplicateWordsOp,
    };

    #[test]
    fn derive_seed_matches_python_reference() {
        assert_eq!(derive_seed(151, "Reduple", 0), 14619582442299654959);
        assert_eq!(derive_seed(151, "Rushmore", 1), 15756123308692553544);
    }

    #[test]
    fn pipeline_applies_operations_in_order() {
        let master_seed = 151i128;
        let descriptors = vec![
            GlitchDescriptor {
                name: "Reduple".to_string(),
                seed: derive_seed(master_seed, "Reduple", 0),
                operation: GlitchOperation::Reduplicate(ReduplicateWordsOp {
                    reduplication_rate: 1.0,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Redactyl".to_string(),
                seed: derive_seed(master_seed, "Redactyl", 1),
                operation: GlitchOperation::Redact(RedactWordsOp {
                    replacement_char: "█".to_string(),
                    redaction_rate: 0.5,
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
            name: "Reduple".to_string(),
            seed: derive_seed(master_seed, "Reduple", 0),
            operation: GlitchOperation::Reduplicate(ReduplicateWordsOp {
                reduplication_rate: 0.5,
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
                name: "Reduple".to_string(),
                seed: derive_seed(master_seed, "Reduple", 0),
                operation: GlitchOperation::Reduplicate(ReduplicateWordsOp {
                    reduplication_rate: 0.4,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Rushmore".to_string(),
                seed: derive_seed(master_seed, "Rushmore", 1),
                operation: GlitchOperation::Delete(DeleteRandomWordsOp {
                    max_deletion_rate: 0.3,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Redactyl".to_string(),
                seed: derive_seed(master_seed, "Redactyl", 2),
                operation: GlitchOperation::Redact(RedactWordsOp {
                    replacement_char: "█".to_string(),
                    redaction_rate: 0.6,
                    merge_adjacent: true,
                    unweighted: false,
                }),
            },
            GlitchDescriptor {
                name: "Scannequin".to_string(),
                seed: derive_seed(master_seed, "Scannequin", 3),
                operation: GlitchOperation::Ocr(OcrArtifactsOp { error_rate: 0.25 }),
            },
        ];
        let pipeline = Pipeline::new(master_seed, descriptors);
        let output = pipeline
            .run("Guard the vault at midnight")
            .expect("pipeline run succeeds");
        assert_eq!(output, "Guard the ██ at ██████████");
    }
}

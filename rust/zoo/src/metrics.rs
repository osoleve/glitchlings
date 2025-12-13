use std::borrow::Cow;
use std::cmp::max;
use std::collections::{HashMap, HashSet};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyString;
use rayon::prelude::*;

/// Extract strings from Python string objects without deep copying.
/// Returns Cow<str> which borrows when possible and owns when necessary.
fn extract_str_refs<'py>(tokens: &'py [Bound<'py, PyString>]) -> PyResult<Vec<Cow<'py, str>>> {
    tokens.iter().map(|s| s.to_cow()).collect()
}

/// Extract batch of string references from Python.
fn extract_batch_str_refs<'py>(
    batches: &'py [Vec<Bound<'py, PyString>>],
) -> PyResult<Vec<Vec<Cow<'py, str>>>> {
    batches
        .iter()
        .map(|tokens| extract_str_refs(tokens))
        .collect()
}

/// Extract strings as owned Strings for use outside GIL.
/// Use this when you need to release the GIL for parallel processing.
fn extract_owned_strings(tokens: &[Bound<'_, PyString>]) -> PyResult<Vec<String>> {
    tokens.iter().map(|s| s.extract::<String>()).collect()
}

/// Extract batch of owned strings for parallel processing outside GIL.
fn extract_batch_owned_strings(
    batches: &[Vec<Bound<'_, PyString>>],
) -> PyResult<Vec<Vec<String>>> {
    batches
        .iter()
        .map(|tokens| extract_owned_strings(tokens))
        .collect()
}

#[pyfunction]
pub fn jensen_shannon_divergence(
    _py: Python<'_>,
    input_tokens: Vec<Bound<'_, PyString>>,
    output_tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    let inputs = extract_str_refs(&input_tokens)?;
    let outputs = extract_str_refs(&output_tokens)?;
    Ok(compute_jsd(&inputs, &outputs))
}

#[pyfunction]
pub fn normalized_edit_distance(
    _py: Python<'_>,
    input_tokens: Vec<Bound<'_, PyString>>,
    output_tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    let inputs = extract_str_refs(&input_tokens)?;
    let outputs = extract_str_refs(&output_tokens)?;
    Ok(compute_normalized_edit_distance(&inputs, &outputs))
}

#[pyfunction]
pub fn subsequence_retention(
    _py: Python<'_>,
    input_tokens: Vec<Bound<'_, PyString>>,
    output_tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    let inputs = extract_str_refs(&input_tokens)?;
    let outputs = extract_str_refs(&output_tokens)?;
    Ok(compute_subsequence_retention(&inputs, &outputs))
}

#[pyfunction]
pub fn batch_jensen_shannon_divergence(
    py: Python<'_>,
    inputs: Vec<Vec<Bound<'_, PyString>>>,
    outputs: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    // Extract to owned strings while holding GIL
    let input_owned = extract_batch_owned_strings(&inputs)?;
    let output_owned = extract_batch_owned_strings(&outputs)?;

    // Release GIL and process in parallel
    Ok(py.allow_threads(|| {
        input_owned
            .par_iter()
            .zip(output_owned.par_iter())
            .map(|(input, output)| compute_jsd(input, output))
            .collect()
    }))
}

#[pyfunction]
pub fn batch_normalized_edit_distance(
    py: Python<'_>,
    inputs: Vec<Vec<Bound<'_, PyString>>>,
    outputs: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    // Extract to owned strings while holding GIL
    let input_owned = extract_batch_owned_strings(&inputs)?;
    let output_owned = extract_batch_owned_strings(&outputs)?;

    // Release GIL and process in parallel
    Ok(py.allow_threads(|| {
        input_owned
            .par_iter()
            .zip(output_owned.par_iter())
            .map(|(input, output)| compute_normalized_edit_distance(input, output))
            .collect()
    }))
}

#[pyfunction]
pub fn batch_subsequence_retention(
    py: Python<'_>,
    inputs: Vec<Vec<Bound<'_, PyString>>>,
    outputs: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    // Extract to owned strings while holding GIL
    let input_owned = extract_batch_owned_strings(&inputs)?;
    let output_owned = extract_batch_owned_strings(&outputs)?;

    // Release GIL and process in parallel
    Ok(py.allow_threads(|| {
        input_owned
            .par_iter()
            .zip(output_owned.par_iter())
            .map(|(input, output)| compute_subsequence_retention(input, output))
            .collect()
    }))
}

fn compute_jsd<S: AsRef<str>>(tokens1: &[S], tokens2: &[S]) -> f64 {
    if tokens1.is_empty() && tokens2.is_empty() {
        return 0.0;
    }

    let mut counts1: HashMap<&str, f64> = HashMap::new();
    let mut counts2: HashMap<&str, f64> = HashMap::new();

    for token in tokens1 {
        *counts1.entry(token.as_ref()).or_insert(0.0) += 1.0;
    }
    for token in tokens2 {
        *counts2.entry(token.as_ref()).or_insert(0.0) += 1.0;
    }

    let sum1: f64 = counts1.values().sum();
    let sum2: f64 = counts2.values().sum();

    let norm1 = if sum1 > 0.0 { sum1 } else { 1.0 };
    let norm2 = if sum2 > 0.0 { sum2 } else { 1.0 };

    let mut kl_pm = 0.0;
    for (token, count_p) in counts1.iter() {
        let p = count_p / norm1;
        let q = counts2.get(token).copied().unwrap_or(0.0) / norm2;
        let m = 0.5 * (p + q);

        if p > 0.0 {
            kl_pm += p * (p / m).log2();
        }
    }

    let mut kl_qm = 0.0;
    for (token, count_q) in counts2.iter() {
        let q = count_q / norm2;
        if q == 0.0 {
            continue;
        }
        let p = counts1.get(token).copied().unwrap_or(0.0) / norm1;
        let m = 0.5 * (p + q);
        kl_qm += q * (q / m).log2();
    }

    0.5 * (kl_pm + kl_qm)
}

fn compute_normalized_edit_distance<S: AsRef<str> + PartialEq>(tokens1: &[S], tokens2: &[S]) -> f64 {
    let n = tokens1.len();
    let m = tokens2.len();

    if n == 0 {
        return if m > 0 { 1.0 } else { 0.0 };
    }
    if m == 0 {
        return if n > 0 { 1.0 } else { 0.0 };
    }

    // Levenshtein distance
    let mut prev: Vec<usize> = (0..=m).collect();
    let mut curr: Vec<usize> = vec![0; m + 1];

    for (i, t1) in tokens1.iter().enumerate() {
        curr[0] = i + 1;
        for (j, t2) in tokens2.iter().enumerate() {
            let cost = if t1.as_ref() == t2.as_ref() { 0 } else { 1 };
            curr[j + 1] =
                std::cmp::min(std::cmp::min(curr[j] + 1, prev[j + 1] + 1), prev[j] + cost);
        }
        prev.copy_from_slice(&curr);
    }

    let dist = prev[m] as f64;
    dist / (max(n, m) as f64)
}

fn compute_subsequence_retention<S: AsRef<str>>(tokens1: &[S], tokens2: &[S]) -> f64 {
    let n = tokens1.len();
    let m = tokens2.len();

    if n == 0 {
        return 1.0;
    }

    // LCS
    // Optimization: O(min(N, M)) space.

    // Ensure s2 is the smaller one for space optimization
    let (s1, s2) = if n < m {
        (tokens2, tokens1)
    } else {
        (tokens1, tokens2)
    };
    let len2 = s2.len();

    let mut prev = vec![0; len2 + 1];
    let mut curr = vec![0; len2 + 1];

    for t1 in s1 {
        for (j, t2) in s2.iter().enumerate() {
            if t1.as_ref() == t2.as_ref() {
                curr[j + 1] = prev[j] + 1;
            } else {
                curr[j + 1] = max(prev[j + 1], curr[j]);
            }
        }
        prev.copy_from_slice(&curr);
    }

    let lcs_len = prev[len2] as f64;

    // Retention is LCS / length of original input (tokens1, which is n)
    lcs_len / (n as f64)
}

fn guard_equal_batches(inputs: usize, outputs: usize) -> PyResult<()> {
    if inputs != outputs {
        return Err(PyValueError::new_err(format!(
            "batch metric inputs and outputs must have the same length (got {inputs} and {outputs})"
        )));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Entropy Delta
// ---------------------------------------------------------------------------

#[pyfunction]
pub fn entropy_delta(
    _py: Python<'_>,
    input_tokens: Vec<Bound<'_, PyString>>,
    output_tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    let inputs = extract_str_refs(&input_tokens)?;
    let outputs = extract_str_refs(&output_tokens)?;
    Ok(compute_entropy_delta(&inputs, &outputs))
}

#[pyfunction]
pub fn batch_entropy_delta(
    py: Python<'_>,
    inputs: Vec<Vec<Bound<'_, PyString>>>,
    outputs: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    // Extract to owned strings while holding GIL
    let input_owned = extract_batch_owned_strings(&inputs)?;
    let output_owned = extract_batch_owned_strings(&outputs)?;

    // Release GIL and process in parallel
    Ok(py.allow_threads(|| {
        input_owned
            .par_iter()
            .zip(output_owned.par_iter())
            .map(|(input, output)| compute_entropy_delta(input, output))
            .collect()
    }))
}

fn shannon_entropy<S: AsRef<str>>(tokens: &[S]) -> f64 {
    if tokens.is_empty() {
        return 0.0;
    }

    let mut counts: HashMap<&str, usize> = HashMap::new();
    for token in tokens {
        *counts.entry(token.as_ref()).or_insert(0) += 1;
    }

    let total = tokens.len() as f64;
    let mut entropy = 0.0;
    for &count in counts.values() {
        if count > 0 {
            let p = count as f64 / total;
            entropy -= p * p.log2();
        }
    }
    entropy
}

fn compute_entropy_delta<S: AsRef<str>>(tokens1: &[S], tokens2: &[S]) -> f64 {
    let h_orig = shannon_entropy(tokens1);
    let h_corr = shannon_entropy(tokens2);
    let delta = h_corr - h_orig;

    // Collect combined vocabulary
    let mut vocab: HashSet<&str> = HashSet::new();
    for token in tokens1 {
        vocab.insert(token.as_ref());
    }
    for token in tokens2 {
        vocab.insert(token.as_ref());
    }

    if vocab.is_empty() {
        return 0.0;
    }

    let max_entropy = if vocab.len() > 1 {
        (vocab.len() as f64).log2()
    } else {
        1.0
    };

    if max_entropy > 0.0 {
        delta / max_entropy
    } else {
        0.0
    }
}

// ---------------------------------------------------------------------------
// Merge-Split Index
// ---------------------------------------------------------------------------

#[pyfunction]
pub fn merge_split_index(
    _py: Python<'_>,
    input_tokens: Vec<Bound<'_, PyString>>,
    output_tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    let inputs = extract_str_refs(&input_tokens)?;
    let outputs = extract_str_refs(&output_tokens)?;
    Ok(compute_merge_split_index(&inputs, &outputs))
}

#[pyfunction]
pub fn batch_merge_split_index(
    py: Python<'_>,
    inputs: Vec<Vec<Bound<'_, PyString>>>,
    outputs: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    // Extract to owned strings while holding GIL
    let input_owned = extract_batch_owned_strings(&inputs)?;
    let output_owned = extract_batch_owned_strings(&outputs)?;

    // Release GIL and process in parallel
    Ok(py.allow_threads(|| {
        input_owned
            .par_iter()
            .zip(output_owned.par_iter())
            .map(|(input, output)| compute_merge_split_index(input, output))
            .collect()
    }))
}

fn lcs_length<S: AsRef<str>>(a: &[S], b: &[S]) -> usize {
    let m = a.len();
    let n = b.len();

    if m == 0 || n == 0 {
        return 0;
    }

    // Space-optimized LCS using two rows
    let mut prev = vec![0usize; n + 1];
    let mut curr = vec![0usize; n + 1];

    for i in 1..=m {
        for j in 1..=n {
            if a[i - 1].as_ref() == b[j - 1].as_ref() {
                curr[j] = prev[j - 1] + 1;
            } else {
                curr[j] = max(prev[j], curr[j - 1]);
            }
        }
        std::mem::swap(&mut prev, &mut curr);
        curr.fill(0);
    }

    prev[n]
}

fn compute_merge_split_index<S: AsRef<str>>(tokens1: &[S], tokens2: &[S]) -> f64 {
    let m = tokens1.len();
    let n = tokens2.len();

    if m == 0 && n == 0 {
        return 0.0;
    }
    if m == 0 || n == 0 {
        return 1.0; // Complete transformation
    }

    // Find preserved tokens via LCS
    let lcs_len = lcs_length(tokens1, tokens2);

    // Tokens that changed: those not in LCS
    let orig_changed = m - lcs_len; // tokens that were removed/split
    let corr_changed = n - lcs_len; // tokens that were added/merged

    // Merge/split events are indicated by the DIFFERENCE in changed tokens:
    // - If orig_changed > corr_changed: merges occurred (k→1)
    // - If corr_changed > orig_changed: splits occurred (1→k)
    // - If orig_changed == corr_changed: substitutions only (no restructuring)
    let merge_split_events = if orig_changed > corr_changed {
        orig_changed - corr_changed
    } else {
        corr_changed - orig_changed
    };

    let max_len = max(m, n);
    merge_split_events as f64 / max_len as f64
}

// ---------------------------------------------------------------------------
// Tokenizer Metrics (for analyzing tokenizer behavior)
// ---------------------------------------------------------------------------

/// Compute compression ratio: bytes per token.
/// Lower values indicate more compact encoding.
#[pyfunction]
pub fn compression_ratio(
    _py: Python<'_>,
    text: &str,
    tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    if text.is_empty() {
        return Ok(0.0);
    }

    let token_count = tokens.len();
    if token_count == 0 {
        return Ok(f64::INFINITY);
    }

    let byte_count = text.len(); // UTF-8 byte count
    Ok(byte_count as f64 / token_count as f64)
}

/// Compute batch compression ratios.
#[pyfunction]
pub fn batch_compression_ratio(
    _py: Python<'_>,
    texts: Vec<String>,
    token_batches: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(texts.len(), token_batches.len())?;

    Ok(texts
        .iter()
        .zip(token_batches.iter())
        .map(|(text, tokens)| {
            if text.is_empty() {
                0.0
            } else if tokens.is_empty() {
                f64::INFINITY
            } else {
                text.len() as f64 / tokens.len() as f64
            }
        })
        .collect())
}

/// Compute characters per token ratio.
/// Higher values mean fewer tokens needed.
#[pyfunction]
pub fn characters_per_token(
    _py: Python<'_>,
    text: &str,
    tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    if text.is_empty() {
        return Ok(0.0);
    }

    let token_count = tokens.len();
    if token_count == 0 {
        return Ok(f64::INFINITY);
    }

    let char_count = text.chars().count();
    Ok(char_count as f64 / token_count as f64)
}

/// Compute batch characters per token ratios.
#[pyfunction]
pub fn batch_characters_per_token(
    _py: Python<'_>,
    texts: Vec<String>,
    token_batches: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(texts.len(), token_batches.len())?;

    Ok(texts
        .iter()
        .zip(token_batches.iter())
        .map(|(text, tokens)| {
            if text.is_empty() {
                0.0
            } else if tokens.is_empty() {
                f64::INFINITY
            } else {
                text.chars().count() as f64 / tokens.len() as f64
            }
        })
        .collect())
}

/// Compute Shannon entropy of token distribution.
/// Higher entropy means more uniform token usage (less repetition).
#[pyfunction]
pub fn token_entropy(
    _py: Python<'_>,
    tokens: Vec<Bound<'_, PyString>>,
) -> PyResult<f64> {
    let token_refs = extract_str_refs(&tokens)?;
    Ok(shannon_entropy(&token_refs))
}

/// Compute batch token entropies.
#[pyfunction]
pub fn batch_token_entropy(
    py: Python<'_>,
    token_batches: Vec<Vec<Bound<'_, PyString>>>,
) -> PyResult<Vec<f64>> {
    // Extract to owned strings while holding GIL
    let batch_owned = extract_batch_owned_strings(&token_batches)?;

    // Release GIL and process in parallel
    Ok(py.allow_threads(|| {
        batch_owned
            .par_iter()
            .map(|tokens| shannon_entropy(tokens))
            .collect()
    }))
}

/// Result type for vocabulary utilization analysis.
#[derive(Clone)]
pub struct VocabUtilization {
    unique_ratio: f64,
    repetition_rate: f64,
    max_id: f64,
    id_spread: f64,
}

impl<'py> pyo3::IntoPyObject<'py> for VocabUtilization {
    type Target = pyo3::types::PyDict;
    type Output = Bound<'py, Self::Target>;
    type Error = pyo3::PyErr;

    fn into_pyobject(self, py: Python<'py>) -> Result<Self::Output, Self::Error> {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("unique_ratio", self.unique_ratio)?;
        dict.set_item("repetition_rate", self.repetition_rate)?;
        dict.set_item("max_id", self.max_id)?;
        dict.set_item("id_spread", self.id_spread)?;
        Ok(dict)
    }
}

/// Analyze vocabulary usage patterns.
/// Returns a dictionary with:
/// - unique_ratio: fraction of tokens that are unique
/// - repetition_rate: 1 - unique_ratio
/// - max_id: highest token ID used
/// - id_spread: standard deviation of IDs
#[pyfunction]
pub fn vocabulary_utilization(
    _py: Python<'_>,
    tokens: Vec<Bound<'_, PyString>>,
    token_ids: Vec<i64>,
) -> PyResult<VocabUtilization> {
    if tokens.is_empty() {
        return Ok(VocabUtilization {
            unique_ratio: 0.0,
            repetition_rate: 0.0,
            max_id: 0.0,
            id_spread: 0.0,
        });
    }

    // Count unique tokens
    let token_refs = extract_str_refs(&tokens)?;
    let unique_set: HashSet<&str> = token_refs.iter().map(|s| s.as_ref()).collect();
    let unique_count = unique_set.len();
    let unique_ratio = unique_count as f64 / tokens.len() as f64;

    // ID statistics
    let max_id = *token_ids.iter().max().unwrap_or(&0);
    let mean_id: f64 = token_ids.iter().map(|&id| id as f64).sum::<f64>() / token_ids.len() as f64;
    let variance: f64 = token_ids
        .iter()
        .map(|&id| {
            let diff = id as f64 - mean_id;
            diff * diff
        })
        .sum::<f64>()
        / token_ids.len() as f64;
    let id_spread = variance.sqrt();

    Ok(VocabUtilization {
        unique_ratio,
        repetition_rate: 1.0 - unique_ratio,
        max_id: max_id as f64,
        id_spread,
    })
}

/// Compute batch vocabulary utilization.
#[pyfunction]
pub fn batch_vocabulary_utilization(
    _py: Python<'_>,
    token_batches: Vec<Vec<Bound<'_, PyString>>>,
    token_id_batches: Vec<Vec<i64>>,
) -> PyResult<Vec<VocabUtilization>> {
    guard_equal_batches(token_batches.len(), token_id_batches.len())?;

    let mut results = Vec::with_capacity(token_batches.len());

    for (tokens, token_ids) in token_batches.iter().zip(token_id_batches.iter()) {
        if tokens.is_empty() {
            results.push(VocabUtilization {
                unique_ratio: 0.0,
                repetition_rate: 0.0,
                max_id: 0.0,
                id_spread: 0.0,
            });
            continue;
        }

        // Count unique tokens
        let token_refs = extract_str_refs(tokens)?;
        let unique_set: HashSet<&str> = token_refs.iter().map(|s| s.as_ref()).collect();
        let unique_count = unique_set.len();
        let unique_ratio = unique_count as f64 / tokens.len() as f64;

        // ID statistics
        let max_id = *token_ids.iter().max().unwrap_or(&0);
        let mean_id: f64 =
            token_ids.iter().map(|&id| id as f64).sum::<f64>() / token_ids.len() as f64;
        let variance: f64 = token_ids
            .iter()
            .map(|&id| {
                let diff = id as f64 - mean_id;
                diff * diff
            })
            .sum::<f64>()
            / token_ids.len() as f64;
        let id_spread = variance.sqrt();

        results.push(VocabUtilization {
            unique_ratio,
            repetition_rate: 1.0 - unique_ratio,
            max_id: max_id as f64,
            id_spread,
        });
    }

    Ok(results)
}

/// Default unknown token markers.
const DEFAULT_UNKNOWN_MARKERS: &[&str] = &["[UNK]", "<unk>", "�", "\u{FFFD}"];

/// Compute unknown token rate.
/// Fraction of tokens that appear to be unknown/fallback tokens.
#[pyfunction]
#[pyo3(signature = (tokens, unknown_markers=None))]
pub fn unknown_token_rate(
    _py: Python<'_>,
    tokens: Vec<Bound<'_, PyString>>,
    unknown_markers: Option<Vec<String>>,
) -> PyResult<f64> {
    if tokens.is_empty() {
        return Ok(0.0);
    }

    let token_refs = extract_str_refs(&tokens)?;

    // Build marker set from provided markers or defaults
    let marker_set: HashSet<&str> = match &unknown_markers {
        Some(markers) => markers.iter().map(|s| s.as_str()).collect(),
        None => DEFAULT_UNKNOWN_MARKERS.iter().copied().collect(),
    };

    let unknown_count = token_refs
        .iter()
        .filter(|token| {
            let t = token.as_ref();
            marker_set.contains(t) || t.starts_with("<0x")
        })
        .count();

    Ok(unknown_count as f64 / token_refs.len() as f64)
}

/// Compute batch unknown token rates.
#[pyfunction]
#[pyo3(signature = (token_batches, unknown_markers=None))]
pub fn batch_unknown_token_rate(
    _py: Python<'_>,
    token_batches: Vec<Vec<Bound<'_, PyString>>>,
    unknown_markers: Option<Vec<String>>,
) -> PyResult<Vec<f64>> {
    // Build marker set from provided markers or defaults
    let marker_set: HashSet<&str> = match &unknown_markers {
        Some(markers) => markers.iter().map(|s| s.as_str()).collect(),
        None => DEFAULT_UNKNOWN_MARKERS.iter().copied().collect(),
    };

    let batch_refs = extract_batch_str_refs(&token_batches)?;

    Ok(batch_refs
        .iter()
        .map(|token_refs| {
            if token_refs.is_empty() {
                0.0
            } else {
                let unknown_count = token_refs
                    .iter()
                    .filter(|token| {
                        let t = token.as_ref();
                        marker_set.contains(t) || t.starts_with("<0x")
                    })
                    .count();
                unknown_count as f64 / token_refs.len() as f64
            }
        })
        .collect())
}

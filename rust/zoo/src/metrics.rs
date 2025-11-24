use std::cmp::max;
use std::collections::HashMap;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyfunction]
pub fn jensen_shannon_divergence(
    py: Python<'_>,
    input_tokens: Vec<String>,
    output_tokens: Vec<String>,
) -> PyResult<f64> {
    Ok(py.allow_threads(|| compute_jsd(&input_tokens, &output_tokens)))
}

#[pyfunction]
pub fn normalized_edit_distance(
    py: Python<'_>,
    input_tokens: Vec<String>,
    output_tokens: Vec<String>,
) -> PyResult<f64> {
    Ok(py.allow_threads(|| compute_normalized_edit_distance(&input_tokens, &output_tokens)))
}

#[pyfunction]
pub fn subsequence_retention(
    py: Python<'_>,
    input_tokens: Vec<String>,
    output_tokens: Vec<String>,
) -> PyResult<f64> {
    Ok(py.allow_threads(|| compute_subsequence_retention(&input_tokens, &output_tokens)))
}

#[pyfunction]
pub fn batch_jensen_shannon_divergence(
    py: Python<'_>,
    inputs: Vec<Vec<String>>,
    outputs: Vec<Vec<String>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    Ok(py.allow_threads(|| {
        inputs
            .iter()
            .zip(outputs.iter())
            .map(|(input, output)| compute_jsd(input, output))
            .collect()
    }))
}

#[pyfunction]
pub fn batch_normalized_edit_distance(
    py: Python<'_>,
    inputs: Vec<Vec<String>>,
    outputs: Vec<Vec<String>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    Ok(py.allow_threads(|| {
        inputs
            .iter()
            .zip(outputs.iter())
            .map(|(input, output)| compute_normalized_edit_distance(input, output))
            .collect()
    }))
}

#[pyfunction]
pub fn batch_subsequence_retention(
    py: Python<'_>,
    inputs: Vec<Vec<String>>,
    outputs: Vec<Vec<String>>,
) -> PyResult<Vec<f64>> {
    guard_equal_batches(inputs.len(), outputs.len())?;

    Ok(py.allow_threads(|| {
        inputs
            .iter()
            .zip(outputs.iter())
            .map(|(input, output)| compute_subsequence_retention(input, output))
            .collect()
    }))
}

fn compute_jsd(tokens1: &[String], tokens2: &[String]) -> f64 {
    if tokens1.is_empty() && tokens2.is_empty() {
        return 0.0;
    }

    let mut counts1: HashMap<&str, f64> = HashMap::new();
    let mut counts2: HashMap<&str, f64> = HashMap::new();

    for token in tokens1 {
        *counts1.entry(token.as_str()).or_insert(0.0) += 1.0;
    }
    for token in tokens2 {
        *counts2.entry(token.as_str()).or_insert(0.0) += 1.0;
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

fn compute_normalized_edit_distance(tokens1: &[String], tokens2: &[String]) -> f64 {
    let n = tokens1.len();
    let m = tokens2.len();

    if n == 0 { return if m > 0 { 1.0 } else { 0.0 }; }
    if m == 0 { return if n > 0 { 1.0 } else { 0.0 }; }

    // Levenshtein distance
    let mut prev: Vec<usize> = (0..=m).collect();
    let mut curr: Vec<usize> = vec![0; m + 1];

    for (i, t1) in tokens1.iter().enumerate() {
        curr[0] = i + 1;
        for (j, t2) in tokens2.iter().enumerate() {
            let cost = if t1 == t2 { 0 } else { 1 };
            curr[j + 1] = std::cmp::min(
                std::cmp::min(curr[j] + 1, prev[j + 1] + 1),
                prev[j] + cost
            );
        }
        prev.copy_from_slice(&curr);
    }

    let dist = prev[m] as f64;
    dist / (max(n, m) as f64)
}

fn compute_subsequence_retention(tokens1: &[String], tokens2: &[String]) -> f64 {
    let n = tokens1.len();
    let m = tokens2.len();

    if n == 0 { return 1.0; }

    // LCS
    // Optimization: O(min(N, M)) space.

    // Ensure s2 is the smaller one for space optimization
    let (s1, s2) = if n < m { (tokens2, tokens1) } else { (tokens1, tokens2) };
    let len2 = s2.len();

    let mut prev = vec![0; len2 + 1];
    let mut curr = vec![0; len2 + 1];

    for t1 in s1 {
        for (j, t2) in s2.iter().enumerate() {
            if t1 == t2 {
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

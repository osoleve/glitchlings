use crate::resources::{split_affixes, split_with_separators};
use crate::rng::{DeterministicRng, RngError};
use blake2::{Blake2s256, Digest};
use once_cell::sync::Lazy;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::PyErr;
use std::collections::HashMap;

static RAW_DEFAULT_VECTOR_CACHE: &str =
    include_str!(concat!(env!("OUT_DIR"), "/default_vector_cache.json"));

static DEFAULT_VECTOR_CACHE: Lazy<HashMap<String, Vec<String>>> = Lazy::new(|| {
    serde_json::from_str(RAW_DEFAULT_VECTOR_CACHE)
        .expect("default vector cache should be valid JSON")
});

#[derive(Debug)]
struct Candidate {
    token_index: usize,
    prefix: String,
    suffix: String,
    synonyms: Vec<String>,
}

fn rng_error(err: RngError) -> PyErr {
    PyValueError::new_err(err.to_string())
}

fn deterministic_sample(
    values: &[String],
    limit: usize,
    word: &str,
    pos: Option<&str>,
    base_seed: Option<&str>,
) -> Vec<String> {
    if limit == 0 {
        return Vec::new();
    }

    if values.len() <= limit {
        return values.to_vec();
    }

    let mut hasher = Blake2s256::new();
    hasher.update(word.to_lowercase());
    if let Some(tag) = pos {
        hasher.update(tag.to_lowercase());
    }
    let seed_repr = base_seed.unwrap_or("None");
    hasher.update(seed_repr.as_bytes());
    let digest = hasher.finalize();
    let mut seed_bytes = [0u8; 8];
    seed_bytes.copy_from_slice(&digest[..8]);
    let derived_seed = u64::from_be_bytes(seed_bytes);

    let mut rng = DeterministicRng::new(derived_seed);
    let mut indices = match rng.sample_indices(values.len(), limit) {
        Ok(indices) => indices,
        Err(_) => return values[..limit].to_vec(),
    };
    indices.sort_unstable();
    indices
        .into_iter()
        .map(|index| values[index].clone())
        .collect()
}

fn cache_synonyms_for(word: &str, pos: Option<&str>, base_seed: Option<&str>) -> Vec<String> {
    let lookup = word.to_lowercase();
    let Some(values) = DEFAULT_VECTOR_CACHE.get(&lookup) else {
        return Vec::new();
    };

    deterministic_sample(values.as_slice(), 5, word, pos, base_seed)
}

fn python_supports_pos(
    py: Python<'_>,
    lexicon: &Bound<'_, PyAny>,
    pos: Option<&str>,
) -> PyResult<bool> {
    if let Some(tag) = pos {
        lexicon.call_method1("supports_pos", (tag,))?.extract()
    } else {
        lexicon
            .call_method1("supports_pos", (py.None(),))?
            .extract()
    }
}

fn python_synonyms_for(
    py: Python<'_>,
    lexicon: &Bound<'_, PyAny>,
    word: &str,
    pos: Option<&str>,
) -> PyResult<Vec<String>> {
    let kwargs = PyDict::new(py);
    match pos {
        Some(tag) => kwargs.set_item("pos", tag)?,
        None => kwargs.set_item("pos", py.None())?,
    }
    let synonyms = lexicon.call_method("get_synonyms", (word,), Some(&kwargs))?;
    synonyms.extract()
}

fn collect_synonyms(
    py: Python<'_>,
    lexicon: Option<&Bound<'_, PyAny>>,
    word: &str,
    part_of_speech: &[String],
    base_seed: Option<&str>,
) -> PyResult<Vec<String>> {
    if let Some(python_lexicon) = lexicon {
        let mut chosen: Vec<String> = Vec::new();
        for tag in part_of_speech {
            if !python_supports_pos(py, python_lexicon, Some(tag))? {
                continue;
            }
            let synonyms = python_synonyms_for(py, python_lexicon, word, Some(tag))?;
            if !synonyms.is_empty() {
                chosen = synonyms;
                return Ok(chosen);
            }
        }

        if python_supports_pos(py, python_lexicon, None)? {
            chosen = python_synonyms_for(py, python_lexicon, word, None)?;
        }
        return Ok(chosen);
    }

    for tag in part_of_speech {
        let synonyms = cache_synonyms_for(word, Some(tag), base_seed);
        if !synonyms.is_empty() {
            return Ok(synonyms);
        }
    }

    Ok(cache_synonyms_for(word, None, base_seed))
}

#[pyfunction(signature = (text, rate, part_of_speech, seed, lexicon=None, lexicon_seed=None))]
pub(crate) fn substitute_random_synonyms(
    py: Python<'_>,
    text: &str,
    rate: f64,
    part_of_speech: Vec<String>,
    seed: u64,
    lexicon: Option<Bound<'_, PyAny>>,
    lexicon_seed: Option<String>,
) -> PyResult<String> {
    if text.is_empty() {
        return Ok(String::new());
    }

    if part_of_speech.is_empty() {
        return Ok(text.to_string());
    }

    let mut tokens = split_with_separators(text);
    let base_seed = lexicon_seed.as_deref();

    let mut candidates: Vec<Candidate> = Vec::new();
    for (index, token) in tokens.iter().enumerate() {
        if index % 2 != 0 {
            continue;
        }
        if token.is_empty() || token.chars().all(char::is_whitespace) {
            continue;
        }

        let (prefix, core, suffix) = split_affixes(token);
        if core.is_empty() {
            continue;
        }

        let synonyms = collect_synonyms(py, lexicon.as_ref(), &core, &part_of_speech, base_seed)?;
        if synonyms.is_empty() {
            continue;
        }

        candidates.push(Candidate {
            token_index: index,
            prefix,
            suffix,
            synonyms,
        });
    }

    if candidates.is_empty() {
        return Ok(text.to_string());
    }

    let clamped_rate = rate.max(0.0);
    if clamped_rate == 0.0 {
        return Ok(text.to_string());
    }

    let population = candidates.len();
    let effective_fraction = clamped_rate.min(1.0);
    let expected = (population as f64) * effective_fraction;
    let mut max_replacements = expected.floor() as usize;
    let remainder = expected - (max_replacements as f64);

    let mut rng = DeterministicRng::new(seed);
    if clamped_rate >= 1.0 {
        max_replacements = population;
    } else {
        if remainder > 0.0 && rng.random() < remainder {
            max_replacements += 1;
        }
        if clamped_rate > 0.0 && max_replacements == 0 && population > 0 {
            max_replacements = 1;
        }
    }

    max_replacements = max_replacements.min(population);
    if max_replacements == 0 {
        return Ok(text.to_string());
    }

    let mut selected = rng
        .sample_indices(population, max_replacements)
        .map_err(rng_error)?
        .into_iter()
        .map(|candidate_index| {
            let token_index = candidates[candidate_index].token_index;
            (token_index, candidate_index)
        })
        .collect::<Vec<_>>();

    selected.sort_by_key(|(token_index, _)| *token_index);

    for (_, candidate_index) in selected {
        let candidate = &candidates[candidate_index];
        let choice_index = rng
            .rand_index(candidate.synonyms.len())
            .map_err(rng_error)?;
        let replacement = &candidate.synonyms[choice_index];
        tokens[candidate.token_index] =
            format!("{}{}{}", candidate.prefix, replacement, candidate.suffix);
    }

    Ok(tokens.concat())
}

use once_cell::sync::Lazy;
use std::collections::{HashMap, HashSet};

use crate::operations::{TextOperation, OperationError, OperationRng};
use crate::resources::{wherewolf_homophone_sets, is_whitespace_only, split_affixes};
use crate::text_buffer::TextBuffer;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HomophoneWeighting {
    Flat,
}

impl HomophoneWeighting {
    pub fn try_from_str(value: &str) -> Option<Self> {
        match value {
            "flat" => Some(HomophoneWeighting::Flat),
            _ => None,
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            HomophoneWeighting::Flat => "flat",
        }
    }
}

#[derive(Debug, Clone)]
pub struct HomophoneOp {
    pub rate: f64,
    pub weighting: HomophoneWeighting,
}

static HOMOPHONE_LOOKUP: Lazy<HashMap<String, Vec<String>>> = Lazy::new(|| {
    let mut mapping: HashMap<String, Vec<String>> = HashMap::new();

    for group in wherewolf_homophone_sets() {
        let mut seen: HashSet<String> = HashSet::new();
        let mut normalised: Vec<String> = Vec::new();
        for word in group {
            let lowered = word.to_lowercase();
            if seen.insert(lowered.clone()) {
                normalised.push(lowered);
            }
        }

        if normalised.len() < 2 {
            continue;
        }

        for word in &normalised {
            mapping.insert(word.clone(), normalised.clone());
        }
    }

    mapping
});

fn apply_casing(template: &str, candidate: &str) -> String {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum CasingPattern {
        Upper,
        Lower,
        Capitalised,
        Other,
    }

    fn detect_pattern(value: &str) -> CasingPattern {
        let mut has_cased = false;
        let mut upper = 0usize;
        let mut lower = 0usize;
        for ch in value.chars() {
            if ch.is_uppercase() {
                has_cased = true;
                upper += 1;
            } else if ch.is_lowercase() {
                has_cased = true;
                lower += 1;
            }
        }

        if !has_cased {
            return CasingPattern::Other;
        }
        if lower == 0 {
            return CasingPattern::Upper;
        }
        if upper == 0 {
            return CasingPattern::Lower;
        }

        let mut chars = value.chars();
        if let Some(first) = chars.next() {
            if first.is_uppercase() && chars.all(|ch| ch.is_lowercase()) {
                return CasingPattern::Capitalised;
            }
        }

        CasingPattern::Other
    }

    match detect_pattern(template) {
        CasingPattern::Upper => candidate.to_uppercase(),
        CasingPattern::Lower => candidate.to_string(),
        CasingPattern::Capitalised => {
            let mut chars = candidate.chars();
            if let Some(first) = chars.next() {
                let mut result = String::new();
                result.extend(first.to_uppercase());
                for ch in chars {
                    result.extend(ch.to_lowercase());
                }
                result
            } else {
                String::new()
            }
        }
        CasingPattern::Other => candidate.to_string(),
    }
}

fn choose_alternative(
    rng: &mut dyn OperationRng,
    group: &[String],
    source: &str,
    weighting: HomophoneWeighting,
) -> Result<Option<String>, OperationError> {
    let lowered = source.to_lowercase();
    let candidates: Vec<&String> = group
        .iter()
        .filter(|candidate| *candidate != &lowered)
        .collect();

    if candidates.is_empty() {
        return Ok(None);
    }

    match weighting {
        HomophoneWeighting::Flat => {
            let index = rng.rand_index(candidates.len())?;
            Ok(Some(candidates[index].clone()))
        }
    }
}

impl TextOperation for HomophoneOp {
    fn apply(&self, buffer: &mut TextBuffer, rng: &mut dyn OperationRng) -> Result<(), OperationError> {
        if buffer.word_count() == 0 {
            return Ok(());
        }

        if self.rate.is_nan() {
            return Ok(());
        }

        let clamped_rate = self.rate.clamp(0.0, 1.0);
        if clamped_rate <= f64::EPSILON {
            return Ok(());
        }

        // Collect all replacements first to avoid index shifting during mutation
        let mut replacements: Vec<(usize, String)> = Vec::new();

        for idx in 0..buffer.word_count() {
            let segment = match buffer.word_segment(idx) {
                Some(seg) => seg,
                None => continue,
            };

            let token = segment.text();
            if token.is_empty() || is_whitespace_only(token) {
                continue;
            }

            let (prefix, core, suffix) = split_affixes(token);
            if core.is_empty() {
                continue;
            }

            let lowered = core.to_lowercase();
            let group = match HOMOPHONE_LOOKUP.get(&lowered) {
                Some(group) => group,
                None => continue,
            };

            if rng.random()? >= clamped_rate {
                continue;
            }

            let replacement_core = match choose_alternative(rng, group, &core, self.weighting)? {
                Some(value) => apply_casing(&core, &value),
                None => continue,
            };

            let replacement = format!("{prefix}{replacement_core}{suffix}");
            replacements.push((idx, replacement));
        }

        // Apply all replacements using bulk update
        if !replacements.is_empty() {
            buffer.replace_words_bulk(replacements.into_iter())?;
        }

        buffer.reindex_if_needed();
        Ok(())
    }
}

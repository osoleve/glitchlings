use rand::rngs::SmallRng;
use rand::seq::{index, SliceRandom};
use rand::{Rng, SeedableRng};
use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum RngError {
    EmptyRange(&'static str),
    SampleSizeTooLarge { requested: usize, population: usize },
}

impl fmt::Display for RngError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyRange(context) => write!(f, "cannot sample from empty range in {context}"),
            Self::SampleSizeTooLarge {
                requested,
                population,
            } => write!(
                f,
                "requested sample of {requested} from population of {population}"
            ),
        }
    }
}

impl std::error::Error for RngError {}

#[derive(Clone)]
pub struct DeterministicRng {
    inner: SmallRng,
}

impl DeterministicRng {
    pub fn new(seed: u64) -> Self {
        Self {
            inner: SmallRng::seed_from_u64(seed),
        }
    }

    pub fn random(&mut self) -> f64 {
        self.inner.gen::<f64>()
    }

    pub fn rand_index(&mut self, upper: usize) -> Result<usize, RngError> {
        if upper == 0 {
            return Err(RngError::EmptyRange("rand_index"));
        }
        Ok(self.inner.gen_range(0..upper))
    }

    pub fn sample_indices(&mut self, population: usize, k: usize) -> Result<Vec<usize>, RngError> {
        if k > population {
            return Err(RngError::SampleSizeTooLarge {
                requested: k,
                population,
            });
        }
        let sample = index::sample(&mut self.inner, population, k);
        Ok(sample.into_iter().collect())
    }

    pub fn sample<T: Clone>(&mut self, population: &[T], k: usize) -> Result<Vec<T>, RngError> {
        if k > population.len() {
            return Err(RngError::SampleSizeTooLarge {
                requested: k,
                population: population.len(),
            });
        }
        Ok(population
            .choose_multiple(&mut self.inner, k)
            .cloned()
            .collect())
    }
}

#[cfg(test)]
mod tests {
    use super::DeterministicRng;

    #[test]
    fn random_is_deterministic_for_known_seed() {
        let mut rng = DeterministicRng::new(151);
        let expected = [
            0.0223485004498145,
            0.6717816014265233,
            0.1281738842609825,
            0.4433510526041998,
            0.1952597232845318,
        ];
        for value in expected {
            let actual = rng.random();
            assert!(
                (actual - value).abs() < 1e-15,
                "expected {value}, got {actual}"
            );
        }
    }

    #[test]
    fn sample_indices_respects_population_bounds() {
        let mut rng = DeterministicRng::new(42);
        let actual = rng.sample_indices(10, 4).unwrap();
        assert_eq!(actual.len(), 4);
        assert!(actual.iter().all(|value| *value < 10));
        let mut deduped = actual.clone();
        deduped.sort_unstable();
        deduped.dedup();
        assert_eq!(deduped.len(), actual.len(), "indices must be unique");
    }

    #[test]
    fn sample_respects_population_bounds() {
        let mut rng = DeterministicRng::new(7);
        let population: Vec<_> = (0..20).collect();
        let actual = rng.sample(&population, 5).unwrap();
        assert_eq!(actual.len(), 5);
        assert!(actual.into_iter().all(|value| population.contains(&value)));
    }
}

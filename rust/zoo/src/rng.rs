use rand::RngCore;
use rand::SeedableRng;
use std::collections::HashSet;
use std::fmt;

const STATE_SIZE: usize = 624;
const M: usize = 397;
const MATRIX_A: u32 = 0x9908B0DF;
const UPPER_MASK: u32 = 0x8000_0000;
const LOWER_MASK: u32 = 0x7FFF_FFFF;

#[derive(Debug, PartialEq, Eq)]
pub enum PyRngError {
    EmptyRange(&'static str),
    StepZero,
    MissingStop,
    UnsupportedBits(u32),
    RangeTooLarge,
}

impl fmt::Display for PyRngError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyRange(context) => write!(f, "empty range in {context}"),
            Self::StepZero => write!(f, "zero step for randrange()"),
            Self::MissingStop => write!(f, "missing a non-None stop argument"),
            Self::UnsupportedBits(bits) => write!(f, "unsupported bit request: {bits}"),
            Self::RangeTooLarge => write!(f, "range is too large to sample"),
        }
    }
}

impl std::error::Error for PyRngError {}

#[derive(Clone)]
pub struct PyRng {
    state: [u32; STATE_SIZE],
    index: usize,
}

impl PyRng {
    pub fn new(seed: u64) -> Self {
        let mut rng = Self {
            state: [0; STATE_SIZE],
            index: STATE_SIZE,
        };
        rng.seed(seed);
        rng
    }

    pub fn seed(&mut self, seed: u64) {
        let mut key = if seed == 0 {
            Vec::from([0u32])
        } else {
            Vec::new()
        };
        if seed != 0 {
            let mut value = seed;
            while value > 0 {
                key.push((value & 0xFFFF_FFFF) as u32);
                value >>= 32;
            }
        }
        self.init_by_array(&key);
    }

    fn init_by_array(&mut self, key: &[u32]) {
        self.state[0] = 19650218;
        for i in 1..STATE_SIZE {
            let prev = self.state[i - 1];
            self.state[i] = 1812433253u32
                .wrapping_mul(prev ^ (prev >> 30))
                .wrapping_add(i as u32);
        }
        let mut i = 1usize;
        let mut j = 0usize;
        let key_len = key.len().max(1);
        let mut k = STATE_SIZE.max(key_len);
        while k > 0 {
            let prev = self.state[(i + STATE_SIZE - 1) % STATE_SIZE];
            self.state[i] = (self.state[i] ^ ((prev ^ (prev >> 30)).wrapping_mul(1664525)))
                .wrapping_add(*key.get(j).unwrap_or(&0))
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= STATE_SIZE {
                self.state[0] = self.state[STATE_SIZE - 1];
                i = 1;
            }
            if j >= key_len {
                j = 0;
            }
            k -= 1;
        }
        k = STATE_SIZE - 1;
        while k > 0 {
            let prev = self.state[(i + STATE_SIZE - 1) % STATE_SIZE];
            self.state[i] = (self.state[i] ^ ((prev ^ (prev >> 30)).wrapping_mul(1566083941)))
                .wrapping_sub(i as u32);
            i += 1;
            if i >= STATE_SIZE {
                self.state[0] = self.state[STATE_SIZE - 1];
                i = 1;
            }
            k -= 1;
        }
        self.state[0] = 0x8000_0000;
        self.index = STATE_SIZE;
    }

    fn twist(&mut self) {
        for i in 0..STATE_SIZE {
            let x = (self.state[i] & UPPER_MASK) + (self.state[(i + 1) % STATE_SIZE] & LOWER_MASK);
            let mut xa = x >> 1;
            if x & 1 != 0 {
                xa ^= MATRIX_A;
            }
            self.state[i] = self.state[(i + M) % STATE_SIZE] ^ xa;
        }
        self.index = 0;
    }

    fn gen_u32(&mut self) -> u32 {
        if self.index >= STATE_SIZE {
            self.twist();
        }
        let mut y = self.state[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9D2C5680;
        y ^= (y << 15) & 0xEFC60000;
        y ^= y >> 18;
        y
    }

    pub fn random(&mut self) -> f64 {
        let a = (self.gen_u32() >> 5) as u64;
        let b = (self.gen_u32() >> 6) as u64;
        ((a << 26) + b) as f64 * (1.0 / (1u64 << 53) as f64)
    }

    pub fn getrandbits(&mut self, k: u32) -> Result<u128, PyRngError> {
        if k == 0 {
            return Ok(0);
        }
        if k > 128 {
            return Err(PyRngError::UnsupportedBits(k));
        }
        if k <= 32 {
            return Ok((self.gen_u32() >> (32 - k)) as u128);
        }
        let mut bits_remaining = k;
        let mut words: Vec<u32> = Vec::with_capacity(((k - 1) / 32 + 1) as usize);
        while bits_remaining > 0 {
            let mut r = self.gen_u32();
            if bits_remaining < 32 {
                r >>= 32 - bits_remaining;
            }
            words.push(r);
            bits_remaining = bits_remaining.saturating_sub(32);
        }
        let mut value: u128 = 0;
        for (i, word) in words.iter().enumerate() {
            value |= (*word as u128) << (32 * i as u32);
        }
        Ok(value)
    }

    pub fn randbelow(&mut self, n: u64) -> Result<u64, PyRngError> {
        if n == 0 {
            return Err(PyRngError::EmptyRange("randrange()"));
        }
        let k = 64 - n.leading_zeros();
        loop {
            let r = self.getrandbits(k)?;
            if r < n as u128 {
                return Ok(r as u64);
            }
        }
    }

    pub fn randrange(
        &mut self,
        start: i64,
        stop: Option<i64>,
        step: i64,
    ) -> Result<i64, PyRngError> {
        match stop {
            None => {
                if step != 1 {
                    return Err(PyRngError::MissingStop);
                }
                if start > 0 {
                    return Ok(self.randbelow(start as u64)? as i64);
                }
                Err(PyRngError::EmptyRange("randrange()"))
            }
            Some(stop_value) => {
                let width = stop_value as i128 - start as i128;
                let step128 = step as i128;
                if step128 == 1 {
                    if width > 0 {
                        if width as u128 > u64::MAX as u128 {
                            return Err(PyRngError::RangeTooLarge);
                        }
                        return Ok(start + self.randbelow(width as u64)? as i64);
                    }
                    return Err(PyRngError::EmptyRange("randrange(start, stop)"));
                }
                if step128 == 0 {
                    return Err(PyRngError::StepZero);
                }
                let numerator = if step128 > 0 {
                    width + step128 - 1
                } else {
                    width + step128 + 1
                };
                let n = div_floor(numerator, step128);
                if n <= 0 {
                    return Err(PyRngError::EmptyRange("randrange(start, stop, step)"));
                }
                if n as u128 > u64::MAX as u128 {
                    return Err(PyRngError::RangeTooLarge);
                }
                let offset = self.randbelow(n as u64)? as i128;
                Ok((start as i128 + step128 * offset) as i64)
            }
        }
    }

    pub fn sample_indices(
        &mut self,
        population: usize,
        k: usize,
    ) -> Result<Vec<usize>, PyRngError> {
        if k > population {
            return Err(PyRngError::EmptyRange("sample()"));
        }
        let mut result = Vec::with_capacity(k);
        if k == 0 {
            return Ok(result);
        }
        let mut setsize: usize = 21;
        if k > 5 {
            let exponent = ((k * 3) as f64).log(4.0).ceil() as u32;
            setsize += 4usize.pow(exponent);
        }
        if population <= setsize {
            let mut pool: Vec<usize> = (0..population).collect();
            for i in 0..k {
                let j = self.randbelow((population - i) as u64)? as usize;
                result.push(pool[j]);
                pool.swap(j, population - i - 1);
            }
        } else {
            let mut selected: HashSet<usize> = HashSet::with_capacity(k);
            while result.len() < k {
                let j = self.randbelow(population as u64)? as usize;
                if selected.insert(j) {
                    result.push(j);
                }
            }
        }
        Ok(result)
    }

    pub fn sample<T: Clone>(&mut self, population: &[T], k: usize) -> Result<Vec<T>, PyRngError> {
        let indices = self.sample_indices(population.len(), k)?;
        let mut out = Vec::with_capacity(k);
        for index in indices {
            out.push(population[index].clone());
        }
        Ok(out)
    }
}

impl RngCore for PyRng {
    fn next_u32(&mut self) -> u32 {
        self.gen_u32()
    }

    fn next_u64(&mut self) -> u64 {
        ((self.gen_u32() as u64) << 32) | self.gen_u32() as u64
    }

    fn fill_bytes(&mut self, dest: &mut [u8]) {
        self.try_fill_bytes(dest)
            .expect("PyRng::try_fill_bytes is infallible");
    }

    fn try_fill_bytes(&mut self, dest: &mut [u8]) -> Result<(), rand::Error> {
        let mut written = 0;
        while written < dest.len() {
            let chunk = self.gen_u32().to_le_bytes();
            let take = (dest.len() - written).min(chunk.len());
            dest[written..written + take].copy_from_slice(&chunk[..take]);
            written += take;
        }
        Ok(())
    }
}

impl SeedableRng for PyRng {
    type Seed = [u8; 8];

    fn from_seed(seed: Self::Seed) -> Self {
        Self::new(u64::from_le_bytes(seed))
    }

    fn seed_from_u64(seed: u64) -> Self {
        Self::new(seed)
    }
}

fn div_floor(a: i128, b: i128) -> i128 {
    let mut q = a / b;
    let r = a % b;
    if (r > 0 && b < 0) || (r < 0 && b > 0) {
        q -= 1;
    }
    q
}

#[cfg(test)]
mod tests {
    use super::PyRng;

    #[test]
    fn random_matches_python_for_master_seed() {
        let mut rng = PyRng::new(151);
        let expected = [
            0.7065737352491744,
            0.8459813212725689,
            0.9507856720093933,
            0.6327886858871649,
            0.20461024606293488,
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
    fn random_matches_python_for_derived_seed() {
        let mut rng = PyRng::new(13006513535068165406);
        let expected = [
            0.035611281084551805,
            0.303230319068173,
            0.5505529172330853,
            0.03282053534387952,
            0.013761028062003189,
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
    fn random_matches_python_for_additional_seed() {
        let mut rng = PyRng::new(3815924951222172525);
        let expected = [
            0.18518006574496737,
            0.5841689581060610,
            0.3699113163178772,
            0.7394349068470196,
            0.6855497906317899,
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
    fn randrange_supports_default_arguments() {
        let mut rng = PyRng::new(151);
        let expected = [6, 3, 5, 4, 5];
        for value in expected {
            let actual = rng.randrange(10, None, 1).unwrap();
            assert_eq!(value, actual);
        }
    }

    #[test]
    fn randrange_supports_custom_step() {
        let mut rng = PyRng::new(151);
        let expected = [35, 20, 30, 25, 30];
        for value in expected {
            let actual = rng.randrange(5, Some(50), 5).unwrap();
            assert_eq!(value, actual);
        }
        let mut rng = PyRng::new(13006513535068165406);
        let expected = [-50, -35, -30, -15, -10];
        for value in expected {
            let actual = rng.randrange(-50, Some(-5), 5).unwrap();
            assert_eq!(value, actual);
        }
    }

    #[test]
    fn getrandbits_matches_python() {
        let mut rng = PyRng::new(151);
        assert_eq!(2894, rng.getrandbits(12).unwrap());
        assert_eq!(1950700110956246240, rng.getrandbits(61).unwrap());
        let mut rng = PyRng::new(13006513535068165406);
        assert_eq!(145, rng.getrandbits(12).unwrap());
        assert_eq!(699201512668378865, rng.getrandbits(61).unwrap());
    }

    #[test]
    fn sample_matches_python_small_population() {
        let mut rng = PyRng::new(151);
        let population: Vec<_> = (0..20).collect();
        let actual = rng.sample(&population, 5).unwrap();
        let expected = vec![13, 6, 11, 9, 17];
        assert_eq!(expected, actual);
    }

    #[test]
    fn sample_matches_python_large_population() {
        let mut rng = PyRng::new(13006513535068165406);
        let population: Vec<_> = (0..1000).collect();
        let actual = rng.sample(&population, 15).unwrap();
        let expected = vec![
            36, 244, 310, 497, 563, 711, 33, 702, 14, 943, 239, 435, 252, 40, 623,
        ];
        assert_eq!(expected, actual);
    }
}

//! Content-based caching utilities.
//!
//! This module provides thread-safe caching with content-based keys rather than
//! pointer-based keys. Pointer-based caching is dangerous because Python can
//! reuse memory addresses after garbage collection, leading to cache poisoning.
//!
//! Values are stored wrapped in `Arc<V>` to enable cheap retrieval without
//! deep cloning the cached data.

use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::sync::{Arc, RwLock};

/// A thread-safe cache that uses content-based keys.
///
/// Unlike pointer-based caching, this approach hashes the actual content
/// to generate cache keys, ensuring correctness even when memory addresses
/// are reused.
///
/// Values are stored as `Arc<V>` internally, so retrieval returns a cheap
/// reference-counted pointer rather than cloning the entire value.
pub struct ContentCache<V> {
    data: RwLock<HashMap<u64, Arc<V>>>,
}

impl<V> ContentCache<V> {
    pub fn new() -> Self {
        Self {
            data: RwLock::new(HashMap::new()),
        }
    }

    /// Get a cached value by its content hash, if present.
    ///
    /// Returns an `Arc<V>` for cheap access without deep cloning.
    pub fn get(&self, hash: u64) -> Option<Arc<V>> {
        self.data.read().ok()?.get(&hash).cloned()
    }

    /// Get a cached value or insert it if not present.
    ///
    /// Returns an `Arc<V>` pointing to the cached value.
    pub fn get_or_insert_with<F>(&self, hash: u64, f: F) -> Arc<V>
    where
        F: FnOnce() -> V,
    {
        // Fast path: check if already cached
        if let Some(cached) = self.get(hash) {
            return cached;
        }

        // Slow path: compute and insert
        let value = Arc::new(f());
        if let Ok(mut guard) = self.data.write() {
            // Double-check in case another thread inserted while we were computing
            if let Some(existing) = guard.get(&hash) {
                return Arc::clone(existing);
            }
            guard.insert(hash, Arc::clone(&value));
        }
        value
    }
}

impl<V> Default for ContentCache<V> {
    fn default() -> Self {
        Self::new()
    }
}

// Safety: ContentCache uses RwLock which is Send + Sync when V is Send + Sync
unsafe impl<V: Send> Send for ContentCache<V> {}
unsafe impl<V: Send + Sync> Sync for ContentCache<V> {}

/// Compute a content-based hash for a keyboard layout mapping.
///
/// This creates a deterministic hash from the actual key-value pairs,
/// not from memory addresses.
pub fn hash_layout_map(layout: &HashMap<String, Vec<String>>) -> u64 {
    let mut hasher = DefaultHasher::new();

    // Sort keys for deterministic ordering
    let mut keys: Vec<_> = layout.keys().collect();
    keys.sort();

    for key in keys {
        key.hash(&mut hasher);
        if let Some(values) = layout.get(key) {
            values.len().hash(&mut hasher);
            for v in values {
                v.hash(&mut hasher);
            }
        }
    }

    hasher.finish()
}

/// Compute a content-based hash for a shift map.
pub fn hash_shift_map(shift_map: &HashMap<String, String>) -> u64 {
    let mut hasher = DefaultHasher::new();

    // Sort keys for deterministic ordering
    let mut keys: Vec<_> = shift_map.keys().collect();
    keys.sort();

    for key in keys {
        key.hash(&mut hasher);
        if let Some(value) = shift_map.get(key) {
            value.hash(&mut hasher);
        }
    }

    hasher.finish()
}

/// Compute a content-based hash for a layout vector.
pub fn hash_layout_vec(layout: &[(String, Vec<String>)]) -> u64 {
    let mut hasher = DefaultHasher::new();

    // Sort by key for deterministic ordering
    let mut sorted: Vec<_> = layout.iter().collect();
    sorted.sort_by_key(|(k, _)| k);

    for (key, values) in sorted {
        key.hash(&mut hasher);
        values.len().hash(&mut hasher);
        for v in values {
            v.hash(&mut hasher);
        }
    }

    hasher.finish()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_content_cache_basic() {
        let cache: ContentCache<String> = ContentCache::new();

        let value = cache.get_or_insert_with(42, || "hello".to_string());
        assert_eq!(&*value, "hello");

        // Should return cached value (same Arc, not a clone)
        let value2 = cache.get_or_insert_with(42, || "world".to_string());
        assert_eq!(&*value2, "hello");

        // Verify both point to the same allocation
        assert!(Arc::ptr_eq(&value, &value2));
    }

    #[test]
    fn test_hash_layout_map_deterministic() {
        let mut map1 = HashMap::new();
        map1.insert("a".to_string(), vec!["b".to_string(), "c".to_string()]);
        map1.insert("d".to_string(), vec!["e".to_string()]);

        let mut map2 = HashMap::new();
        map2.insert("d".to_string(), vec!["e".to_string()]);
        map2.insert("a".to_string(), vec!["b".to_string(), "c".to_string()]);

        // Same content should produce same hash regardless of insertion order
        assert_eq!(hash_layout_map(&map1), hash_layout_map(&map2));
    }

    #[test]
    fn test_hash_layout_map_different_content() {
        let mut map1 = HashMap::new();
        map1.insert("a".to_string(), vec!["b".to_string()]);

        let mut map2 = HashMap::new();
        map2.insert("a".to_string(), vec!["c".to_string()]);

        // Different content should produce different hash
        assert_ne!(hash_layout_map(&map1), hash_layout_map(&map2));
    }
}

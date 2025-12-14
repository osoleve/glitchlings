//! Thread-safe caching utilities for Python object materialization.
//!
//! This module provides a generic caching mechanism for expensive Python-to-Rust
//! conversions. Caches are keyed by Python object pointer address, which is stable
//! for the lifetime of the object.
//!
//! # Cache Poisoning
//!
//! `RwLock` becomes "poisoned" when a thread panics while holding the lock.
//! Rather than panicking on poisoned locks (which would cascade failures),
//! we recover by extracting the inner data. This is safe because:
//! 1. The data itself is still valid even if the updating thread panicked
//! 2. We'd rather return stale/reconstructed data than crash the Python process

use std::collections::HashMap;
use std::hash::Hash;
use std::sync::{Arc, PoisonError, RwLock, RwLockReadGuard, RwLockWriteGuard};

/// A thread-safe cache that stores `Arc<V>` values keyed by `K`.
///
/// Handles lock poisoning gracefully by recovering the inner data.
pub struct StaticCache<K, V> {
    inner: RwLock<HashMap<K, Arc<V>>>,
}

impl<K, V> StaticCache<K, V>
where
    K: Eq + Hash,
{
    /// Creates a new empty cache.
    pub fn new() -> Self {
        Self {
            inner: RwLock::new(HashMap::new()),
        }
    }

    /// Attempts to get a cached value by key.
    ///
    /// Returns `None` if the key is not present. Recovers gracefully from
    /// poisoned locks.
    pub fn get(&self, key: &K) -> Option<Arc<V>> {
        let guard = Self::recover_read(&self.inner);
        guard.get(key).cloned()
    }

    /// Inserts a value into the cache, returning the cached `Arc`.
    ///
    /// If the key already exists, returns the existing value without
    /// replacing it (first-writer-wins semantics).
    pub fn get_or_insert(&self, key: K, value: V) -> Arc<V> {
        // Check if already cached (common case)
        if let Some(cached) = self.get(&key) {
            return cached;
        }

        // Need to insert - acquire write lock
        let mut guard = Self::recover_write(&self.inner);

        // Double-check after acquiring write lock (another thread may have inserted)
        if let Some(cached) = guard.get(&key) {
            return cached.clone();
        }

        let arc = Arc::new(value);
        guard.insert(key, arc.clone());
        arc
    }

    /// Recovers a read guard from a potentially poisoned lock.
    #[inline]
    fn recover_read(lock: &RwLock<HashMap<K, Arc<V>>>) -> RwLockReadGuard<'_, HashMap<K, Arc<V>>> {
        lock.read().unwrap_or_else(PoisonError::into_inner)
    }

    /// Recovers a write guard from a potentially poisoned lock.
    #[inline]
    fn recover_write(
        lock: &RwLock<HashMap<K, Arc<V>>>,
    ) -> RwLockWriteGuard<'_, HashMap<K, Arc<V>>> {
        lock.write().unwrap_or_else(PoisonError::into_inner)
    }
}

impl<K, V> Default for StaticCache<K, V>
where
    K: Eq + Hash,
{
    fn default() -> Self {
        Self::new()
    }
}

// Safety: StaticCache uses RwLock which is Send + Sync when K and V are
unsafe impl<K: Send, V: Send> Send for StaticCache<K, V> {}
unsafe impl<K: Send + Sync, V: Send + Sync> Sync for StaticCache<K, V> {}

/// Macro to define a static cache with a getter function.
///
/// # Example
///
/// ```ignore
/// define_static_cache!(
///     layout_cache,           // getter function name
///     usize,                  // key type
///     HashMap<String, Vec<String>>  // value type
/// );
/// ```
#[macro_export]
macro_rules! define_static_cache {
    ($name:ident, $key:ty, $value:ty) => {
        fn $name() -> &'static $crate::cache::StaticCache<$key, $value> {
            static CACHE: std::sync::OnceLock<$crate::cache::StaticCache<$key, $value>> =
                std::sync::OnceLock::new();
            CACHE.get_or_init($crate::cache::StaticCache::new)
        }
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_insert_and_get() {
        let cache: StaticCache<usize, String> = StaticCache::new();

        let value = cache.get_or_insert(42, "hello".to_string());
        assert_eq!(&*value, "hello");

        // Second insert with same key returns original value
        let value2 = cache.get_or_insert(42, "world".to_string());
        assert_eq!(&*value2, "hello");

        // Different key works
        let value3 = cache.get_or_insert(99, "world".to_string());
        assert_eq!(&*value3, "world");
    }

    #[test]
    fn test_cache_get_missing() {
        let cache: StaticCache<usize, String> = StaticCache::new();
        assert!(cache.get(&42).is_none());
    }

    #[test]
    fn test_cache_arc_sharing() {
        let cache: StaticCache<usize, String> = StaticCache::new();

        let arc1 = cache.get_or_insert(1, "shared".to_string());
        let arc2 = cache.get(&1).unwrap();

        // Both point to the same allocation
        assert!(Arc::ptr_eq(&arc1, &arc2));
    }
}

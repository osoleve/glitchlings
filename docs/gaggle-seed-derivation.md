# Gaggle Seed Derivation

Deterministic seeds keep a gaggle's glitchlings reproducible across runs. The master seed supplied to the gaggle is transformed into a unique per-glitchling seed by `Gaggle.derive_seed` so that every creature sees its own stable random number stream, even when the gaggle contents or ordering change.【F:src/glitchlings/zoo/core.py†L437-L492】

## How the digest is built

```python
Gaggle.derive_seed(master_seed, glitchling_name, index)
```

1. Convert the integer master seed into a big-endian byte string (including handling negative values) via a helper that guarantees at least one byte of output.
2. Feed those bytes into an 8-byte `blake2s` digest, inserting a `\x00` separator.
3. Encode the glitchling's canonical name as UTF-8, add another separator, and append the gaggle index (the position assigned during orchestration) as bytes.
4. Convert the resulting 8-byte digest back into an integer, which becomes the glitchling's seed.

The byte conversion helper retries for negative numbers until Python's `int.to_bytes` accepts the chosen width, so even large negative seeds produce a stable byte representation.【F:src/glitchlings/zoo/core.py†L470-L484】

## Seed pipeline

```mermaid
flowchart TD
    MasterSeed['Master seed (int)'] -->|_int_to_bytes| SeedBytes[Master seed bytes]
    SeedBytes --> Hash[[blake2s digest (8 bytes)]]
    GlitchlingName[Glitchling name] -->|UTF-8 + "\x00"| Hash
    Index[Orchestration index] -->|_int_to_bytes + "\x00"| Hash
    Hash --> DerivedSeed[Derived seed (int)]
```

Because each stage uses both the glitchling name and its index in the gaggle, clones of the same glitchling still receive distinct seeds and the plan remains stable regardless of execution order.【F:src/glitchlings/zoo/core.py†L443-L507】

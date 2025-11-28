# Determinism guide

Glitchlings are deterministic by design. Use the knobs below to keep runs reproducible across machines and environments.

## Seeds and RNGs

- **Glitchlings** – every glitchling owns a private `random.Random`. Pass `seed=` on construction (or call `reset_rng`) to stabilise behaviour.
- **Gaggle** – pass `seed=` to derive per-glitchling seeds via `Gaggle.derive_seed`. Changing the roster order or names changes the derived seeds.
- **Attack helper** - pass `seed=` to `Attack(...)` when providing a sequence; Attack will build a seeded `Gaggle` using `DEFAULT_ATTACK_SEED` when none is given. Supplying an existing `Gaggle` or `Glitchling` clones it before applying the seed so the caller's instance is never mutated.
- **Dataset corruption** - the enclosing gaggle seed controls dataset corruption; reuse the same seed to reproduce `GlitchedDataset(...)` wraps or `Gaggle.corrupt_dataset(..., columns=...)` output.
- **Rust pipeline** – seeds are forwarded into the compiled pipeline; keep Rust and Python in lockstep by using the same master seed across runs.

## Best practices

- Stabilise candidate ordering before sampling subsets (e.g., sort replacement pools) to avoid drift.
- Derive new seeds from the surrounding context rather than relying on global RNG state.
- Expose configurable parameters through `set_param` so tests can reset state predictably.

## Quick checklist

1. Set `seed=` on glitchlings and gaggles.
2. Pass `seed=` to `Attack(...)` when building from a list.
3. Keep roster names and order stable if you expect identical derived seeds.
4. Avoid module-level randomness; route everything through the glitchling RNG.

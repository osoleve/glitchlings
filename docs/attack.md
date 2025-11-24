# Attack module

The `glitchlings.attack.Attack` helper runs a roster of glitchlings, tokenises both the clean and corrupted text, and reports similarity metrics in one call. It mirrors the rest of the library's determinism guarantees while handling transcripts as batches.

## When to use it

- You want the **original, corrupted text, tokens, token IDs, and metrics** in a single object.
- You need **deterministic runs** without hand-rolling Gaggle construction and seeding.
- You plan to **compare transcript-style chat turns**: transcripts are treated as batches and metrics return one value per turn.

## Parameters

- `glitchlings`: A `Glitchling`, a `Gaggle`, or any sequence of glitchlings. Sequences are wrapped in a `Gaggle`.
- `seed`: Master seed used when constructing a `Gaggle` from a sequence (defaults to `DEFAULT_ATTACK_SEED`). If you pass an existing `Gaggle` or `Glitchling`, the seed is applied directly and the RNG is reset.
- `tokenizer`: Optional tokenizer name or object. Defaults to a modern `tiktoken` encoding (`o200k_base`, falling back to `cl100k_base`, then whitespace). Hugging Face `tokenizers.Tokenizer` instances and names are also supported.
- `metrics`: Mapping of metric names to callables. Defaults to the Rust-backed `jensen_shannon_divergence`, `normalized_edit_distance`, and `subsequence_retention`.
- Sequences must contain glitchling instances; mixed types raise a `TypeError` at construction.

## Transcript handling

If you pass a transcript (list of dicts containing `content`), `Attack`:

- Treats each turn as a separate sample in a batch.
- Encodes each turn independently.
- Returns per-turn metrics as lists (aligned with the transcript order).
- Returns empty metric lists for empty transcripts (no turns in, no turns out).

Input and output types must match; mixed string/transcript pairs raise an error.

## Example

```python
from glitchlings import Mim1c, Rushmore, Typogre
from glitchlings.attack import Attack

attack = Attack(
    [Rushmore(rate=0.05), Mim1c(rate=0.02), Typogre(rate=0.03)],
    seed=404,
)

result = attack.run("Glitchlings keep your evaluations honest.")
print(result.metrics["normalized_edit_distance"])
print(result.input_tokens)
print(result.output_tokens)
```

## Choosing a tokenizer

By default, Attack uses a lightweight `tiktoken` encoder:

- Tries `o200k_base` first (good coverage for modern LLM contexts).
- Falls back to `cl100k_base`, then to a whitespace tokenizer if tiktoken is unavailable.
- Pass a name (e.g., `"gpt2"`), a `tiktoken.Encoding`, a Hugging Face `tokenizers.Tokenizer`, or a custom object implementing `encode`/`decode`.

## Determinism

- Default seeds align with the rest of the library (`DEFAULT_ATTACK_SEED = 151`).
- Passing `seed=` stabilises both roster ordering and per-glitchling RNGs when Attack builds the `Gaggle`.
- When a `Gaggle` or `Glitchling` instance is supplied directly, the seed is applied to that instance and its RNG is reset to keep outputs reproducible.

## Metrics and performance

The default metrics run inside the compiled Rust extension for speed:

- **Jensen-Shannon divergence** (`jensen_shannon_divergence`)
- **Normalized edit distance** (`normalized_edit_distance`)
- **Subsequence retention** (`subsequence_retention`)

Custom metrics can be supplied; they should accept two token sequences or two batches of token sequences and return either a float or a list of floats.

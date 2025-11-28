# Attack module

The `glitchlings.attack.Attack` helper runs a roster of glitchlings, tokenises both the clean and corrupted text, and reports similarity metrics in one call. It mirrors the rest of the library's determinism guarantees while handling transcripts as batches.

## When to use it

- You want the **original, corrupted text, tokens, token IDs, and metrics** in a single object.
- You need **deterministic runs** without hand-rolling Gaggle construction and seeding.
- You plan to **compare transcript-style chat turns**: transcripts are treated as batches and metrics return one value per turn.

## Parameters

- `glitchlings`: A `Glitchling`, a `Gaggle`, or any sequence of glitchlings. Sequences are wrapped in a `Gaggle`.
- `seed`: Master seed used when constructing a `Gaggle` from a sequence (defaults to `DEFAULT_ATTACK_SEED`). If you pass an existing `Gaggle` or `Glitchling`, Attack clones it before applying the seed so your original object stays untouched while the Attack-owned copy is reseeded.
- `transcript_target`: Controls which transcript turns are corrupted. See below for options.
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

### Controlling which turns are corrupted

The `transcript_target` parameter controls which transcript turns are corrupted:

| Value | Effect |
|-------|--------|
| `"last"` | Corrupt only the last turn (default). |
| `"all"` | Corrupt all turns. |
| `"assistant"` | Corrupt only turns with `role="assistant"`. |
| `"user"` | Corrupt only turns with `role="user"`. |
| `int` | Corrupt a specific turn by index (negative indexing supported). |
| `Sequence[int]` | Corrupt multiple specific turns by index. |

This setting is available on `Attack`, `Gaggle`, and `Glitchling`. The default (`"last"`) matches the previous implicit behaviour.

```python
from glitchlings import Typogre, Gaggle
from glitchlings.attack import Attack

# Corrupt only assistant turns
attack = Attack([Typogre()], transcript_target="assistant")

# Or set it directly on a Gaggle
gaggle = Gaggle([Typogre()], transcript_target="all")
```

## Plain string batches

`Attack.run` accepts simple `list[str]` batches in addition to transcripts. Each entry is corrupted independently, tokenised, and scored, with metrics returned per element:

```python
attack = Attack(["Typogre(rate=0.02)"])
batched = attack.run(["left", "right"])
print(batched.metrics["normalized_edit_distance"])  # -> [0.0, 0.21]
```

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

## Quick summaries

`AttackResult.summary()` renders a compact, human-readable view of token drift and metrics without manual iteration:

```python
summary = result.summary(max_rows=6)
print(summary)
```

It highlights token count deltas, metric values, and a small token-by-token comparison (truncated to keep the output scannable).

## Comparing tokenizers

Use `Attack.compare` to benchmark multiple tokenizers against the same corruption in one call. It returns a `MultiAttackResult` with keyed `AttackResult` objects and a combined summary:

```python
comparison = attack.compare(
    SAMPLE_TEXT,
    tokenizers=["cl100k_base", "gpt2"],
)

print(comparison.summary())
json_ready = comparison.to_report()
```

When `include_self=True` (default), the Attack's configured tokenizer is included alongside the provided list.

## CLI reports

Prefer to stay in the terminal? The `glitchlings` CLI exposes the same report via `--report` (alias `--attack`):

```bash
glitchlings --report json --sample
glitchlings --report yaml "Corrupt me"
```

## Choosing a tokenizer

By default, Attack uses a lightweight `tiktoken` encoder:

- Tries `o200k_base` first (good coverage for modern LLM contexts).
- Falls back to `cl100k_base`, then to a whitespace tokenizer if tiktoken is unavailable.
- Pass a name (e.g., `"gpt2"`), a `tiktoken.Encoding`, a Hugging Face `tokenizers.Tokenizer`, or a custom object implementing `encode`/`decode`.

## Determinism

- Default seeds align with the rest of the library (`DEFAULT_ATTACK_SEED = 151`).
- Passing `seed=` stabilises both roster ordering and per-glitchling RNGs when Attack builds the `Gaggle`.
- When a `Gaggle` or `Glitchling` instance is supplied directly, Attack clones it before applying the seed so caller-owned instances are never mutated while the Attack copy is reseeded.

## Metrics and performance

The default metrics run inside the compiled Rust extension for speed:

- **Jensen-Shannon divergence** (`jensen_shannon_divergence`)
- **Normalized edit distance** (`normalized_edit_distance`)
- **Subsequence retention** (`subsequence_retention`)

Custom metrics can be supplied; they should accept two token sequences or two batches of token sequences and return either a float or a list of floats.

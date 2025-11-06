# Auggie

Auggie is a laboratory assistant for composing gaggles. It wraps the
:class:`~glitchlings.zoo.core.Gaggle` API with behaviour-focused helper methods so
you can stack glitchlings without memorising every signature.

- **Scope**: orchestrator (builds multi-glitchling pipelines).
- **Signature**: `Auggie(glitchlings: Iterable[Glitchling] | None = None, seed: int = 151)`.
- **Behaviour**: maintains a "blueprint" of glitchlings, cloning them behind the
  scenes so each invocation is deterministic. Every helper (``.typo()``,
  ``.confusable()``, ``.pedantry()``, and friends) adds a pre-configured
  glitchling to the roster and returns the same Auggie instance for fluent
  chaining.

## Quick start

```python
from glitchlings import Auggie, SAMPLE_TEXT

auggie = (
    Auggie(seed=404)
    .typo(rate=0.015)
    .confusable(rate=0.01, classes=["LATIN", "CYRILLIC"])
    .homophone(rate=0.02)
)

print(auggie(SAMPLE_TEXT)[:240])
```

Auggie behaves just like a ``Gaggle``: call the instance on a string or iterable
and it will apply each staged glitchling in a deterministic order.

## Behaviour-focused helpers

All helpers accept the same parameters as their underlying glitchlings, making it
straightforward to tune the roster without drilling into individual docs.

```python
from glitchlings import Auggie
from glitchlings.zoo.pedant import PedantStone

auggie = (
    Auggie()
    .typo(rate=0.01, keyboard="DVORAK")
    .stretch(rate=0.4, extension_max=7)
    .pedantry(stone=PedantStone.FUNNELITE)
    .remix(modes=["delete", "swap"], swap_rate=0.02)
    .redact(rate=0.05)
)
```

Behind the scenes Auggie clones the configured glitchlings and keeps an internal
blueprint so you can reuse the same assistant as a template:

```python
base = Auggie().typo(rate=0.01).homophone(rate=0.02)
variant = base.clone(seed=999).synonym(rate=0.03, part_of_speech="v")
```

## Dataset pipelines

Because Auggie subclasses ``Gaggle``, it plugs into the dataset helpers in the
same way. Use ``.corrupt_dataset`` for Hugging Face datasets or slot it into your
existing map-style transforms:

```python
from datasets import load_dataset
from glitchlings import Auggie

dataset = load_dataset("ag_news")
auggie = Auggie(seed=151).typo(rate=0.02).ocr(rate=0.01)

corrupted = auggie.corrupt_dataset(dataset, columns=["text"], description="ag_news + OCR noise")
```

Need finer control? Build the initial roster manually and hand it to Auggie:

```python
from glitchlings import Auggie, Mim1c, Zeedub

automaton = Auggie([Mim1c(rate=0.03), Zeedub(rate=0.01)], seed=2024)
```

Auggie will copy the provided glitchlings into its blueprint and expose the same
helper methods for subsequent adjustments.

from __future__ import annotations

import importlib
import random

apostrofae_module = importlib.import_module("glitchlings.zoo.apostrofae")
core_module = importlib.import_module("glitchlings.zoo.core")


def test_python_fallback_replaces_pairs():
    text = "\"Hello\", he wrote, `code` and 'world'. It's tricky."
    rng = random.Random(1337)
    result = apostrofae_module._apostrofae_python(text, rng=rng)

    assert result != text
    assert '"' not in result
    assert "`" not in result
    assert result.count("'") == 1  # Only the apostrophe from It's should remain.


def test_apostrofae_pipeline_descriptor():
    glitch = apostrofae_module.Apostrofae(seed=2024)
    assert glitch.pipeline_operation() == {"type": "apostrofae"}


def test_apostrofae_invokes_python_fallback(monkeypatch):
    monkeypatch.setattr(apostrofae_module, "_apostrofae_rust", None, raising=False)

    text = '"Hello" there'
    seed = 99
    derived = core_module.Gaggle.derive_seed(seed, apostrofae_module.apostrofae.name, 0)
    expected = apostrofae_module._apostrofae_python(text, rng=random.Random(derived))

    glitch = apostrofae_module.Apostrofae(seed=seed)
    glitch.reset_rng(seed)
    assert glitch(text) == expected

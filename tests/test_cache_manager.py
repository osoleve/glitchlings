from __future__ import annotations

import logging

import pytest

from glitchlings import summon
from glitchlings.util import CacheManager


def test_cache_key_deterministic(tmp_path) -> None:
    cache = CacheManager(cache_dir=tmp_path)
    text = "lorem ipsum"
    configuration = {
        "seed": 42,
        "glitchlings": [
            {"name": "Typogre", "kwargs": {"rate": 0.01}, "level": 5, "order": 1},
            {"name": "Reduple", "kwargs": {"rate": 0.02}, "level": 4, "order": 2},
        ],
    }
    flipped = {
        "glitchlings": list(reversed(configuration["glitchlings"])),
        "seed": 42,
    }
    key = cache.make_key(text=text, configuration=configuration)
    assert key == cache.make_key(text=text, configuration=flipped)


def test_gaggle_corrupt_with_cache(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    cache = CacheManager(cache_dir=tmp_path)
    gaggle = summon(["Typogre(rate=0.01)", "Reduple(rate=0.01)"])
    text = "Summon the glitchlings"

    caplog.set_level(logging.INFO, logger="glitchlings.cache")

    first = gaggle.corrupt_with_cache(text, cache)
    second = gaggle.corrupt_with_cache(text, cache)

    assert first == second
    key = cache.make_key(text=text, configuration=gaggle.cache_descriptor())
    assert cache.get(key) == first

    messages = [record.message for record in caplog.records if record.name == "glitchlings.cache"]
    assert any("Cache miss" in message for message in messages)
    assert any("Cache hit" in message for message in messages)

    cache.clear()
    assert cache.get(key) is None

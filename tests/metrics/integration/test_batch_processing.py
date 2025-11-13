"""Integration tests for batch processing - Milestone 3.

Tests the complete pipeline: texts → glitchling → tokenizers → metrics → Parquet.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from glitchlings.metrics.core.batch import BatchProcessor, ParquetWriter, process_and_write
from glitchlings.metrics.core.schema import Observation, RunManifest
from glitchlings.metrics.core.tokenizers import SimpleTokenizer
from glitchlings.metrics.metrics.defaults import create_default_registry


@pytest.fixture
def registry():
    """Provide default metric registry."""
    return create_default_registry()


@pytest.fixture
def tokenizer():
    """Provide simple tokenizer."""
    return SimpleTokenizer()


@pytest.fixture
def temp_output_dir():
    """Provide temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def uppercase_glitchling(text: str) -> str:
    """Simple glitchling for testing."""
    return text.upper()


def test_batch_processor_single_text(registry, tokenizer):
    """Test batch processor on single text."""
    processor = BatchProcessor(registry, [tokenizer])

    observations = list(
        processor.process(
            texts=["hello world"],
            glitchling_fn=uppercase_glitchling,
            glitchling_id="uppercase",
            input_type="test",
        )
    )

    assert len(observations) == 1  # One observation per tokenizer

    obs = observations[0]
    assert obs.glitchling_id == "uppercase"
    assert obs.input_type == "test"
    assert obs.tokenizer_id == "simple-whitespace"
    assert obs.m > 0  # Has tokens
    assert obs.n > 0
    assert len(obs.metrics) > 0  # Computed metrics


def test_batch_processor_multiple_texts(registry, tokenizer):
    """Test batch processor on multiple texts."""
    processor = BatchProcessor(registry, [tokenizer])

    texts = ["hello", "world", "foo bar"]

    observations = list(
        processor.process(
            texts=texts,
            glitchling_fn=uppercase_glitchling,
            glitchling_id="uppercase",
        )
    )

    assert len(observations) == len(texts)  # One per text

    # Check input IDs are unique
    input_ids = {obs.input_id for obs in observations}
    assert len(input_ids) == len(texts)


def test_batch_processor_multiple_tokenizers(registry):
    """Test batch processor with multiple tokenizers."""
    tok1 = SimpleTokenizer()
    tok2 = SimpleTokenizer()  # Second instance

    processor = BatchProcessor(registry, [tok1, tok2])

    observations = list(
        processor.process(
            texts=["test"],
            glitchling_fn=uppercase_glitchling,
            glitchling_id="uppercase",
        )
    )

    assert len(observations) == 2  # One per tokenizer


def test_batch_processor_store_text(registry, tokenizer):
    """Test storing original/corrupted text."""
    processor = BatchProcessor(registry, [tokenizer])

    observations = list(
        processor.process(
            texts=["hello world"],
            glitchling_fn=uppercase_glitchling,
            glitchling_id="uppercase",
            store_text=True,
        )
    )

    obs = observations[0]
    assert obs.text_before == "hello world"
    assert obs.text_after == "HELLO WORLD"


def test_observation_hashes():
    """Test observation automatically computes token hashes."""
    obs = Observation(
        run_id="test",
        observation_id="obs1",
        input_id="input1",
        input_type="test",
        glitchling_id="test",
        tokenizer_id="test-tok",
        tokens_before=[1, 2, 3],
        tokens_after=[1, 2, 3],
        m=3,
        n=3,
    )

    assert obs.tokens_before_hash is not None
    assert obs.tokens_after_hash is not None
    assert len(obs.tokens_before_hash) == 16  # Truncated SHA256


def test_observation_to_dict():
    """Test observation serialization."""
    obs = Observation(
        run_id="test",
        observation_id="obs1",
        input_id="input1",
        input_type="test",
        glitchling_id="test",
        tokenizer_id="test-tok",
        tokens_before=[1, 2, 3],
        tokens_after=[4, 5, 6],
        m=3,
        n=3,
        metrics={"ned.value": 1.0, "lcsr.value": 0.0},
    )

    d = obs.to_dict()

    assert d["run_id"] == "test"
    assert d["metric_ned.value"] == 1.0
    assert d["metric_lcsr.value"] == 0.0
    assert "tokens_before" not in d  # Not included by default

    # With tokens
    d_with_tokens = obs.to_dict(include_tokens=True)
    assert d_with_tokens["tokens_before"] == [1, 2, 3]


def test_run_manifest_serialization():
    """Test manifest JSON serialization."""
    manifest = RunManifest(
        run_id="test-run",
        created_at="2025-01-01T00:00:00Z",
        config={"param": "value"},
        tokenizers=["gpt2", "bert"],
        metrics=["ned", "lcsr"],
        num_observations=100,
        seed=42,
    )

    # To JSON
    json_str = manifest.to_json()
    assert "test-run" in json_str

    # From JSON
    loaded = RunManifest.from_json(json_str)
    assert loaded.run_id == "test-run"
    assert loaded.num_observations == 100
    assert loaded.seed == 42


def test_parquet_writer_single_file(temp_output_dir, registry, tokenizer):
    """Test writing observations to single Parquet file."""
    processor = BatchProcessor(registry, [tokenizer])

    observations = list(
        processor.process(
            texts=["test one", "test two"],
            glitchling_fn=uppercase_glitchling,
            glitchling_id="uppercase",
        )
    )

    writer = ParquetWriter(temp_output_dir)
    output_path = writer.write(observations)

    assert output_path.exists()
    assert output_path.suffix == ".parquet"

    # Verify we can read it back
    try:
        import pandas as pd

        df = pd.read_parquet(output_path)
        assert len(df) == 2
        assert "metric_ned.value" in df.columns
    except ImportError:
        pytest.skip("pandas not installed")


def test_parquet_writer_manifest(temp_output_dir):
    """Test writing and reading manifest."""
    writer = ParquetWriter(temp_output_dir)

    manifest = RunManifest(
        run_id="test-manifest",
        created_at="2025-01-01T00:00:00Z",
        config={},
        tokenizers=["simple"],
        metrics=["ned"],
        num_observations=10,
    )

    # Write
    manifest_path = writer.write_manifest(manifest)
    assert manifest_path.exists()

    # Read back
    loaded = writer.read_manifest("test-manifest")
    assert loaded.run_id == "test-manifest"
    assert loaded.num_observations == 10


def test_process_and_write_end_to_end(temp_output_dir, registry, tokenizer):
    """Test complete end-to-end pipeline."""
    texts = ["hello world", "foo bar baz"]

    parquet_path, manifest = process_and_write(
        texts=texts,
        glitchling_fn=uppercase_glitchling,
        glitchling_id="uppercase",
        registry=registry,
        tokenizers=[tokenizer],
        output_dir=temp_output_dir,
        input_type="test",
        seed=42,
    )

    # Check Parquet file created
    assert parquet_path.exists()

    # Check manifest
    assert manifest.run_id is not None
    assert manifest.num_observations == len(texts)
    assert manifest.seed == 42
    assert "uppercase" in manifest.config["glitchling_id"]

    # Check manifest file created
    manifest_file = temp_output_dir / f"manifest_{manifest.run_id}.json"
    assert manifest_file.exists()


def test_empty_text_handling(registry, tokenizer):
    """Test handling of empty strings."""
    processor = BatchProcessor(registry, [tokenizer])

    observations = list(
        processor.process(
            texts=[""],
            glitchling_fn=uppercase_glitchling,
            glitchling_id="uppercase",
        )
    )

    assert len(observations) == 1
    obs = observations[0]
    assert obs.m == 0  # Empty token sequence
    assert obs.n == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

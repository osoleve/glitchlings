"""Batch processing for metrics computation.

Provides streaming batch processing with Parquet output and run manifests.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from ..metrics.registry import MetricRegistry
from .schema import Observation, RunManifest
from .tokenizers import TokenizerAdapter


class BatchProcessor:
    """Streaming batch processor for metrics computation.

    Processes (text, glitchling, tokenizer) tuples and computes metrics,
    yielding observations for storage.

    Example:
        >>> processor = BatchProcessor(registry, tokenizers)
        >>> observations = processor.process(
        ...     texts=["Hello world", "Test"],
        ...     glitchling_fn=lambda t: t.upper(),
        ...     glitchling_id="uppercase",
        ...     input_type="demo"
        ... )
        >>> for obs in observations:
        ...     print(obs.metrics)
    """

    def __init__(
        self,
        registry: MetricRegistry,
        tokenizers: Iterable[TokenizerAdapter],
        context: Mapping[str, Any] | None = None,
    ):
        """Initialize batch processor.

        Args:
            registry: Metric registry with registered metrics
            tokenizers: Iterable of tokenizer adapters
            context: Optional context dict for metrics
        """
        self.registry = registry
        self.tokenizers = list(tokenizers)
        self.context = dict(context) if context else {}

    def process(
        self,
        texts: Iterable[str],
        glitchling_fn: Callable[[str], str],
        glitchling_id: str,
        input_type: str = "default",
        gaggle_id: str | None = None,
        run_id: str | None = None,
        store_text: bool = False,
    ) -> Iterable[Observation]:
        """Process texts through glitchling and compute metrics.

        Args:
            texts: Iterable of input texts
            glitchling_fn: Function text -> corrupted_text
            glitchling_id: Identifier for the glitchling
            input_type: Category/type of inputs
            gaggle_id: Optional gaggle identifier
            run_id: Optional run ID (generated if not provided)
            store_text: Store original/corrupted text in observations

        Yields:
            Observation objects with computed metrics

        Example:
            >>> def uppercase(text):
            ...     return text.upper()
            >>> obs = list(processor.process(
            ...     ["hello"],
            ...     uppercase,
            ...     "uppercase"
            ... ))
            >>> len(obs)  # One per tokenizer
            2
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        for input_idx, text_before in enumerate(texts):
            input_id = f"input_{input_idx}"

            # Apply glitchling
            text_after = glitchling_fn(text_before)

            # Process with each tokenizer
            for tokenizer in self.tokenizers:
                # Tokenize
                tokens_before = list(tokenizer.encode(text_before))
                tokens_after = list(tokenizer.encode(text_after))

                # Compute metrics
                metrics = self.registry.compute_all(
                    tokens_before, tokens_after, self.context
                )

                # Create observation
                observation = Observation(
                    run_id=run_id,
                    observation_id=f"{run_id}_{input_id}_{tokenizer.name}",
                    input_id=input_id,
                    input_type=input_type,
                    glitchling_id=glitchling_id,
                    gaggle_id=gaggle_id,
                    tokenizer_id=tokenizer.name,
                    tokens_before=tokens_before,
                    tokens_after=tokens_after,
                    m=len(tokens_before),
                    n=len(tokens_after),
                    metrics=metrics,
                    text_before=text_before if store_text else None,
                    text_after=text_after if store_text else None,
                    context={"vocab_hash": tokenizer.vocab_hash()},
                )

                yield observation


class ParquetWriter:
    """Write observations to Parquet files with partitioning.

    Supports partitioning by tokenizer, glitchling, and/or input_type for
    efficient querying.

    Example:
        >>> writer = ParquetWriter("results/")
        >>> writer.write(observations, partition_by=["tokenizer_id"])
    """

    def __init__(self, output_dir: str | Path):
        """Initialize Parquet writer.

        Args:
            output_dir: Directory to write Parquet files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        observations: Iterable[Observation],
        partition_by: list[str] | None = None,
        include_tokens: bool = False,
    ) -> Path:
        """Write observations to Parquet.

        Args:
            observations: Iterable of observations
            partition_by: Partition columns (e.g., ["tokenizer_id"])
            include_tokens: Include full token sequences (expensive)

        Returns:
            Path to output file or directory

        Note:
            Requires pandas and pyarrow to be installed.
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas required for Parquet writing. "
                "Install with: pip install 'glitchlings[metrics]'"
            ) from e

        # Collect observations into DataFrame
        rows = [obs.to_dict(include_tokens=include_tokens) for obs in observations]

        if not rows:
            raise ValueError("No observations to write")

        df = pd.DataFrame(rows)

        # Write with optional partitioning
        if partition_by:
            # Partitioned write (Hive-style)
            output_path = self.output_dir / "observations.parquet"
            df.to_parquet(
                output_path,
                partition_cols=partition_by,
                engine="pyarrow",
                index=False,
            )
        else:
            # Single file write
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"observations_{timestamp}.parquet"
            df.to_parquet(output_path, engine="pyarrow", index=False)

        return output_path

    def write_manifest(self, manifest: RunManifest) -> Path:
        """Write run manifest to JSON.

        Args:
            manifest: RunManifest to serialize

        Returns:
            Path to manifest file
        """
        manifest_path = self.output_dir / f"manifest_{manifest.run_id}.json"
        manifest_path.write_text(manifest.to_json())
        return manifest_path

    def read_manifest(self, run_id: str) -> RunManifest:
        """Read run manifest from JSON.

        Args:
            run_id: Run ID to load

        Returns:
            RunManifest object

        Raises:
            FileNotFoundError: If manifest not found
        """
        manifest_path = self.output_dir / f"manifest_{run_id}.json"
        return RunManifest.from_json(manifest_path.read_text())


def process_and_write(
    texts: Iterable[str],
    glitchling_fn: Callable[[str], str],
    glitchling_id: str,
    registry: MetricRegistry,
    tokenizers: Iterable[TokenizerAdapter],
    output_dir: str | Path,
    input_type: str = "default",
    partition_by: list[str] | None = None,
    store_text: bool = False,
    seed: int | None = None,
) -> tuple[Path, RunManifest]:
    """Convenience function: process texts and write to Parquet in one shot.

    Args:
        texts: Input texts
        glitchling_fn: Glitchling function
        glitchling_id: Glitchling identifier
        registry: Metric registry
        tokenizers: Tokenizer adapters
        output_dir: Output directory
        input_type: Input type category
        partition_by: Partition columns
        store_text: Store text in observations
        seed: Random seed

    Returns:
        Tuple of (parquet_path, manifest)

    Example:
        >>> path, manifest = process_and_write(
        ...     texts=["hello", "world"],
        ...     glitchling_fn=lambda t: t.upper(),
        ...     glitchling_id="uppercase",
        ...     registry=registry,
        ...     tokenizers=[tokenizer],
        ...     output_dir="results/"
        ... )
    """
    run_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    # Process
    processor = BatchProcessor(registry, tokenizers)
    observations_list = list(
        processor.process(
            texts=texts,
            glitchling_fn=glitchling_fn,
            glitchling_id=glitchling_id,
            input_type=input_type,
            run_id=run_id,
            store_text=store_text,
        )
    )

    # Write observations
    writer = ParquetWriter(output_dir)
    parquet_path = writer.write(
        observations_list, partition_by=partition_by, include_tokens=False
    )

    # Create and write manifest
    tokenizer_names = [tok.name for tok in tokenizers]
    metric_ids = [spec.id for spec in registry.list_metrics()]

    manifest = RunManifest(
        run_id=run_id,
        created_at=created_at,
        config={
            "glitchling_id": glitchling_id,
            "input_type": input_type,
            "partition_by": partition_by,
            "store_text": store_text,
        },
        tokenizers=tokenizer_names,
        metrics=metric_ids,
        num_observations=len(observations_list),
        seed=seed,
    )

    manifest_path = writer.write_manifest(manifest)

    return parquet_path, manifest


__all__ = [
    "BatchProcessor",
    "ParquetWriter",
    "process_and_write",
]

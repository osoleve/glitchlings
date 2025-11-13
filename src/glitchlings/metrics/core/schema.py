"""Data schemas for metrics storage.

Defines the structure for storing metrics results in Parquet format
with proper partitioning and metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RunManifest:
    """Metadata for a metrics computation run.

    Stores configuration and context needed for reproducibility.

    Attributes:
        run_id: Unique identifier for this run (UUID or timestamp)
        created_at: ISO 8601 timestamp
        config: JSON-serializable configuration dict
        tokenizers: List of tokenizer names used
        metrics: List of metric IDs computed
        num_observations: Total observations processed
        seed: Random seed (if applicable)
    """

    run_id: str
    created_at: str
    config: Mapping[str, Any]
    tokenizers: Sequence[str]
    metrics: Sequence[str]
    num_observations: int = 0
    seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "config": dict(self.config),
            "tokenizers": list(self.tokenizers),
            "metrics": list(self.metrics),
            "num_observations": self.num_observations,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunManifest:
        """Load from dictionary."""
        return cls(
            run_id=data["run_id"],
            created_at=data["created_at"],
            config=data["config"],
            tokenizers=data["tokenizers"],
            metrics=data["metrics"],
            num_observations=data.get("num_observations", 0),
            seed=data.get("seed"),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> RunManifest:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Observation:
    """Single observation of metrics for one (text, glitchling, tokenizer) triple.

    Attributes:
        run_id: Reference to parent run
        observation_id: Unique ID for this observation
        input_id: Identifier for the input text
        input_type: Category/type of input (e.g., "news", "code", "chat")
        glitchling_id: Glitchling identifier
        gaggle_id: Gaggle identifier (if applicable)
        tokenizer_id: Tokenizer identifier
        text_before: Original text (optional, for debugging)
        text_after: Corrupted text (optional, for debugging)
        tokens_before: Token IDs before glitchling
        tokens_after: Token IDs after glitchling
        tokens_before_hash: SHA256 hash of token sequence (for dedup)
        tokens_after_hash: SHA256 hash of token sequence
        m: Length of before sequence
        n: Length of after sequence
        metrics: Dict of computed metric values
        context: Additional context/metadata
    """

    run_id: str
    observation_id: str
    input_id: str
    input_type: str
    glitchling_id: str
    tokenizer_id: str
    tokens_before: Sequence[int]
    tokens_after: Sequence[int]
    m: int  # len(tokens_before)
    n: int  # len(tokens_after)
    metrics: dict[str, float] = field(default_factory=dict)
    gaggle_id: str | None = None
    text_before: str | None = None
    text_after: str | None = None
    tokens_before_hash: str | None = None
    tokens_after_hash: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute derived fields."""
        # Compute hashes if not provided
        if self.tokens_before_hash is None:
            tokens_bytes = b"".join(
                t.to_bytes(4, "little", signed=True) for t in self.tokens_before
            )
            object.__setattr__(
                self, "tokens_before_hash", hashlib.sha256(tokens_bytes).hexdigest()[:16]
            )

        if self.tokens_after_hash is None:
            tokens_bytes = b"".join(t.to_bytes(4, "little", signed=True) for t in self.tokens_after)
            object.__setattr__(
                self, "tokens_after_hash", hashlib.sha256(tokens_bytes).hexdigest()[:16]
            )

    def to_dict(self, include_tokens: bool = False) -> dict[str, Any]:
        """Convert to dictionary for storage.

        Args:
            include_tokens: Include full token sequences (expensive for large datasets)

        Returns:
            Dictionary suitable for Parquet/JSON serialization
        """
        result = {
            "run_id": self.run_id,
            "observation_id": self.observation_id,
            "input_id": self.input_id,
            "input_type": self.input_type,
            "glitchling_id": self.glitchling_id,
            "gaggle_id": self.gaggle_id,
            "tokenizer_id": self.tokenizer_id,
            "m": self.m,
            "n": self.n,
            "tokens_before_hash": self.tokens_before_hash,
            "tokens_after_hash": self.tokens_after_hash,
            **{f"metric_{k}": v for k, v in self.metrics.items()},
        }

        # Optional fields
        if self.text_before is not None:
            result["text_before"] = self.text_before
        if self.text_after is not None:
            result["text_after"] = self.text_after

        # Include tokens if requested (expensive)
        if include_tokens:
            result["tokens_before"] = list(self.tokens_before)
            result["tokens_after"] = list(self.tokens_after)

        # Include context metadata
        for k, v in self.context.items():
            result[f"context_{k}"] = v

        return result


def create_parquet_schema() -> dict[str, str]:
    """Define Parquet schema for observations.

    Returns:
        Dictionary mapping column names to PyArrow types

    Note:
        Actual PyArrow schema creation happens in the writer.
        This is a reference schema for documentation.
    """
    return {
        # Identifiers
        "run_id": "string",
        "observation_id": "string",
        "input_id": "string",
        "input_type": "string",
        "glitchling_id": "string",
        "gaggle_id": "string",  # nullable
        "tokenizer_id": "string",
        # Sequence metadata
        "m": "int32",
        "n": "int32",
        "tokens_before_hash": "string",
        "tokens_after_hash": "string",
        # Optional text fields
        "text_before": "string",  # nullable
        "text_after": "string",  # nullable
        # Metrics (dynamic - added per metric)
        # "metric_ned.value": "float64",
        # "metric_lcsr.value": "float64",
        # ...
        # Context fields (dynamic)
        # "context_epsilon": "float64",
        # ...
    }


__all__ = [
    "RunManifest",
    "Observation",
    "create_parquet_schema",
]

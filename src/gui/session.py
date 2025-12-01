"""Session management for save/load functionality.

Handles serialization and deserialization of complete GUI session state
including glitchlings, tokenizers, parameters, and UI settings.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .theme import AVAILABLE_GLITCHLINGS

# Map glitchling names to classes for deserialization
GLITCHLING_MAP = {cls.__name__: cls for cls in AVAILABLE_GLITCHLINGS}


@dataclass
class SessionConfig:
    """Serializable session configuration."""

    # Glitchling configuration: list of (name, params) tuples
    glitchlings: List[Tuple[str, Dict[str, Any]]] = field(default_factory=list)

    # Tokenizer names
    tokenizers: List[str] = field(default_factory=list)

    # Core settings
    seed: int = 151
    auto_update: bool = True

    # Scan mode settings
    scan_mode: bool = False
    scan_count: int = 100

    # UI state
    diff_mode: str = "label"
    diff_tokenizer: str = "cl100k_base"

    # Optional: input text (can be large, so optional)
    input_text: str = ""
    include_input: bool = True

    # Metadata
    version: str = "1.0"
    name: str = ""
    description: str = ""


def session_to_dict(config: SessionConfig) -> Dict[str, Any]:
    """Convert session config to a JSON-serializable dictionary."""
    data = asdict(config)
    # Ensure glitchlings is a list of [name, params] for JSON
    data["glitchlings"] = [[name, params] for name, params in config.glitchlings]
    return data


def dict_to_session(data: Dict[str, Any]) -> SessionConfig:
    """Convert dictionary back to SessionConfig."""
    # Handle glitchlings format (list of [name, params])
    glitchlings_data = data.get("glitchlings", [])
    glitchlings = [(item[0], item[1]) for item in glitchlings_data]

    return SessionConfig(
        glitchlings=glitchlings,
        tokenizers=data.get("tokenizers", []),
        seed=data.get("seed", 151),
        auto_update=data.get("auto_update", True),
        scan_mode=data.get("scan_mode", False),
        scan_count=data.get("scan_count", 100),
        diff_mode=data.get("diff_mode", "label"),
        diff_tokenizer=data.get("diff_tokenizer", "cl100k_base"),
        input_text=data.get("input_text", ""),
        include_input=data.get("include_input", True),
        version=data.get("version", "1.0"),
        name=data.get("name", ""),
        description=data.get("description", ""),
    )


def save_session(config: SessionConfig, path: Path | str) -> None:
    """Save session configuration to a JSON file."""
    path = Path(path)
    data = session_to_dict(config)

    # Don't save input text if not requested
    if not config.include_input:
        data["input_text"] = ""

    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_session(path: Path | str) -> SessionConfig:
    """Load session configuration from a JSON file."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict_to_session(data)


def resolve_glitchlings(
    config: SessionConfig,
) -> List[Tuple[type, Dict[str, Any]]]:
    """Convert session glitchling names back to classes with parameters."""
    result: List[Tuple[type, Dict[str, Any]]] = []
    for name, params in config.glitchlings:
        cls = GLITCHLING_MAP.get(name)
        if cls is not None:
            result.append((cls, params))
    return result

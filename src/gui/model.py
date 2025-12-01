from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class ScanResult:
    """Results from a scan operation."""

    token_count_out: List[int] = field(default_factory=list)
    token_delta: List[int] = field(default_factory=list)
    jsd: List[float] = field(default_factory=list)
    ned: List[float] = field(default_factory=list)
    sr: List[float] = field(default_factory=list)
    char_count_out: List[int] = field(default_factory=list)


@dataclass
class SessionState:
    """Holds the application state."""

    input_text: str = ""
    output_text: str = ""
    seed: int = 151

    # Configuration
    enabled_glitchlings: List[Tuple[type, Dict[str, Any]]] = field(default_factory=list)
    enabled_tokenizers: List[str] = field(default_factory=list)

    # Multi-seed aggregation (for main transform)
    multi_seed_mode: bool = False
    multi_seed_count: int = 10

    # Dataset batch processing
    dataset_results: Dict[str, ScanResult] = field(default_factory=dict)
    dataset_running: bool = False
    dataset_total: int = 0
    dataset_processed: int = 0

    # UI State
    status_message: str = "Ready"
    status_color: str = "green"
    auto_update: bool = True
    diff_mode: str = "label"
    diff_tokenizer: str = "cl100k_base"

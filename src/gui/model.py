from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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

    # Scan state
    scan_mode: bool = False
    scan_count: int = 100
    scan_results: Dict[str, ScanResult] = field(default_factory=dict)
    scan_running: bool = False

    # UI State
    status_message: str = "Ready"
    status_color: str = "green"
    auto_update: bool = True
    diff_mode: str = "label"
    diff_tokenizer: str = "cl100k_base"

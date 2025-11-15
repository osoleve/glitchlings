"""Controller logic for the metrics TUI (textual-agnostic)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, cast

from glitchlings.zoo import (
    DEFAULT_GLITCHLING_NAMES,
    Glitchling,
    RushmoreMode,
    get_glitchling_class,
    parse_glitchling_spec,
)

from ...core.session import MetricsSession, SessionResult, TextTransformer
from ...core.tokenizers import (
    SimpleTokenizer,
    TokenizerAdapter,
    create_huggingface_adapter,
    create_tiktoken_adapter,
)

METRIC_LABEL_OVERRIDES: dict[str, str] = {
    "ned.value": "Edit Distance",
    "lcsr.value": "LCS %",
    "lr.ratio": "Length %",
    "pmr.value": "Position Match %",
    "jsdiv.value": "Jensen-Shannon Div.",
    "rord.value": "Rank Order",
}

DEFAULT_METRIC_KEYS: list[str] = [
    "ned.value",
    "lcsr.value",
    "pmr.value",
    "jsdiv.value",
    "rord.value",
    "lr.ratio",
]

IDENTITY_ALIASES = {"identity", "none", "noop", "passthrough"}

BUILTIN_TOKENIZERS: list[tuple[str, str]] = [
    ("Simple (whitespace)", "simple"),
    ("HF GPT-2", "hf:gpt2"),
    ("HF bert-base-uncased", "hf:bert-base-uncased"),
    ("tiktoken cl100k_base", "tiktoken:cl100k_base"),
]


def build_glitchling_pipeline(specs: Sequence[str]) -> tuple[str, TextTransformer]:
    """Create a callable that applies a glitchling gaggle described by ``specs``."""

    cleaned = [spec.strip() for spec in specs if spec and spec.strip()]
    if not cleaned:
        return ("identity", lambda text: text)

    glitchlings: list[Glitchling] = []
    display_parts: list[str] = []

    for spec in cleaned:
        lower = spec.lower()
        if lower in IDENTITY_ALIASES:
            display_parts.append("identity")
            continue

        glitchling = _instantiate_glitchling(spec)
        glitchlings.append(glitchling)
        display_parts.append(spec)

    if not glitchlings:
        return ("identity", lambda text: text)

    pipeline = list(glitchlings)

    def run(text: str, *, pipeline: list[Glitchling] = pipeline) -> str:
        result = text
        for glitch in pipeline:
            result = _apply_glitchling(glitch, result)
        return result

    return (" + ".join(display_parts), run)


def resolve_tokenizer_specs(specs: Sequence[str]) -> list[TokenizerAdapter]:
    """Instantiate tokenizers described by ``specs``."""
    if not specs:
        return [SimpleTokenizer()]

    adapters: list[TokenizerAdapter] = []
    for raw_spec in specs:
        spec = raw_spec.strip()
        if not spec or spec.lower() in {"simple", "default"}:
            adapters.append(SimpleTokenizer())
            continue

        if spec.startswith(("hf:", "huggingface:")):
            model_name = spec.split(":", 1)[1].strip()
            if not model_name:
                raise ValueError("HuggingFace tokenizer spec must include a model name.")
            try:
                adapters.append(create_huggingface_adapter(model_name))
            except ImportError as exc:
                raise ValueError(
                    "transformers is required for HuggingFace tokenizers. "
                    "Install with: pip install glitchlings[metrics-tokenizers]"
                ) from exc
            continue

        if spec.startswith(("tiktoken:", "tk:")):
            encoding = spec.split(":", 1)[1].strip()
            if not encoding:
                raise ValueError("tiktoken spec must include an encoding name.")
            try:
                adapters.append(create_tiktoken_adapter(encoding))
            except ImportError as exc:
                raise ValueError(
                    "tiktoken is required for OpenAI tokenizers. "
                    "Install with: pip install glitchlings[metrics-tokenizers]"
                ) from exc
            continue

        raise ValueError(f"Unknown tokenizer specification '{spec}'.")

    return adapters


@dataclass(slots=True)
class ControllerOptions:
    """Options for the TUI controller."""

    text: str
    glitchling_specs: Sequence[str] | None = None
    tokenizer_specs: Sequence[str] | None = None
    metric_keys: Sequence[str] | None = None
    input_type: str = "adhoc"


class MetricsTUIController:
    """Bridges user input, metrics session, and UI rendering."""

    def __init__(self, session: MetricsSession, options: ControllerOptions) -> None:
        self.session = session
        self.metric_keys = list(options.metric_keys or DEFAULT_METRIC_KEYS)
        self.text = options.text
        self.input_type = options.input_type

        initial_glitchlings = list(options.glitchling_specs or ["identity"])
        initial_tokenizers = list(options.tokenizer_specs or ["simple"])

        builtin_glitch_set = {name.lower() for name in DEFAULT_GLITCHLING_NAMES}
        self._selected_builtin_glitchlings: set[str] = {
            spec.strip().lower()
            for spec in initial_glitchlings
            if spec.strip().lower() in builtin_glitch_set
        }
        self._custom_glitchling_specs: list[str] = [
            spec.strip()
            for spec in initial_glitchlings
            if spec.strip() and spec.strip().lower() not in builtin_glitch_set
        ]

        builtin_tokenizer_set = {spec for _, spec in BUILTIN_TOKENIZERS}
        self._selected_builtin_tokenizers: set[str] = {
            spec.strip() for spec in initial_tokenizers if spec.strip() in builtin_tokenizer_set
        }
        if not self._selected_builtin_tokenizers:
            self._selected_builtin_tokenizers.add("simple")
        self._custom_tokenizer_specs: list[str] = [
            spec.strip()
            for spec in initial_tokenizers
            if spec.strip() and spec.strip() not in builtin_tokenizer_set
        ]

        self._result: SessionResult | None = None

    @property
    def result(self) -> SessionResult | None:
        return self._result

    # -------- Glitchlings --------
    def available_glitchlings(self) -> list[str]:
        return list(DEFAULT_GLITCHLING_NAMES)

    def is_glitchling_selected(self, name: str) -> bool:
        return name.lower() in self._selected_builtin_glitchlings

    def set_builtin_glitchling(self, name: str, selected: bool) -> None:
        key = name.lower()
        if selected:
            self._selected_builtin_glitchlings.add(key)
        else:
            self._selected_builtin_glitchlings.discard(key)
        self.session.clear_cache()

    def custom_glitchlings_text(self) -> str:
        return ", ".join(self._custom_glitchling_specs)

    def set_custom_glitchlings(
        self, raw: str | Sequence[str | Mapping[str, object]]
    ) -> None:
        specs = _coerce_custom_specs(raw)
        self._custom_glitchling_specs = specs
        self.session.clear_cache()

    def current_glitchling_specs(self) -> list[str]:
        specs = [
            name
            for name in self.available_glitchlings()
            if name.lower() in self._selected_builtin_glitchlings
        ]
        specs.extend(self._custom_glitchling_specs)
        return specs or ["identity"]

    def partition_custom_glitchlings(self) -> tuple[dict[str, dict[str, object]], list[str]]:
        """Split structured overrides from raw custom specs."""

        return _partition_custom_specs(self._custom_glitchling_specs)

    # -------- Tokenizers --------
    def available_tokenizers(self) -> list[tuple[str, str]]:
        return BUILTIN_TOKENIZERS

    def is_tokenizer_selected(self, spec: str) -> bool:
        return spec in self._selected_builtin_tokenizers

    def set_builtin_tokenizer(self, spec: str, selected: bool) -> None:
        if selected:
            self._selected_builtin_tokenizers.add(spec)
        else:
            self._selected_builtin_tokenizers.discard(spec)
        self.session.clear_cache()

    def custom_tokenizers_text(self) -> str:
        return ", ".join(self._custom_tokenizer_specs)

    def set_custom_tokenizers(self, raw: str) -> None:
        specs = _split_specs(raw)
        self._custom_tokenizer_specs = specs
        self.session.clear_cache()

    def selected_tokenizer_specs(self) -> list[str]:
        specs = [
            spec for _, spec in BUILTIN_TOKENIZERS if spec in self._selected_builtin_tokenizers
        ]
        specs.extend(self._custom_tokenizer_specs)
        return specs or ["simple"]

    # -------- Text & execution --------
    def update_text(self, text: str) -> None:
        self.text = text
        self.session.clear_cache()

    def refresh(self) -> SessionResult:
        glitchling_specs = self.current_glitchling_specs()
        glitchling_id, glitchling_fn = build_glitchling_pipeline(glitchling_specs)
        tokenizers = resolve_tokenizer_specs(self.selected_tokenizer_specs())

        result = self.session.compute_once(
            text_before=self.text,
            glitchling_fn=glitchling_fn,
            glitchling_id=glitchling_id,
            tokenizers=tokenizers,
            input_type=self.input_type,
        )
        self._result = result
        return result

    def metric_columns(self) -> list[str]:
        return ["Tokenizer", "Input Tokens", "Output Tokens", *self._metric_labels]

    def metric_rows(self) -> list[list[str]]:
        if not self._result:
            return []

        rows: list[list[str]] = []
        for observation in self._result.observations:
            row = [
                observation.tokenizer_id,
                str(len(observation.tokens_before)),
                str(len(observation.tokens_after)),
            ]
            for key in self.metric_keys:
                value = observation.metrics.get(key)
                row.append(self._format_value(value))
            rows.append(row)
        return rows

    def summary_text(self) -> str:
        if not self._result:
            return "Run metrics to view results."

        glitch_summary = " + ".join(self.current_glitchling_specs())
        tokenizer_summary = ", ".join(
            observation.tokenizer_id for observation in self._result.observations
        )
        return f"[b]Glitchlings:[/b] {glitch_summary}\n[b]Tokenizers:[/b] {tokenizer_summary}"

    @staticmethod
    def _format_value(value: float | None) -> str:
        if value is None:
            return "-"
        if not math.isfinite(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"

    @property
    def _metric_labels(self) -> list[str]:
        labels: list[str] = []
        for key in self.metric_keys:
            override = METRIC_LABEL_OVERRIDES.get(key)
            if override:
                labels.append(override)
                continue
            parts = re.split(r"[._]", key)
            if not parts:
                labels.append(key.title())
                continue
            head, *tail = parts
            label = head.upper()
            if tail:
                tail_label = " ".join(part.capitalize() for part in tail if part)
                if tail_label:
                    label = f"{label} {tail_label}"
            labels.append(label)
        return labels


def _instantiate_glitchling(spec: str) -> Glitchling:
    if "(" not in spec:
        glitchling_type = cast(type[Any], get_glitchling_class(spec))
        return cast(Glitchling, glitchling_type())

    glitchling = parse_glitchling_spec(spec)
    if not isinstance(glitchling, Glitchling):
        raise ValueError(f"Specification '{spec}' did not produce a glitchling.")
    return glitchling


def _apply_glitchling(glitchling: Glitchling, text: str) -> str:
    result = glitchling(text)
    if not isinstance(result, str):
        raise TypeError("Glitchling callables must return text.")
    return result


def _split_specs(raw: str) -> list[str]:
    if not raw:
        return []
    tokens = raw.replace("\n", ",").split(",")
    return [token.strip() for token in tokens if token.strip()]


def _coerce_custom_specs(
    raw: str | Sequence[str | Mapping[str, object]]
) -> list[str]:
    if isinstance(raw, str):
        return _split_specs(raw)
    specs: list[str] = []
    for entry in raw:
        if isinstance(entry, str):
            cleaned = entry.strip()
            if cleaned:
                specs.append(cleaned)
            continue
        specs.append(_format_structured_entry(entry))
    return specs


def _format_structured_entry(entry: Mapping[str, object]) -> str:
    value = entry.get("value") or entry.get("name")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Structured glitch entry is missing a name/value field.")
    params = entry.get("params")
    if not params:
        return value
    if not isinstance(params, Mapping):
        raise ValueError("Structured glitch entry params must be a mapping.")
    rendered = ", ".join(
        f"{key}={_format_glitch_param(value)}" for key, value in sorted(params.items())
    )
    return f"{value}({rendered})"


def _format_glitch_param(value: object) -> str:
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (float, int)):
        return repr(value)
    if isinstance(value, Mapping):
        inner = ", ".join(
            f"{key}: {_format_glitch_param(entry)}" for key, entry in sorted(value.items())
        )
        return "{" + inner + "}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        inner = ", ".join(_format_glitch_param(entry) for entry in value)
        return f"[{inner}]"
    if value is None:
        return "None"
    return repr(value)


def _partition_custom_specs(
    specs: Sequence[str],
) -> tuple[dict[str, dict[str, object]], list[str]]:
    structured: dict[str, dict[str, object]] = {}
    remainder: list[str] = []
    for spec in specs:
        parsed = _parse_structured_glitch_spec(spec)
        if parsed is None:
            remainder.append(spec)
            continue
        value, params = parsed
        if value in structured:
            remainder.append(spec)
            continue
        structured[value] = params
    return structured, remainder


def _parse_structured_glitch_spec(spec: str) -> tuple[str, dict[str, object]] | None:
    try:
        glitch = parse_glitchling_spec(spec)
    except ValueError:
        return None

    name = glitch.name.lower()
    params: dict[str, object] = {}
    if name in {"ekkokin", "scannequin"}:
        rate_value = glitch.kwargs.get("rate")
        if rate_value is not None:
            params["rate"] = float(rate_value)
    elif name == "rushmore":
        modes_value = glitch.kwargs.get("modes")
        modes = _modes_to_strings(modes_value)
        if modes:
            params["modes"] = modes
        rate_value = glitch.kwargs.get("rate")
        if rate_value is not None:
            params["rate"] = float(rate_value)
    else:
        return None

    if not params:
        return None
    return name, params


def _modes_to_strings(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, RushmoreMode):
        return [value.value]
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        modes: list[str] = []
        for entry in value:
            if isinstance(entry, RushmoreMode):
                modes.append(entry.value)
            else:
                modes.append(str(entry))
        return modes
    return [str(value)]


__all__ = [
    "ControllerOptions",
    "DEFAULT_METRIC_KEYS",
    "METRIC_LABEL_OVERRIDES",
    "MetricsTUIController",
    "build_glitchling_pipeline",
    "resolve_tokenizer_specs",
]

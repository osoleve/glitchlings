"""Controller logic for the metrics TUI (textual-agnostic)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence, cast

from glitchlings.zoo import (
    DEFAULT_GLITCHLING_NAMES,
    Glitchling,
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

    def set_custom_glitchlings(self, raw: str) -> None:
        specs = _split_specs(raw)
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
        return ["tokenizer"] + self.metric_keys

    def metric_rows(self) -> list[list[str]]:
        if not self._result:
            return []

        rows: list[list[str]] = []
        for observation in self._result.observations:
            row = [observation.tokenizer_id]
            for key in self.metric_keys:
                value = observation.metrics.get(key)
                row.append(self._format_value(value))
            rows.append(row)
        return rows

    def summary_text(self) -> str:
        if not self._result:
            return "Run metrics to view results."

        observation = self._result.observations[0]
        glitch_summary = " + ".join(self.current_glitchling_specs())
        tokenizer_summary = ", ".join(
            observation.tokenizer_id for observation in self._result.observations
        )
        return (
            f"[b]Glitchlings:[/b] {glitch_summary}\n"
            f"[b]Tokenizers:[/b] {tokenizer_summary}\n"
            f"[b]Input tokens:[/b] {len(observation.tokens_before)}\n"
            f"[b]Output tokens:[/b] {len(observation.tokens_after)}"
        )

    @staticmethod
    def _format_value(value: float | None) -> str:
        if value is None:
            return "-"
        if not math.isfinite(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"


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


__all__ = [
    "ControllerOptions",
    "DEFAULT_METRIC_KEYS",
    "MetricsTUIController",
    "build_glitchling_pipeline",
    "resolve_tokenizer_specs",
]

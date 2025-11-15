"""Tests for the metrics TUI controller utilities."""

from __future__ import annotations

from glitchlings.metrics.cli.tui.controller import (
    BUILTIN_TOKENIZERS,
    DEFAULT_METRIC_KEYS,
    METRIC_LABEL_OVERRIDES,
    ControllerOptions,
    MetricsTUIController,
    build_glitchling_pipeline,
    resolve_tokenizer_specs,
)
from glitchlings.metrics.core.session import MetricsSession


def test_build_glitchling_pipeline_identity() -> None:
    glitchling_id, fn = build_glitchling_pipeline(["identity"])
    assert glitchling_id == "identity"
    assert fn("sample") == "sample"


def test_build_glitchling_pipeline_multi() -> None:
    glitchling_id, fn = build_glitchling_pipeline(["typogre", "typogre(rate=0.1)"])
    assert "typogre" in glitchling_id
    output = fn("hello world")
    assert isinstance(output, str)
    assert output


def test_resolve_tokenizer_specs_defaults_to_simple() -> None:
    adapters = resolve_tokenizer_specs([])
    assert len(adapters) == 1
    assert adapters[0].name == "simple-whitespace"


def test_controller_refresh_populates_rows() -> None:
    options = ControllerOptions(
        text="hello world",
        glitchling_specs=["typogre", "identity"],
        tokenizer_specs=["simple"],
    )
    controller = MetricsTUIController(MetricsSession(), options)
    controller.refresh()

    rows = controller.metric_rows()
    assert rows
    assert rows[0][0] == "simple-whitespace"
    assert controller.metric_columns()[:3] == ["Tokenizer", "Input Tokens", "Output Tokens"]


def test_controller_tokenizer_selection_helpers() -> None:
    options = ControllerOptions(text="demo")
    controller = MetricsTUIController(MetricsSession(), options)
    label, spec = BUILTIN_TOKENIZERS[0]
    assert controller.is_tokenizer_selected(spec)
    controller.set_builtin_tokenizer(spec, False)
    # Simple tokenizer stays selected as the fallback choice.
    assert controller.selected_tokenizer_specs() == ["simple"]
    controller.set_custom_tokenizers("hf:gpt2")
    assert "hf:gpt2" in controller.selected_tokenizer_specs()


def test_controller_glitchling_selection_helpers() -> None:
    options = ControllerOptions(text="demo", glitchling_specs=["typogre"])
    controller = MetricsTUIController(MetricsSession(), options)
    assert controller.available_glitchlings()
    assert controller.is_glitchling_selected("typogre")
    controller.set_builtin_glitchling("typogre", False)
    assert controller.current_glitchling_specs() == ["identity"]
    controller.set_custom_glitchlings("typogre(rate=0.3)")
    assert "typogre(rate=0.3)" in controller.current_glitchling_specs()
    friendly = [
        METRIC_LABEL_OVERRIDES.get(key) or key.replace(".", " ").title()
        for key in DEFAULT_METRIC_KEYS
    ]
    expected = ["Tokenizer", "Input Tokens", "Output Tokens", *friendly]
    assert controller.metric_columns() == expected


def test_controller_structured_custom_glitchlings_roundtrip() -> None:
    controller = MetricsTUIController(MetricsSession(), ControllerOptions(text="demo"))
    payload: list[str | dict[str, object]] = [
        {"value": "ekkokin", "params": {"rate": 0.05}},
        {"value": "rushmore", "params": {"modes": ["delete", "swap"], "rate": 0.2}},
        "scannequin(rate=0.1)",
    ]
    controller.set_custom_glitchlings(payload)
    structured, remainder = controller.partition_custom_glitchlings()
    assert structured["ekkokin"]["rate"] == 0.05
    assert structured["rushmore"]["modes"] == ["delete", "swap"]
    assert structured["rushmore"]["rate"] == 0.2
    assert structured["scannequin"]["rate"] == 0.1
    assert remainder == []

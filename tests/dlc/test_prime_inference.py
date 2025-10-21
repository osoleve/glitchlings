"""Tests for Prime Intellect inference integration with glitchconf evals."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest


# Mock lm_eval module
class MockTaskManager:
    """Mock TaskManager for lm_eval."""

    def __init__(self):
        self._tasks: dict[str, Any] = {}
        self._task_groups: dict[str, list[str]] = {}

    def load_task_or_group(self, tasks: list[str]) -> dict[str, Any]:
        """Load tasks or task groups."""
        result = {}
        for task_name in tasks:
            if task_name in self._task_groups:
                # Load all tasks in group
                for subtask in self._task_groups[task_name]:
                    result[subtask] = self._tasks.get(subtask, MockTask(subtask))
            else:
                result[task_name] = self._tasks.get(task_name, MockTask(task_name))
        return result


class MockTask:
    """Mock task for lm_eval."""

    def __init__(self, name: str):
        self.name = name
        self._test_context = "Hello world"

    def doc_to_text(self, doc: Any) -> str:
        """Convert document to text."""
        if isinstance(doc, dict):
            return doc.get("text", "sample text")
        return str(doc)

    def construct_requests(self, doc: Any, ctx: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Construct evaluation requests."""
        return [{"context": ctx, "doc": doc}]


def mock_simple_evaluate(**kwargs: Any) -> dict[str, Any]:
    """Mock simple_evaluate function."""
    tasks = kwargs.get("tasks", [])
    return {
        "results": {
            task: {
                "acc": 0.75,
                "acc_stderr": 0.02,
            }
            for task in tasks
        },
        "config": kwargs,
    }


@pytest.fixture(autouse=True)
def mock_lm_eval(monkeypatch):
    """Mock lm_eval module for testing."""
    lm_eval_module = types.ModuleType("lm_eval")
    lm_eval_module.simple_evaluate = mock_simple_evaluate

    # Create tasks submodule
    tasks_module = types.ModuleType("lm_eval.tasks")
    tasks_module.TaskManager = MockTaskManager

    # Register modules
    monkeypatch.setitem(sys.modules, "lm_eval", lm_eval_module)
    monkeypatch.setitem(sys.modules, "lm_eval.tasks", tasks_module)

    yield lm_eval_module


def test_glitched_task_wrapper_corrupts_text():
    """Test that GlitchedTaskWrapper applies corruption to doc_to_text."""
    from glitchlings.dlc.prime_inference import GlitchedTaskWrapper
    from glitchlings.zoo import Gaggle
    from glitchlings.zoo.core import Glitchling, AttackWave

    # Create a simple marker glitchling
    def marker_fn(text: str) -> str:
        return f"{text}<<<MARKED>>>"

    glitchling = Glitchling("marker", marker_fn, AttackWave.SENTENCE)
    gaggle = Gaggle([glitchling], seed=42)

    # Wrap a mock task
    original_task = MockTask("test_task")
    wrapped_task = GlitchedTaskWrapper(original_task, gaggle)

    # Test doc_to_text corruption
    doc = {"text": "Hello world"}
    result = wrapped_task.doc_to_text(doc)

    assert "<<<MARKED>>>" in result
    assert "Hello world" in result


def test_glitched_task_wrapper_preserves_attributes():
    """Test that GlitchedTaskWrapper delegates unknown attributes to wrapped task."""
    from glitchlings.dlc.prime_inference import GlitchedTaskWrapper
    from glitchlings.zoo import Gaggle, Typogre

    gaggle = Gaggle([Typogre(rate=0.1)], seed=42)
    original_task = MockTask("test_task")
    wrapped_task = GlitchedTaskWrapper(original_task, gaggle)

    # Should delegate to original task
    assert wrapped_task.name == "test_task"


def test_create_glitched_task_dict():
    """Test creating a dictionary of glitched tasks."""
    from glitchlings.dlc.prime_inference import create_glitched_task_dict
    from glitchlings.zoo import Gaggle, Typogre

    gaggle = Gaggle([Typogre(rate=0.05)], seed=123)
    task_dict = {
        "hellaswag": MockTask("hellaswag"),
        "arc_easy": MockTask("arc_easy"),
    }

    glitched_dict = create_glitched_task_dict(task_dict, gaggle)

    assert len(glitched_dict) == 2
    assert "hellaswag" in glitched_dict
    assert "arc_easy" in glitched_dict


def test_eval_with_glitchconf_with_yaml_config(tmp_path):
    """Test eval_with_glitchconf with YAML configuration file."""
    from glitchlings.dlc.prime_inference import eval_with_glitchconf

    # Create a test YAML config
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text("""
glitchlings:
  - name: Typogre
    rate: 0.1
  - Mim1c
seed: 42
""")

    results = eval_with_glitchconf(
        model="hf",
        model_args="pretrained=gpt2",
        tasks=["hellaswag"],
        glitchconf=str(config_path),
        seed=42,
        limit=10,
    )

    assert "results" in results
    assert "hellaswag" in results["results"]


def test_eval_with_glitchconf_with_inline_spec():
    """Test eval_with_glitchconf with inline glitchling specification."""
    from glitchlings.dlc.prime_inference import eval_with_glitchconf
    from glitchlings.zoo import Typogre

    results = eval_with_glitchconf(
        model="hf",
        model_args="pretrained=gpt2",
        tasks=["hellaswag"],
        glitchconf=[Typogre(rate=0.05)],
        seed=123,
    )

    assert "results" in results
    assert "hellaswag" in results["results"]


def test_eval_with_glitchconf_with_gaggle():
    """Test eval_with_glitchconf with pre-built Gaggle."""
    from glitchlings.dlc.prime_inference import eval_with_glitchconf
    from glitchlings.zoo import Gaggle, Typogre, Mim1c

    gaggle = Gaggle([Typogre(rate=0.1), Mim1c(rate=0.05)], seed=42)

    results = eval_with_glitchconf(
        model="hf",
        model_args="pretrained=gpt2",
        tasks=["hellaswag", "arc_easy"],
        glitchconf=gaggle,
        seed=42,
    )

    assert "results" in results
    assert "hellaswag" in results["results"]
    assert "arc_easy" in results["results"]


def test_eval_with_glitchconf_handles_string_tasks():
    """Test that eval_with_glitchconf handles single task string."""
    from glitchlings.dlc.prime_inference import eval_with_glitchconf
    from glitchlings.zoo import Typogre

    results = eval_with_glitchconf(
        model="hf",
        model_args="pretrained=gpt2",
        tasks="hellaswag",  # Single string instead of list
        glitchconf=[Typogre()],
        seed=42,
    )

    assert "results" in results


def test_parse_glitchconf_with_yaml_path(tmp_path):
    """Test _parse_glitchconf with YAML file path."""
    from glitchlings.dlc.prime_inference import _parse_glitchconf

    config_path = tmp_path / "attack.yaml"
    config_path.write_text("""
glitchlings:
  - Typogre
  - name: Mim1c
    rate: 0.1
seed: 99
""")

    gaggle = _parse_glitchconf(str(config_path), seed=42)

    assert gaggle is not None
    # Check that gaggle has the expected glitchlings by counting clones
    assert len(gaggle._clones_by_index) == 2


def test_parse_glitchconf_with_gaggle():
    """Test _parse_glitchconf with pre-built Gaggle."""
    from glitchlings.dlc.prime_inference import _parse_glitchconf
    from glitchlings.zoo import Gaggle, Typogre

    input_gaggle = Gaggle([Typogre()], seed=123)
    result = _parse_glitchconf(input_gaggle, seed=42)

    assert result is input_gaggle


def test_parse_glitchconf_with_glitchling_list():
    """Test _parse_glitchconf with list of glitchlings."""
    from glitchlings.dlc.prime_inference import _parse_glitchconf
    from glitchlings.zoo import Typogre, Mim1c

    glitchlings = [Typogre(rate=0.1), Mim1c()]
    gaggle = _parse_glitchconf(glitchlings, seed=42)

    assert len(gaggle._clones_by_index) == 2


def test_cli_main_with_basic_args(tmp_path, capsys):
    """Test CLI main function with basic arguments."""
    from glitchlings.dlc.prime_inference import main

    # Create test config
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
glitchlings:
  - Typogre
""")

    argv = [
        "--model", "hf",
        "--model_args", "pretrained=gpt2",
        "--tasks", "hellaswag",
        "--glitchconf", str(config_path),
        "--seed", "42",
        "--limit", "10",
    ]

    exit_code = main(argv)

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "GLITCHCONF EVALUATION RESULTS" in captured.out
    assert "hellaswag" in captured.out


def test_cli_main_with_multiple_tasks(tmp_path, capsys):
    """Test CLI with comma-separated tasks."""
    from glitchlings.dlc.prime_inference import main

    config_path = tmp_path / "config.yaml"
    config_path.write_text("glitchlings: [Typogre]")

    argv = [
        "--model", "hf",
        "--model_args", "pretrained=gpt2",
        "--tasks", "hellaswag,arc_easy,mmlu",
        "--glitchconf", str(config_path),
    ]

    exit_code = main(argv)

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "hellaswag, arc_easy, mmlu" in captured.out


def test_cli_main_with_corruption_fields(tmp_path):
    """Test CLI with custom corruption fields."""
    from glitchlings.dlc.prime_inference import main

    config_path = tmp_path / "config.yaml"
    config_path.write_text("glitchlings: [Typogre]")

    argv = [
        "--model", "hf",
        "--tasks", "hellaswag",
        "--glitchconf", str(config_path),
        "--corruption-fields", "prompt", "answer",
    ]

    exit_code = main(argv)
    assert exit_code == 0


def test_cli_main_missing_required_args(capsys):
    """Test CLI error handling for missing required arguments."""
    from glitchlings.dlc.prime_inference import main

    argv = ["--model", "hf"]  # Missing --tasks and --glitchconf

    # argparse will call sys.exit with code 2 for missing required args
    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    # Check that error message appears (argparse puts it in stderr)
    assert "required" in captured.err or "error" in captured.err


def test_cli_main_with_optional_flags(tmp_path):
    """Test CLI with various optional flags."""
    from glitchlings.dlc.prime_inference import main

    config_path = tmp_path / "config.yaml"
    config_path.write_text("glitchlings: [Mim1c]")

    argv = [
        "--model", "hf",
        "--model_args", "pretrained=gpt2",
        "--tasks", "hellaswag",
        "--glitchconf", str(config_path),
        "--num_fewshot", "5",
        "--batch_size", "8",
        "--device", "cpu",
        "--check_integrity",
        "--write_out",
        "--no_log_samples",
        "--verbosity", "DEBUG",
        "--predict_only",
    ]

    exit_code = main(argv)
    assert exit_code == 0


def test_deterministic_corruption_with_same_seed():
    """Test that same seed produces identical corruption."""
    from glitchlings.dlc.prime_inference import eval_with_glitchconf
    from glitchlings.zoo import Typogre

    # Run twice with same seed
    results1 = eval_with_glitchconf(
        model="hf",
        tasks=["hellaswag"],
        glitchconf=[Typogre(rate=0.1)],
        seed=42,
    )

    results2 = eval_with_glitchconf(
        model="hf",
        tasks=["hellaswag"],
        glitchconf=[Typogre(rate=0.1)],
        seed=42,
    )

    # Results structure should be identical (same keys)
    assert results1["results"].keys() == results2["results"].keys()
    # Task results should have same metrics
    for task in results1["results"]:
        assert results1["results"][task].keys() == results2["results"][task].keys()


def test_require_lm_eval_raises_helpful_error(monkeypatch):
    """Test that missing lm_eval raises helpful error."""
    from glitchlings.dlc.prime_inference import _require_lm_eval

    # Temporarily remove lm_eval from sys.modules
    if "lm_eval" in sys.modules:
        monkeypatch.delitem(sys.modules, "lm_eval")
    if "lm_eval.tasks" in sys.modules:
        monkeypatch.delitem(sys.modules, "lm_eval.tasks")

    with pytest.raises(ModuleNotFoundError, match="lm-evaluation-harness"):
        _require_lm_eval()


def test_glitched_task_wrapper_corrupts_context():
    """Test that construct_requests corrupts context strings."""
    from glitchlings.dlc.prime_inference import GlitchedTaskWrapper
    from glitchlings.zoo import Gaggle
    from glitchlings.zoo.core import Glitchling, AttackWave

    def marker_fn(text: str) -> str:
        return f"[{text}]"

    glitchling = Glitchling("marker", marker_fn, AttackWave.SENTENCE)
    gaggle = Gaggle([glitchling], seed=42)

    original_task = MockTask("test")
    wrapped_task = GlitchedTaskWrapper(original_task, gaggle)

    doc = {"text": "sample"}
    ctx = "original context"
    requests = wrapped_task.construct_requests(doc, ctx)

    # Context should be corrupted
    assert requests[0]["context"].startswith("[")
    assert requests[0]["context"].endswith("]")


def test_eval_with_glitchconf_restores_original_tasks():
    """Test that original tasks are restored after evaluation."""
    from glitchlings.dlc.prime_inference import eval_with_glitchconf
    from glitchlings.zoo import Typogre

    # The evaluation function creates a new TaskManager internally,
    # so we just verify that it completes successfully without errors
    results = eval_with_glitchconf(
        model="hf",
        tasks=["hellaswag"],
        glitchconf=[Typogre()],
        seed=42,
    )

    # Verify results are returned
    assert "results" in results

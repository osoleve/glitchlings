"""Prime Intellect inference integration with glitchconf evaluation support.

This module provides integration with lm-evaluation-harness for running evaluations
with glitched inputs, enabling robust model testing under realistic text corruption.

Example:
    Run an evaluation with glitched prompts::

        $ glitchlings prime-eval \\
            --model hf \\
            --model_args pretrained=meta-llama/Llama-2-7b-hf \\
            --tasks hellaswag \\
            --glitchconf experiments/chaos.yaml \\
            --seed 42

    Or use programmatically::

        from glitchlings.dlc.prime_inference import eval_with_glitchconf

        results = eval_with_glitchconf(
            model="hf",
            model_args="pretrained=meta-llama/Llama-2-7b-hf",
            tasks=["hellaswag"],
            glitchconf="experiments/chaos.yaml",
            seed=42,
        )
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Protocol

from ..compat import require_datasets
from ..config import DEFAULT_ATTACK_SEED, build_gaggle, load_attack_config
from ..zoo import Gaggle, Glitchling


class _LMEvalModule(Protocol):
    """Protocol for lm_eval module interface."""

    def simple_evaluate(
        self,
        model: str | Any,
        model_args: str | None = None,
        tasks: list[str] | None = None,
        num_fewshot: int | None = None,
        batch_size: int | str | None = None,
        max_batch_size: int | None = None,
        device: str | None = None,
        use_cache: str | None = None,
        limit: float | int | None = None,
        check_integrity: bool = False,
        write_out: bool = False,
        log_samples: bool = True,
        gen_kwargs: str | None = None,
        task_manager: Any | None = None,
        verbosity: str = "INFO",
        predict_only: bool = False,
        random_seed: int = 0,
        numpy_random_seed: int = 1234,
        torch_random_seed: int = 1234,
        fewshot_random_seed: int = 1234,
    ) -> dict[str, Any]:
        ...


def _require_lm_eval(message: str | None = None) -> _LMEvalModule:
    """Import lm_eval or raise with helpful error message."""
    try:
        import lm_eval
    except ModuleNotFoundError as exc:
        default_msg = (
            "lm_eval (lm-evaluation-harness) is required for Prime inference integration. "
            "Install with: pip install lm-eval"
        )
        raise ModuleNotFoundError(message or default_msg) from exc
    return lm_eval  # type: ignore[return-value]


class GlitchedTaskWrapper:
    """Wraps lm_eval tasks to apply glitchling corruption to prompts.

    This wrapper intercepts document processing and applies configured glitchlings
    to corrupt text before it reaches the model, enabling evaluation of model
    robustness to realistic text perturbations.

    Args:
        task: The original lm_eval task instance
        gaggle: Gaggle of glitchlings to apply
        corruption_fields: List of field names to corrupt (default: ["query", "context", "question"])
    """

    def __init__(
        self,
        task: Any,
        gaggle: Gaggle,
        corruption_fields: list[str] | None = None,
    ):
        self._task = task
        self._gaggle = gaggle
        self._corruption_fields = corruption_fields or ["query", "context", "question"]

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped task."""
        return getattr(self._task, name)

    def doc_to_text(self, doc: Any) -> str:
        """Process document text with glitchling corruption."""
        original = self._task.doc_to_text(doc)
        return self._gaggle.corrupt(original)

    def construct_requests(self, doc: Any, ctx: Any, **kwargs: Any) -> Any:
        """Construct requests with corrupted context."""
        # Corrupt the context before constructing requests
        if isinstance(ctx, str):
            ctx = self._gaggle.corrupt(ctx)
        return self._task.construct_requests(doc, ctx, **kwargs)


def create_glitched_task_dict(
    task_dict: dict[str, Any],
    gaggle: Gaggle,
    corruption_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Wrap all tasks in task_dict with glitchling corruption.

    Args:
        task_dict: Dictionary mapping task names to task instances
        gaggle: Gaggle to apply for corruption
        corruption_fields: Optional list of field names to corrupt

    Returns:
        Dictionary with wrapped task instances
    """
    return {
        name: GlitchedTaskWrapper(task, gaggle, corruption_fields)
        for name, task in task_dict.items()
    }


def eval_with_glitchconf(
    model: str | Any,
    tasks: list[str] | str,
    glitchconf: str | Path | Gaggle | list[Glitchling] | Glitchling,
    *,
    model_args: str | None = None,
    num_fewshot: int | None = None,
    batch_size: int | str | None = None,
    max_batch_size: int | None = None,
    device: str | None = None,
    use_cache: str | None = None,
    limit: float | int | None = None,
    check_integrity: bool = False,
    write_out: bool = False,
    log_samples: bool = True,
    gen_kwargs: str | None = None,
    verbosity: str = "INFO",
    predict_only: bool = False,
    seed: int = DEFAULT_ATTACK_SEED,
    corruption_fields: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run lm_eval evaluation with glitchling corruption applied to inputs.

    This function wraps lm-evaluation-harness's simple_evaluate to enable
    deterministic text corruption during evaluation, useful for testing
    model robustness to realistic text perturbations.

    Args:
        model: Model name or instance (e.g., "hf" for HuggingFace)
        tasks: List of task names or single task name to evaluate
        glitchconf: Glitchling configuration (path to YAML, Gaggle, or glitchlings)
        model_args: Model arguments string (e.g., "pretrained=meta-llama/Llama-2-7b-hf")
        num_fewshot: Number of few-shot examples
        batch_size: Batch size for evaluation
        max_batch_size: Maximum batch size
        device: Device to run on (e.g., "cuda", "cpu")
        use_cache: Cache directory path
        limit: Limit number of examples (for debugging)
        check_integrity: Check data integrity
        write_out: Write outputs to file
        log_samples: Log individual samples
        gen_kwargs: Generation kwargs string
        verbosity: Logging verbosity level
        predict_only: Only generate predictions without scoring
        seed: Random seed for deterministic corruption
        corruption_fields: List of field names to corrupt
        **kwargs: Additional arguments passed to simple_evaluate

    Returns:
        Dictionary containing evaluation results

    Example:
        >>> results = eval_with_glitchconf(
        ...     model="hf",
        ...     model_args="pretrained=gpt2",
        ...     tasks=["hellaswag"],
        ...     glitchconf="experiments/chaos.yaml",
        ...     seed=42,
        ...     limit=10,
        ... )
    """
    lm_eval = _require_lm_eval()

    # Parse glitchconf into a Gaggle
    gaggle = _parse_glitchconf(glitchconf, seed=seed)

    # Normalize tasks to list
    if isinstance(tasks, str):
        tasks_list = [tasks]
    else:
        tasks_list = list(tasks)

    # Import task manager and get tasks
    task_manager = kwargs.pop("task_manager", None)
    if task_manager is None:
        from lm_eval.tasks import TaskManager
        task_manager = TaskManager()

    # Get task instances
    task_dict = task_manager.load_task_or_group(tasks_list)

    # Wrap tasks with glitchling corruption
    glitched_task_dict = create_glitched_task_dict(
        task_dict,
        gaggle,
        corruption_fields=corruption_fields,
    )

    # Replace task instances with glitched versions
    # We do this by temporarily modifying the task manager's registry
    original_tasks = {}
    for task_name, glitched_task in glitched_task_dict.items():
        if task_name in task_manager._tasks:
            original_tasks[task_name] = task_manager._tasks[task_name]
            task_manager._tasks[task_name] = glitched_task

    try:
        # Run evaluation with glitched tasks
        results = lm_eval.simple_evaluate(
            model=model,
            model_args=model_args,
            tasks=tasks_list,
            num_fewshot=num_fewshot,
            batch_size=batch_size,
            max_batch_size=max_batch_size,
            device=device,
            use_cache=use_cache,
            limit=limit,
            check_integrity=check_integrity,
            write_out=write_out,
            log_samples=log_samples,
            gen_kwargs=gen_kwargs,
            task_manager=task_manager,
            verbosity=verbosity,
            predict_only=predict_only,
            random_seed=seed,
            numpy_random_seed=seed,
            torch_random_seed=seed,
            fewshot_random_seed=seed,
            **kwargs,
        )
    finally:
        # Restore original tasks
        for task_name, original_task in original_tasks.items():
            task_manager._tasks[task_name] = original_task

    return results


def _parse_glitchconf(
    glitchconf: str | Path | Gaggle | list[Glitchling] | Glitchling,
    *,
    seed: int,
) -> Gaggle:
    """Parse glitchconf specification into a Gaggle."""
    from ..util.adapters import coerce_gaggle

    # If it's already a Gaggle, return it
    if isinstance(glitchconf, Gaggle):
        return glitchconf

    # If it's a path-like object, load attack config
    if isinstance(glitchconf, (str, Path)):
        path = Path(glitchconf)
        if path.exists() and path.suffix in {".yaml", ".yml"}:
            attack_config = load_attack_config(path)
            return build_gaggle(attack_config, seed_override=seed)

    # Otherwise, coerce to Gaggle
    return coerce_gaggle(glitchconf, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point that shadows lm_eval with --glitchconf support.

    This function provides a command-line interface compatible with lm_eval
    but adds support for the --glitchconf flag to enable deterministic
    text corruption during evaluation.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Run LM evaluation with glitchling corruption",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run hellaswag with chaos configuration
  glitchlings prime-eval --model hf \\
      --model_args pretrained=gpt2 \\
      --tasks hellaswag \\
      --glitchconf experiments/chaos.yaml

  # Run with specific seed for reproducibility
  glitchlings prime-eval --model hf \\
      --model_args pretrained=meta-llama/Llama-2-7b-hf \\
      --tasks hellaswag,arc_easy \\
      --glitchconf experiments/chaos.yaml \\
      --seed 42 \\
      --limit 100

  # Use inline glitchling specification
  glitchlings prime-eval --model hf \\
      --model_args pretrained=gpt2 \\
      --tasks hellaswag \\
      --glitchconf "Typogre(rate=0.1)" \\
      --seed 151
        """,
    )

    # Glitchconf-specific arguments
    parser.add_argument(
        "--glitchconf",
        type=str,
        required=True,
        help="Path to glitchling attack YAML config or inline glitchling spec",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_ATTACK_SEED,
        help=f"Random seed for deterministic corruption (default: {DEFAULT_ATTACK_SEED})",
    )
    parser.add_argument(
        "--corruption-fields",
        type=str,
        nargs="+",
        help="Fields to corrupt (default: query, context, question)",
    )

    # Standard lm_eval arguments
    parser.add_argument("--model", type=str, required=True, help="Model name")
    parser.add_argument("--model_args", type=str, help="Model arguments")
    parser.add_argument(
        "--tasks",
        type=str,
        required=True,
        help="Comma-separated list of tasks",
    )
    parser.add_argument("--num_fewshot", type=int, help="Number of few-shot examples")
    parser.add_argument("--batch_size", help="Batch size")
    parser.add_argument("--max_batch_size", type=int, help="Maximum batch size")
    parser.add_argument("--device", type=str, help="Device (cuda, cpu, etc.)")
    parser.add_argument("--use_cache", type=str, help="Cache directory")
    parser.add_argument("--limit", type=float, help="Limit number of examples")
    parser.add_argument(
        "--check_integrity",
        action="store_true",
        help="Check data integrity",
    )
    parser.add_argument("--write_out", action="store_true", help="Write outputs")
    parser.add_argument(
        "--no_log_samples",
        action="store_true",
        help="Don't log samples",
    )
    parser.add_argument("--gen_kwargs", type=str, help="Generation kwargs")
    parser.add_argument(
        "--verbosity",
        type=str,
        default="INFO",
        help="Logging verbosity",
    )
    parser.add_argument(
        "--predict_only",
        action="store_true",
        help="Only predict, don't score",
    )

    args = parser.parse_args(argv)

    # Parse tasks (comma-separated)
    tasks = [t.strip() for t in args.tasks.split(",")]

    # Convert batch_size if needed
    batch_size: int | str | None = args.batch_size
    if batch_size is not None and batch_size.isdigit():
        batch_size = int(batch_size)

    try:
        results = eval_with_glitchconf(
            model=args.model,
            tasks=tasks,
            glitchconf=args.glitchconf,
            model_args=args.model_args,
            num_fewshot=args.num_fewshot,
            batch_size=batch_size,
            max_batch_size=args.max_batch_size,
            device=args.device,
            use_cache=args.use_cache,
            limit=args.limit,
            check_integrity=args.check_integrity,
            write_out=args.write_out,
            log_samples=not args.no_log_samples,
            gen_kwargs=args.gen_kwargs,
            verbosity=args.verbosity,
            predict_only=args.predict_only,
            seed=args.seed,
            corruption_fields=args.corruption_fields,
        )

        # Print results summary
        print("\n" + "=" * 80)
        print("GLITCHCONF EVALUATION RESULTS")
        print("=" * 80)
        print(f"Glitchconf: {args.glitchconf}")
        print(f"Seed: {args.seed}")
        print(f"Tasks: {', '.join(tasks)}")
        print("=" * 80)

        # Print task results
        if "results" in results:
            for task_name, task_results in results["results"].items():
                print(f"\n{task_name}:")
                for metric, value in task_results.items():
                    if isinstance(value, float):
                        print(f"  {metric}: {value:.4f}")
                    else:
                        print(f"  {metric}: {value}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


__all__ = [
    "GlitchedTaskWrapper",
    "create_glitched_task_dict",
    "eval_with_glitchconf",
    "main",
]

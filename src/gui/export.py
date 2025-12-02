"""Export functionality for GUI session data.

Supports exporting to JSON, CSV, and Markdown formats.
"""

from __future__ import annotations

import csv
import io
import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from .model import ScanResult
from .session import SessionConfig, session_to_dict


@dataclass
class ExportOptions:
    """Options controlling what to include in exports."""

    include_config: bool = True
    include_input: bool = True
    include_output: bool = True
    include_metrics: bool = True
    include_scan_results: bool = True


@dataclass
class ExportData:
    """Complete data bundle for export."""

    config: SessionConfig
    input_text: str = ""
    output_text: str = ""
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    scan_results: Dict[str, ScanResult] = field(default_factory=dict)


def _infer_scan_count(scan_results: Dict[str, ScanResult]) -> int:
    """Best-effort scan count derived from stored results."""
    for result in scan_results.values():
        return len(result.token_delta)
    return 0


def export_to_json(data: ExportData, options: ExportOptions) -> str:
    """Export session data to JSON format."""
    result: Dict[str, Any] = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
    }

    if options.include_config:
        result["config"] = session_to_dict(data.config)

    if options.include_input:
        result["input_text"] = data.input_text

    if options.include_output:
        result["output_text"] = data.output_text

    if options.include_metrics and data.metrics:
        result["metrics"] = data.metrics

    if options.include_scan_results and data.scan_results:
        # Convert ScanResult dataclasses to dicts
        scan_data: Dict[str, Dict[str, List[Any]]] = {}
        for tok_name, scan_result in data.scan_results.items():
            scan_data[tok_name] = {
                "token_count_out": scan_result.token_count_out,
                "token_delta": scan_result.token_delta,
                "jsd": scan_result.jsd,
                "ned": scan_result.ned,
                "sr": scan_result.sr,
                "char_count_out": scan_result.char_count_out,
            }
        result["scan_results"] = scan_data

    return json.dumps(result, indent=2)


def export_to_csv(data: ExportData, options: ExportOptions) -> str:
    """Export metrics to CSV format.

    CSV export focuses on metrics data since it's tabular.
    Configuration is included as header comments.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write metadata as comments
    if options.include_config:
        glitchling_names = [name for name, _ in data.config.glitchlings]
        output.write(f"# Exported: {datetime.now().isoformat()}\n")
        output.write(f"# Seed: {data.config.seed}\n")
        output.write(f"# Glitchlings: {', '.join(glitchling_names)}\n")
        output.write(f"# Tokenizers: {', '.join(data.config.tokenizers)}\n")
        output.write("#\n")

    # Write metrics table
    if options.include_metrics and data.metrics:
        tokenizers = list(data.metrics.keys())
        writer.writerow(["Metric", *tokenizers])

        metric_names = ["token_delta", "jsd", "ned", "sr"]
        display_names = {
            "token_delta": "Token Delta",
            "jsd": "Jensen-Shannon Divergence",
            "ned": "Normalized Edit Distance",
            "sr": "Subsequence Retention",
        }

        for metric in metric_names:
            row = [display_names.get(metric, metric)]
            for tok in tokenizers:
                val = data.metrics[tok].get(metric, "-")
                row.append(str(val))
            writer.writerow(row)

    # Write scan results if available
    if options.include_scan_results and data.scan_results:
        output.write("\n# Scan Results (per seed statistics)\n")
        tokenizers = list(data.scan_results.keys())

        # Header with all tokenizer columns
        header = ["Metric", "Statistic"]
        for tok in tokenizers:
            header.append(tok)
        writer.writerow(header)

        # Write stats for each metric
        for metric_name in ["token_delta", "jsd", "ned", "sr"]:
            for stat in ["mean", "std", "min", "max"]:
                row = [metric_name, stat]
                for tok in tokenizers:
                    scan_result = data.scan_results[tok]
                    values = getattr(scan_result, metric_name, [])
                    if values:
                        import statistics

                        if stat == "mean":
                            val = statistics.mean(values)
                        elif stat == "std":
                            val = statistics.stdev(values) if len(values) > 1 else 0
                        elif stat == "min":
                            val = min(values)
                        else:
                            val = max(values)
                        row.append(f"{val:.4f}")
                    else:
                        row.append("-")
                writer.writerow(row)

    return output.getvalue()


def export_to_markdown(data: ExportData, options: ExportOptions) -> str:
    """Export session data to Markdown report format."""
    lines: List[str] = []

    lines.append("# Glitchlings Session Report")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")

    if options.include_config:
        lines.append("## Configuration")
        lines.append("")
        lines.append(f"- **Seed:** {data.config.seed}")
        lines.append(f"- **Auto Update:** {data.config.auto_update}")

        if data.config.glitchlings:
            lines.append("")
            lines.append("### Glitchlings")
            lines.append("")
            for name, params in data.config.glitchlings:
                if params:
                    param_str = ", ".join(f"`{k}={v}`" for k, v in sorted(params.items()))
                    lines.append(f"- **{name}**: {param_str}")
                else:
                    lines.append(f"- **{name}**: *(default parameters)*")

        if data.config.tokenizers:
            lines.append("")
            lines.append("### Tokenizers")
            lines.append("")
            for tok in data.config.tokenizers:
                lines.append(f"- `{tok}`")

        lines.append("")

    if options.include_input and data.input_text:
        lines.append("## Input Text")
        lines.append("")
        lines.append("```")
        lines.append(data.input_text)
        lines.append("```")
        lines.append("")

    if options.include_output and data.output_text:
        lines.append("## Output Text")
        lines.append("")
        lines.append("```")
        lines.append(data.output_text)
        lines.append("```")
        lines.append("")

    if options.include_metrics and data.metrics:
        lines.append("## Metrics")
        lines.append("")

        tokenizers = list(data.metrics.keys())
        header = "| Metric | " + " | ".join(tokenizers) + " |"
        separator = "|" + "|".join(["---"] * (len(tokenizers) + 1)) + "|"
        lines.append(header)
        lines.append(separator)

        metric_display = [
            ("token_delta", "Token Delta"),
            ("jsd", "Jensen-Shannon Divergence"),
            ("ned", "Normalized Edit Distance"),
            ("sr", "Subsequence Retention"),
        ]

        for key, display in metric_display:
            row = f"| {display} |"
            for tok in tokenizers:
                val = data.metrics[tok].get(key, "-")
                row += f" {val} |"
            lines.append(row)

        lines.append("")

    if options.include_scan_results and data.scan_results:
        lines.append("## Scan Results")
        lines.append("")
        scan_count = _infer_scan_count(data.scan_results)
        lines.append(f"*Scanned {scan_count} seeds starting from {data.config.seed}*")
        lines.append("")

        import statistics

        tokenizers = list(data.scan_results.keys())
        header = "| Metric | " + " | ".join(tokenizers) + " |"
        separator = "|" + "|".join(["---"] * (len(tokenizers) + 1)) + "|"
        lines.append(header)
        lines.append(separator)

        for metric_name, display_name in [
            ("token_delta", "Token Delta"),
            ("jsd", "JSD"),
            ("ned", "NED"),
            ("sr", "SR"),
        ]:
            row = f"| {display_name} |"
            for tok in tokenizers:
                values = getattr(data.scan_results[tok], metric_name, [])
                if values:
                    mean = statistics.mean(values)
                    std = statistics.stdev(values) if len(values) > 1 else 0
                    row += f" {mean:.3f} ± {std:.3f} |"
                else:
                    row += " - |"
            lines.append(row)

        lines.append("")

    return "\n".join(lines)


def export_session(
    data: ExportData,
    format: str,
    options: ExportOptions | None = None,
) -> str:
    """Export session data in the specified format.

    Args:
        data: Complete export data bundle
        format: One of 'json', 'csv', 'markdown'
        options: Export options (defaults used if None)

    Returns:
        Formatted export string
    """
    if options is None:
        options = ExportOptions()

    if format == "json":
        return export_to_json(data, options)
    elif format == "csv":
        return export_to_csv(data, options)
    elif format == "markdown":
        return export_to_markdown(data, options)
    else:
        raise ValueError(f"Unknown export format: {format}")


# ---------------------------------------------------------------------------
# Sweep Export Functions
# ---------------------------------------------------------------------------


@dataclass
class SweepExportOptions:
    """Options for sweep data exports."""

    include_metadata: bool = True
    include_raw_values: bool = False  # Include all per-seed values vs just aggregates


@dataclass
class SweepPoint:
    """Results for a single sweep point (imported from grid_sweep_panel)."""

    param_value: float
    metrics: Dict[str, Dict[str, List[float]]] = field(default_factory=dict)
    glitchling_names: List[str] = field(default_factory=list)
    parameter_name: str = ""

    # Backward compatibility property
    @property
    def glitchling_name(self) -> str:
        """Return first glitchling name for backward compatibility."""
        return self.glitchling_names[0] if self.glitchling_names else ""


def export_sweep_to_json(
    results: List[Any],
    options: SweepExportOptions | None = None,
) -> str:
    """Export sweep results to JSON format.

    Args:
        results: List of SweepPoint objects
        options: Export options

    Returns:
        JSON string
    """
    if options is None:
        options = SweepExportOptions()

    output: Dict[str, Any] = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "type": "sweep_results",
    }

    if not results:
        output["points"] = []
        return json.dumps(output, indent=2)

    # Extract metadata from first point
    first = results[0]
    if options.include_metadata:
        # Support both single glitchling_name and multiple glitchling_names
        glitchling_names = getattr(first, "glitchling_names", [])
        if not glitchling_names:
            # Fallback to old single name
            single_name = getattr(first, "glitchling_name", "")
            glitchling_names = [single_name] if single_name else []

        output["metadata"] = {
            "glitchlings": glitchling_names,
            "parameter": getattr(first, "parameter_name", ""),
            "point_count": len(results),
        }

    points: List[Dict[str, Any]] = []
    for point in results:
        point_data: Dict[str, Any] = {
            "param_value": getattr(point, "param_value", 0.0),
        }

        metrics_data: Dict[str, Any] = {}
        point_metrics = getattr(point, "metrics", {})
        for tok_name, tok_metrics in point_metrics.items():
            tok_data: Dict[str, Any] = {}
            for metric_name, values in tok_metrics.items():
                if not values:
                    tok_data[metric_name] = {"mean": None, "std": None}
                    continue

                mean_val = statistics.mean(values)
                std_val = statistics.stdev(values) if len(values) > 1 else 0.0
                tok_data[metric_name] = {
                    "mean": round(mean_val, 6),
                    "std": round(std_val, 6),
                }
                if options.include_raw_values:
                    tok_data[metric_name]["values"] = [round(v, 6) for v in values]

            metrics_data[tok_name] = tok_data

        point_data["metrics"] = metrics_data
        points.append(point_data)

    output["points"] = points
    return json.dumps(output, indent=2)


def export_sweep_to_csv(
    results: List[Any],
    options: SweepExportOptions | None = None,
) -> str:
    """Export sweep results to CSV format.

    Args:
        results: List of SweepPoint objects
        options: Export options

    Returns:
        CSV string
    """
    if options is None:
        options = SweepExportOptions()

    output = io.StringIO()
    writer = csv.writer(output)

    if not results:
        writer.writerow(["No sweep results to export"])
        return output.getvalue()

    # Metadata header comments
    first = results[0]
    if options.include_metadata:
        # Support both single glitchling_name and multiple glitchling_names
        glitchling_names = getattr(first, "glitchling_names", [])
        if not glitchling_names:
            single_name = getattr(first, "glitchling_name", "")
            glitchling_names = [single_name] if single_name else []

        output.write(f"# Exported: {datetime.now().isoformat()}\n")
        output.write(f"# Glitchlings: {', '.join(glitchling_names)}\n")
        output.write(f"# Parameter: {getattr(first, 'parameter_name', 'Unknown')}\n")
        output.write(f"# Points: {len(results)}\n")
        output.write("#\n")

    # Determine tokenizers from first point's metrics
    first_metrics = getattr(first, "metrics", {})
    tokenizers = list(first_metrics.keys()) if first_metrics else []

    # Build header row
    header = ["param_value"]
    for tok in tokenizers:
        for metric in ["jsd", "ned", "sr"]:
            header.append(f"{tok}_{metric}_mean")
            header.append(f"{tok}_{metric}_std")
    writer.writerow(header)

    # Data rows
    for point in results:
        row = [f"{getattr(point, 'param_value', 0.0):.4f}"]
        point_metrics = getattr(point, "metrics", {})

        for tok in tokenizers:
            tok_metrics = point_metrics.get(tok, {})
            for metric in ["jsd", "ned", "sr"]:
                values = tok_metrics.get(metric, [])
                if values:
                    mean_val = statistics.mean(values)
                    std_val = statistics.stdev(values) if len(values) > 1 else 0.0
                    row.append(f"{mean_val:.6f}")
                    row.append(f"{std_val:.6f}")
                else:
                    row.append("-")
                    row.append("-")

        writer.writerow(row)

    return output.getvalue()


def export_sweep_to_markdown(
    results: List[Any],
    options: SweepExportOptions | None = None,
) -> str:
    """Export sweep results to Markdown table format.

    Args:
        results: List of SweepPoint objects
        options: Export options

    Returns:
        Markdown string
    """
    if options is None:
        options = SweepExportOptions()

    lines: List[str] = []

    lines.append("# Parameter Sweep Results")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")

    if not results:
        lines.append("*No sweep results to export.*")
        return "\n".join(lines)

    first = results[0]
    if options.include_metadata:
        # Support both single glitchling_name and multiple glitchling_names
        glitchling_names = getattr(first, "glitchling_names", [])
        if not glitchling_names:
            single_name = getattr(first, "glitchling_name", "")
            glitchling_names = [single_name] if single_name else []

        lines.append("## Configuration")
        lines.append("")
        lines.append(f"- **Glitchlings:** {', '.join(glitchling_names)}")
        lines.append(f"- **Parameter:** {getattr(first, 'parameter_name', 'Unknown')}")
        lines.append(f"- **Sweep Points:** {len(results)}")
        lines.append("")

    # Build table
    first_metrics = getattr(first, "metrics", {})
    tokenizers = list(first_metrics.keys()) if first_metrics else []

    if not tokenizers:
        lines.append("*No metrics available.*")
        return "\n".join(lines)

    lines.append("## Results")
    lines.append("")

    # Table header
    header_parts = ["Parameter"]
    for tok in tokenizers:
        header_parts.append(f"{tok} JSD")
        header_parts.append(f"{tok} NED")
        header_parts.append(f"{tok} SR")

    lines.append("| " + " | ".join(header_parts) + " |")
    lines.append("|" + "|".join(["---"] * len(header_parts)) + "|")

    # Table rows
    for point in results:
        row_parts = [f"{getattr(point, 'param_value', 0.0):.3f}"]
        point_metrics = getattr(point, "metrics", {})

        for tok in tokenizers:
            tok_metrics = point_metrics.get(tok, {})
            for metric in ["jsd", "ned", "sr"]:
                values = tok_metrics.get(metric, [])
                if values:
                    mean_val = statistics.mean(values)
                    std_val = statistics.stdev(values) if len(values) > 1 else 0.0
                    row_parts.append(f"{mean_val:.4f} ± {std_val:.4f}")
                else:
                    row_parts.append("-")

        lines.append("| " + " | ".join(row_parts) + " |")

    lines.append("")
    return "\n".join(lines)


def export_sweep(
    results: List[Any],
    format: str,
    options: SweepExportOptions | None = None,
) -> str:
    """Export sweep results in the specified format.

    Args:
        results: List of SweepPoint objects from grid sweep
        format: One of 'json', 'csv', 'markdown'
        options: Export options (defaults used if None)

    Returns:
        Formatted export string
    """
    if options is None:
        options = SweepExportOptions()

    if format == "json":
        return export_sweep_to_json(results, options)
    elif format == "csv":
        return export_sweep_to_csv(results, options)
    elif format == "markdown":
        return export_sweep_to_markdown(results, options)
    else:
        raise ValueError(f"Unknown export format: {format}")

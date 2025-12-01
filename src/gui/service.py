import statistics
import threading
from typing import Any, Callable, Dict, List, Sequence, Tuple

from glitchlings.attack import (
    jensen_shannon_divergence,
    normalized_edit_distance,
    subsequence_retention,
)
from glitchlings.attack.tokenization import resolve_tokenizer
from glitchlings.zoo import Gaggle

from .model import ScanResult

DEFAULT_TOKENIZER = "cl100k_base"


class GlitchlingService:
    """Service layer for Glitchlings business logic."""

    def transform_text(
        self, input_text: str, glitchlings_config: List[Tuple[type[Any], Dict[str, Any]]], seed: int
    ) -> Tuple[str, List[str]]:
        """
        Transform text using the specified glitchlings.
        Returns the output text and a list of glitchling names used.
        """
        if not input_text:
            return "", []

        if not glitchlings_config:
            return input_text, []

        glitchlings = []
        names = []
        for cls, params in glitchlings_config:
            instance = cls(seed=seed, **params)
            glitchlings.append(instance)
            names.append(cls.__name__)

        gaggle = Gaggle(glitchlings, seed=seed)
        output = gaggle.corrupt(input_text)

        return str(output), names

    def calculate_metrics(
        self, input_text: str, output_text: str, tokenizers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate metrics for the transformation.
        Returns a dictionary of metrics per tokenizer.
        """
        results = {}

        if not tokenizers:
            tokenizers = [DEFAULT_TOKENIZER]

        for tok_name in tokenizers:
            tok_results = {"token_delta": "-", "jsd": "-", "ned": "-", "sr": "-"}

            try:
                tok = resolve_tokenizer(tok_name)
                if not tok:
                    results[tok_name] = tok_results
                    continue

                tokens_in, ids_in = tok.encode(input_text)

                if output_text:
                    tokens_out, ids_out = tok.encode(output_text)

                    # Token Delta
                    delta = len(ids_out) - len(ids_in)
                    tok_results["token_delta"] = f"{'+' if delta > 0 else ''}{delta}"

                    # Metrics
                    if tokens_in and tokens_out:
                        try:
                            jsd = jensen_shannon_divergence(tokens_in, tokens_out)
                            tok_results["jsd"] = f"{jsd:.4f}"
                        except Exception:
                            pass

                        try:
                            ned = normalized_edit_distance(tokens_in, tokens_out)
                            tok_results["ned"] = f"{ned:.4f}"
                        except Exception:
                            pass

                        try:
                            sr = subsequence_retention(tokens_in, tokens_out)
                            tok_results["sr"] = f"{sr:.4f}"
                        except Exception:
                            pass
                else:
                    # Just input stats if needed, but for now we return empty metrics
                    pass

                results[tok_name] = tok_results

            except Exception:
                results[tok_name] = tok_results

        return results

    def run_scan(
        self,
        input_text: str,
        glitchlings_config: List[Tuple[type[Any], Dict[str, Any]]],
        base_seed: int,
        scan_count: int,
        tokenizers: List[str],
        progress_callback: Callable[[int, int], None],
        completion_callback: Callable[[Dict[str, ScanResult], List[str]], None],
        check_cancel: Callable[[], bool],
    ) -> None:
        """Run scan in a background thread."""
        thread = threading.Thread(
            target=self._scan_worker,
            args=(
                input_text,
                glitchlings_config,
                base_seed,
                scan_count,
                tokenizers,
                progress_callback,
                completion_callback,
                check_cancel,
            ),
            daemon=True,
        )
        thread.start()

    def _scan_worker(
        self,
        input_text: str,
        enabled: List[Tuple[type[Any], Dict[str, Any]]],
        base_seed: int,
        scan_count: int,
        tokenizers: List[str],
        progress_callback: Callable[[int, int], None],
        completion_callback: Callable[[Dict[str, ScanResult], List[str]], None],
        check_cancel: Callable[[], bool],
    ) -> None:
        """Worker thread logic for scan mode."""
        if not tokenizers:
            tokenizers = [DEFAULT_TOKENIZER]

        # Resolve tokenizers once
        resolved_toks: Dict[str, Any] = {}
        for tok_name in tokenizers:
            try:
                resolved_toks[tok_name] = resolve_tokenizer(tok_name)
            except Exception:
                resolved_toks[tok_name] = None

        # Pre-encode input text
        input_tokens: Dict[str, List[str]] = {}
        for tok_name, tok in resolved_toks.items():
            if tok:
                try:
                    tokens, _ = tok.encode(input_text)
                    input_tokens[tok_name] = tokens
                except Exception:
                    input_tokens[tok_name] = []
            else:
                input_tokens[tok_name] = []

        # Initialize results storage
        results: Dict[str, ScanResult] = {tok: ScanResult() for tok in tokenizers}

        names = [cls.__name__ for cls, _ in enabled]

        for i in range(scan_count):
            if check_cancel():
                break

            seed = base_seed + i

            try:
                # Create glitchling instances with this seed
                glitchlings = []
                for cls, params in enabled:
                    instance = cls(seed=seed, **params)
                    glitchlings.append(instance)

                # Create gaggle and corrupt
                gaggle = Gaggle(glitchlings, seed=seed)
                output = gaggle.corrupt(input_text)
                output_str = str(output)

                # Calculate metrics for each tokenizer
                for tok_name in tokenizers:
                    tok = resolved_toks.get(tok_name)
                    if not tok or not input_tokens.get(tok_name):
                        continue

                    try:
                        out_tokens, out_ids = tok.encode(output_str)
                        in_tokens = input_tokens[tok_name]

                        res = results[tok_name]
                        res.token_count_out.append(len(out_ids))
                        res.token_delta.append(len(out_ids) - len(in_tokens))
                        res.char_count_out.append(len(output_str))

                        # Calculate divergence metrics
                        if in_tokens and out_tokens:
                            try:
                                jsd_val = jensen_shannon_divergence(in_tokens, out_tokens)
                                if isinstance(jsd_val, (int, float)):
                                    res.jsd.append(float(jsd_val))
                            except Exception:
                                pass

                            try:
                                ned_val = normalized_edit_distance(in_tokens, out_tokens)
                                if isinstance(ned_val, (int, float)):
                                    res.ned.append(float(ned_val))
                            except Exception:
                                pass

                            try:
                                sr_val = subsequence_retention(in_tokens, out_tokens)
                                if isinstance(sr_val, (int, float)):
                                    res.sr.append(float(sr_val))
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

            # Update progress
            if (i + 1) % max(1, scan_count // 100) == 0 or i == scan_count - 1:
                progress_callback(i + 1, scan_count)

        completion_callback(results, names)

    def format_scan_metrics(
        self, results: Dict[str, ScanResult], metrics: Sequence[str] | None = None
    ) -> List[Tuple[str, List[str]]]:
        """Format scan or batch results for display."""
        formatted_rows: List[Tuple[str, List[str]]] = []
        tokenizers = list(results.keys())
        metric_order = list(metrics) if metrics else ["token_delta", "jsd", "ned", "sr"]
        display_names = {
            "token_delta": "Token Delta",
            "jsd": "Jensen-Shannon Divergence",
            "ned": "Normalized Edit Distance",
            "sr": "Subsequence Retention",
            "token_count_out": "Token Count (out)",
            "char_count_out": "Character Count (out)",
        }

        def fmt_stats(values: Sequence[float | int]) -> str:
            if not values:
                return "-"
            numbers = [float(value) for value in values]
            mean = statistics.mean(numbers)
            if len(numbers) > 1:
                std = statistics.stdev(numbers)
                return f"{mean:.3f} +/- {std:.3f}"
            return f"{mean:.3f}"

        for metric_name in metric_order:
            formatted_rows.append(
                (
                    display_names.get(metric_name, metric_name),
                    [fmt_stats(getattr(results[tok], metric_name, [])) for tok in tokenizers],
                )
            )

        return formatted_rows

    def process_dataset(
        self,
        samples: List[str],
        glitchlings_config: List[Tuple[type[Any], Dict[str, Any]]],
        base_seed: int,
        tokenizers: List[str],
        progress_callback: Callable[[int, int], None],
        completion_callback: Callable[[Dict[str, ScanResult], List[str], int, int], None],
        check_cancel: Callable[[], bool],
    ) -> None:
        """Run glitchlings across a dataset in a background thread."""
        thread = threading.Thread(
            target=self._dataset_worker,
            args=(
                samples,
                glitchlings_config,
                base_seed,
                tokenizers,
                progress_callback,
                completion_callback,
                check_cancel,
            ),
            daemon=True,
        )
        thread.start()

    def _dataset_worker(
        self,
        samples: List[str],
        enabled: List[Tuple[type[Any], Dict[str, Any]]],
        base_seed: int,
        tokenizers: List[str],
        progress_callback: Callable[[int, int], None],
        completion_callback: Callable[[Dict[str, ScanResult], List[str], int, int], None],
        check_cancel: Callable[[], bool],
    ) -> None:
        """Worker thread that processes each dataset sample."""
        if not tokenizers:
            tokenizers = [DEFAULT_TOKENIZER]

        total_samples = len(samples)
        if total_samples == 0:
            completion_callback({}, [], 0, 0)
            return

        resolved_toks: Dict[str, Any] = {}
        for tok_name in tokenizers:
            try:
                resolved_toks[tok_name] = resolve_tokenizer(tok_name)
            except Exception:
                resolved_toks[tok_name] = None

        results: Dict[str, ScanResult] = {tok: ScanResult() for tok in tokenizers}
        names = [cls.__name__ for cls, _ in enabled]

        processed = 0
        progress_stride = max(1, total_samples // 100)

        for idx, sample in enumerate(samples):
            if check_cancel():
                break

            seed = base_seed + idx

            try:
                glitchlings = []
                for cls, params in enabled:
                    glitchlings.append(cls(seed=seed, **params))

                if glitchlings:
                    gaggle = Gaggle(glitchlings, seed=seed)
                    output_text = str(gaggle.corrupt(sample))
                else:
                    output_text = sample
            except Exception:
                output_text = sample

            for tok_name in tokenizers:
                tok = resolved_toks.get(tok_name)
                if not tok:
                    continue

                try:
                    input_tokens, input_ids = tok.encode(sample)
                    output_tokens, output_ids = tok.encode(output_text)
                except Exception:
                    continue

                res = results[tok_name]
                res.token_count_out.append(len(output_ids))
                res.token_delta.append(len(output_ids) - len(input_ids))
                res.char_count_out.append(len(output_text))

                if input_tokens and output_tokens:
                    try:
                        jsd_val = jensen_shannon_divergence(input_tokens, output_tokens)
                        if isinstance(jsd_val, (int, float)):
                            res.jsd.append(float(jsd_val))
                    except Exception:
                        pass

                    try:
                        ned_val = normalized_edit_distance(input_tokens, output_tokens)
                        if isinstance(ned_val, (int, float)):
                            res.ned.append(float(ned_val))
                    except Exception:
                        pass

                    try:
                        sr_val = subsequence_retention(input_tokens, output_tokens)
                        if isinstance(sr_val, (int, float)):
                            res.sr.append(float(sr_val))
                    except Exception:
                        pass

            processed += 1
            if (idx + 1) % progress_stride == 0 or idx == total_samples - 1:
                progress_callback(processed, total_samples)

        completion_callback(results, names, total_samples, processed)

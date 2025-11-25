"""
Example script demonstrating the usage of the Attack submodule to compare
corruptions using different tokenizers and metrics.
"""

import importlib.util
from typing import Any, List, Tuple

from glitchlings import SAMPLE_TEXT
from glitchlings.attack import Attack, Tokenizer
from glitchlings.zoo import Typogre

HAS_TIKTOKEN = importlib.util.find_spec("tiktoken") is not None


def main() -> None:
    print("=== Glitchlings Attack Comparison Report ===\n")

    # Use a subset of sample text for readability
    text = SAMPLE_TEXT[:500]
    print(f"Original Text ({len(text)} chars):\n{text[:100]}...\n")

    # Initialize a glitchling (Typogre)
    # We use a fixed seed for reproducibility in the glitchling itself,
    # though Attack wraps it in a Gaggle which also manages seeds.
    typogre = Typogre(rate=0.05, seed=42)

    # 1. Attack using Default Whitespace Tokenizer
    print("-" * 60)
    print("Running Attack with Whitespace Tokenizer")
    print("-" * 60)

    attack_ws = Attack([typogre], tokenizer=None)
    result_ws = attack_ws.run(text)
    print_report(result_ws)

    # 2. Attack using Tiktoken (if available) or Char Tokenizer
    print("\n" + "-" * 60)
    if HAS_TIKTOKEN:
        model = "cl100k_base"
        print(f"Running Attack with Tiktoken ({model})")
        print("-" * 60)
        attack_tt = Attack([typogre], tokenizer=model)
        result_tt = attack_tt.run(text)
        print_report(result_tt)
    else:
        print("Running Attack with Character Tokenizer (Tiktoken not found)")
        print("-" * 60)

        class CharTokenizer(Tokenizer):
            def encode(self, text: str) -> Tuple[List[str], List[int]]:
                return list(text), [ord(c) for c in text]

            def decode(self, tokens: List[str]) -> str:
                return "".join(tokens)

        attack_char = Attack([typogre], tokenizer=CharTokenizer())
        result_char = attack_char.run(text)
        print_report(result_char)


def print_report(result: Any) -> None:
    print(f"Tokenizer Info: {result.tokenizer_info}")
    print(f"Input Tokens:  {len(result.input_tokens)}")
    print(f"Output Tokens: {len(result.output_tokens)}")

    print("\nMetrics:")
    for metric_name, value in result.metrics.items():
        print(f"  {metric_name:<25}: {value:.6f}")

    print("\nSample Token Differences (First 10):")
    # Simple side-by-side of first few tokens
    limit = 10
    in_toks = result.input_tokens[:limit]
    out_toks = result.output_tokens[:limit]

    print(f"  {'Input':<20} | {'Output':<20}")
    print(f"  {'-' * 20} | {'-' * 20}")
    for i in range(max(len(in_toks), len(out_toks))):
        in_t = repr(in_toks[i]) if i < len(in_toks) else ""
        out_t = repr(out_toks[i]) if i < len(out_toks) else ""
        print(f"  {in_t:<20} | {out_t:<20}")
    print("...")


if __name__ == "__main__":
    main()

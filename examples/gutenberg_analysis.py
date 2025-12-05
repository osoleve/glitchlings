#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "glitchlings[attack,gutenberg]",
# ]
# ///
"""Example: Using Project Gutenberg books with tokenizer analysis tools.

This script demonstrates how to:
1. Fetch books from Project Gutenberg via the GlitchenbergAPI
2. Use book excerpts as input for SeedSweep, GridSearch, and TokenizerComparison
3. Analyze how different corruption settings affect literary text

Usage:
    uv run examples/gutenberg_analysis.py

Or with manual installation:
    pip install glitchlings[attack,gutenberg]
    python examples/gutenberg_analysis.py
"""

from __future__ import annotations

import importlib.util
import sys

# Check for required dependencies
HAS_GUTENBERG = importlib.util.find_spec("gutenberg") is not None
HAS_TIKTOKEN = importlib.util.find_spec("tiktoken") is not None

if not HAS_GUTENBERG:
    print("Error: py-gutenberg is required for this example.")
    print("Install it with: pip install py-gutenberg")
    sys.exit(1)

from gutenberg import GutenbergAPI  # noqa: E402, I001

from glitchlings import Mim1c, Rushmore, Typogre  # noqa: E402
from glitchlings.attack import GridSearch, SeedSweep, TokenizerComparison  # noqa: E402


# Famous book IDs from Project Gutenberg
BOOK_IDS = {
    "pride_and_prejudice": 1342,
    "moby_dick": 2701,
    "frankenstein": 84,
    "alice_in_wonderland": 11,
    "dracula": 345,
}


def fetch_book_excerpt(book_id: int, max_chars: int = 1000) -> tuple[str, str]:
    """Fetch a book excerpt from Project Gutenberg.

    Args:
        book_id: The Gutenberg book ID.
        max_chars: Maximum characters to extract.

    Returns:
        Tuple of (title, excerpt text).
    """
    api = GutenbergAPI()
    book = api.get_book(book_id)
    text = book.get_text()

    # Skip the Gutenberg header (usually ends with "***")
    start_marker = "***"
    start_idx = text.find(start_marker)
    if start_idx != -1:
        # Find the end of the header section
        header_end = text.find("\n\n", start_idx + len(start_marker))
        if header_end != -1:
            text = text[header_end:].strip()

    # Get a clean excerpt
    excerpt = text[:max_chars]
    # Try to end at a sentence boundary
    last_period = excerpt.rfind(".")
    if last_period > max_chars // 2:
        excerpt = excerpt[: last_period + 1]

    return book.title, excerpt


def demo_seed_sweep(text: str, title: str) -> None:
    """Demonstrate SeedSweep with book text."""
    print("\n" + "=" * 70)
    print("SEED SWEEP ANALYSIS")
    print("=" * 70)
    print(f"Book: {title}")
    print(f"Text length: {len(text)} characters")

    # Use whitespace tokenizer if tiktoken not available
    tokenizer = "cl100k_base" if HAS_TIKTOKEN else None

    sweep = SeedSweep(
        Typogre(rate=0.03),
        tokenizer=tokenizer,
    )

    # Sweep across 20 seeds to see variance in corruption
    result = sweep.run(text, seeds=range(20))
    print("\n" + result.summary(show_seeds=5))

    # Show some insights
    print("\nKey Insights:")
    jsd_stats = result.aggregate_stats.get("jensen_shannon_divergence", {})
    if jsd_stats:
        print(f"  - JSD variance (std): {jsd_stats.get('std', 0):.4f}")
        print(f"  - JSD range: {jsd_stats.get('min', 0):.4f} - {jsd_stats.get('max', 0):.4f}")


def demo_grid_search(text: str, title: str) -> None:
    """Demonstrate GridSearch with book text."""
    print("\n" + "=" * 70)
    print("GRID SEARCH ANALYSIS")
    print("=" * 70)
    print(f"Book: {title}")
    print("Searching for optimal Typogre rate...")

    tokenizer = "cl100k_base" if HAS_TIKTOKEN else None

    grid = GridSearch(
        Typogre,
        param_grid={
            "rate": [0.01, 0.02, 0.03, 0.05, 0.08, 0.10],
        },
        tokenizer=tokenizer,
        seed=42,
    )

    # Find the rate that produces a target level of edit distance
    result = grid.run(
        text,
        rank_by="normalized_edit_distance",
        minimize=True,  # Lower edit distance = less corruption
    )

    print("\n" + result.summary(show_top=6))

    # Show recommendation
    if result.best_point:
        print("\nRecommendation:")
        ned = result.best_point.metrics.get("normalized_edit_distance", 0)
        print(f"  For minimal corruption, use rate={result.best_point.params['rate']}")
        print(f"  This produces ~{ned:.1%} character-level changes")


def demo_tokenizer_comparison(text: str, title: str) -> None:
    """Demonstrate TokenizerComparison with book text."""
    print("\n" + "=" * 70)
    print("TOKENIZER COMPARISON")
    print("=" * 70)
    print(f"Book: {title}")

    if not HAS_TIKTOKEN:
        print("Skipping tokenizer comparison (tiktoken not installed)")
        print("Install with: pip install tiktoken")
        return

    compare = TokenizerComparison(
        Typogre(rate=0.05),
        tokenizers=["cl100k_base", "o200k_base", "p50k_base"],
        seed=42,
    )

    result = compare.run(text)
    print("\n" + result.summary(show_tokens=5))

    # Highlight differences
    print("\nTokenizer Insights:")
    for entry in result.entries:
        token_count = len(entry.tokens)
        ned = entry.metrics.get("normalized_edit_distance", 0)
        print(f"  {entry.tokenizer_name}: {token_count} tokens, NED={ned:.4f}")


def demo_multi_glitchling_comparison(text: str, title: str) -> None:
    """Compare different glitchlings on the same text."""
    print("\n" + "=" * 70)
    print("MULTI-GLITCHLING COMPARISON")
    print("=" * 70)
    print(f"Book: {title}")
    print("Comparing: Typogre vs Mim1c vs Rushmore")

    tokenizer = "cl100k_base" if HAS_TIKTOKEN else None

    glitchlings = [
        ("Typogre (typos)", Typogre(rate=0.03)),
        ("Mim1c (homoglyphs)", Mim1c(rate=0.03)),
        ("Rushmore (word ops)", Rushmore(rate=0.02)),
    ]

    print("\nResults:")
    print("-" * 60)

    for name, glitchling in glitchlings:
        sweep = SeedSweep(glitchling, tokenizer=tokenizer)
        result = sweep.run(text, seeds=range(10))

        jsd = result.aggregate_stats.get("jensen_shannon_divergence", {})
        ned = result.aggregate_stats.get("normalized_edit_distance", {})

        print(f"\n{name}:")
        print(f"  JSD:  mean={jsd.get('mean', 0):.4f}, std={jsd.get('std', 0):.4f}")
        print(f"  NED:  mean={ned.get('mean', 0):.4f}, std={ned.get('std', 0):.4f}")


def main() -> None:
    print("=" * 70)
    print("GLITCHLINGS + PROJECT GUTENBERG ANALYSIS")
    print("=" * 70)

    # Fetch a book excerpt
    book_id = BOOK_IDS["pride_and_prejudice"]
    print(f"\nFetching book #{book_id} from Project Gutenberg...")

    try:
        title, excerpt = fetch_book_excerpt(book_id, max_chars=800)
    except Exception as e:
        print(f"Error fetching book: {e}")
        print("\nUsing fallback sample text...")
        title = "Sample Text"
        excerpt = (
            "It is a truth universally acknowledged, that a single man in "
            "possession of a good fortune, must be in want of a wife. However "
            "little known the feelings or views of such a man may be on his "
            "first entering a neighbourhood, this truth is so well fixed in "
            "the minds of the surrounding families, that he is considered as "
            "the rightful property of some one or other of their daughters."
        )

    print(f"\nBook: {title}")
    print(f"Excerpt ({len(excerpt)} chars):")
    print("-" * 40)
    print(excerpt[:200] + "..." if len(excerpt) > 200 else excerpt)
    print("-" * 40)

    # Run the demos
    demo_seed_sweep(excerpt, title)
    demo_grid_search(excerpt, title)
    demo_tokenizer_comparison(excerpt, title)
    demo_multi_glitchling_comparison(excerpt, title)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()

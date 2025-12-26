"""
Example script demonstrating the usage of the Glitchlings NeMo DataDesigner plugin.

This example shows how to use Glitchlings as a column generator in NeMo DataDesigner
pipelines for text corruption and augmentation.

Requirements:
    pip install glitchlings pandas
    # For full DataDesigner integration:
    pip install data-designer glitchlings-nemo
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import NamedTemporaryFile

# Check for optional dependencies
HAS_PANDAS = importlib.util.find_spec("pandas") is not None
HAS_DATA_DESIGNER = importlib.util.find_spec("data_designer") is not None


def demo_standalone_usage() -> None:
    """Demonstrate standalone DataFrame corruption without DataDesigner."""
    if not HAS_PANDAS:
        print("Skipping standalone demo (pandas not installed)")
        return

    import pandas as pd

    from glitchlings.dlc.nemo import corrupt_dataframe

    print("=" * 60)
    print("Standalone DataFrame Corruption (no DataDesigner required)")
    print("=" * 60)

    # Create sample data
    df = pd.DataFrame(
        {
            "prompt": [
                "What is the capital of France?",
                "Explain quantum entanglement in simple terms.",
                "Write a haiku about programming.",
            ],
            "category": ["geography", "science", "creative"],
        }
    )

    print("\nOriginal DataFrame:")
    print(df.to_string(index=False))

    # Example 1: Simple single glitchling
    print("\n--- Example 1: Single Glitchling (Typogre) ---")
    result = corrupt_dataframe(df, "typogre", column="prompt", seed=42)
    print(result[["prompt"]].to_string(index=False))

    # Example 2: Multiple glitchlings with parameters
    print("\n--- Example 2: Multiple Glitchlings ---")
    result = corrupt_dataframe(
        df,
        ["Typogre(rate=0.03)", "Mim1c(rate=0.02)"],
        column="prompt",
        seed=42,
    )
    print(result[["prompt"]].to_string(index=False))

    # Example 3: Output to different column
    print("\n--- Example 3: Output to Different Column ---")
    result = corrupt_dataframe(
        df,
        "typogre",
        column="prompt",
        output_column="corrupted_prompt",
        seed=42,
    )
    print(result[["prompt", "corrupted_prompt"]].to_string(index=False))

    # Example 4: Using Auggie fluent builder
    print("\n--- Example 4: Using Auggie Builder ---")
    from glitchlings import Auggie

    auggie = Auggie(seed=404).typo(rate=0.02).confusable(rate=0.01).homophone(rate=0.02)

    result = corrupt_dataframe(df, auggie, column="prompt", seed=42)
    print(result[["prompt"]].to_string(index=False))

    # Example 5: Using pre-constructed Gaggle
    print("\n--- Example 5: Using Pre-constructed Gaggle ---")
    from glitchlings import Gaggle, Mim1c, Typogre

    gaggle = Gaggle([Typogre(rate=0.02), Mim1c(rate=0.01)], seed=404)
    result = corrupt_dataframe(df, gaggle, column="prompt", seed=42)
    print(result[["prompt"]].to_string(index=False))


def demo_yaml_config() -> None:
    """Demonstrate using YAML configuration files."""
    if not HAS_PANDAS:
        print("\nSkipping YAML config demo (pandas not installed)")
        return

    import pandas as pd

    from glitchlings.dlc.nemo import corrupt_dataframe

    print("\n" + "=" * 60)
    print("YAML Configuration")
    print("=" * 60)

    # Create a temporary YAML config
    yaml_content = """
# Glitchlings attack configuration
seed: 404
glitchlings:
  - name: Typogre
    rate: 0.02
  - name: Mim1c
    rate: 0.01
  - name: Wherewolf
    rate: 0.03
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        config_path = Path(f.name)

    try:
        df = pd.DataFrame({"text": ["The quick brown fox jumps over the lazy dog."]})

        print(f"\nUsing config from: {config_path}")
        print(f"Config content:\n{yaml_content}")

        result = corrupt_dataframe(df, config_path, column="text", seed=42)
        print(f"Original: {df['text'].iloc[0]}")
        print(f"Corrupted: {result['text'].iloc[0]}")
    finally:
        config_path.unlink()


def demo_childproofing_haystacks() -> None:
    """Demonstrate childproofing haystacks for long context retrieval.

    This example shows how to use an answer column to construct inclusion masks
    that target known "needles" in needle-in-a-haystack evaluations, breaking
    their surface patterns to force models to rely on approximate retrieval and
    semantic understanding rather than exact pattern matching.

    The key insight: the needle is there on purpose, so let's break it.

    Strategies:
    1. Use the answer column to build inclusion patterns dynamically
    2. Corrupt needles with high rate (break exact matching patterns)
    3. Corrupt haystack with lower rate (add realistic noise floor)

    This is useful for testing whether models truly understand context or are
    just memorizing surface patterns of evaluation needle texts.
    """
    if not HAS_PANDAS:
        print("\n" + "=" * 60)
        print("Childproofing Haystacks (requires pandas)")
        print("=" * 60)
        print("\nSkipping demo (pandas not installed)")
        return

    import re

    import pandas as pd

    from glitchlings import Gaggle, Mim1c, Typogre, Wherewolf

    print("\n" + "=" * 60)
    print("Childproofing Haystacks: Long Context Retrieval")
    print("=" * 60)
    print("\nGoal: Break surface patterns of needles to test semantic retrieval")

    # Sample haystack with embedded needles - no tags, just natural text
    # The "answer" column contains the needle text for ground truth
    df = pd.DataFrame(
        {
            "text": [
                "The quarterly report shows stable growth across all sectors. "
                "Revenue increased by 12% compared to last year. "
                "The secret code for the vault is blue-elephant-42. "
                "Market conditions remain favorable for expansion.",
                "Weather patterns indicate a mild winter ahead. "
                "Agricultural forecasts are optimistic. "
                "The password to access the system is cardinal-mountain-99. "
                "Supply chain logistics have improved significantly.",
                "The research team published their findings last week. "
                "Initial peer review was positive. "
                "The answer to the security question is purple-tiger-17. "
                "Funding for the next phase has been approved.",
            ],
            "answer": [
                "The secret code for the vault is blue-elephant-42.",
                "The password to access the system is cardinal-mountain-99.",
                "The answer to the security question is purple-tiger-17.",
            ],
        }
    )

    print("\n--- Original Data ---")
    for i, row in df.iterrows():
        print(f"  Needle {i}: {row['answer']}")
        print(f"    (embedded in {len(row['text'])} chars of haystack)")

    # Helper: build inclusion pattern from answer column
    def needle_pattern(answer: str) -> str:
        """Escape answer text to use as regex inclusion pattern."""
        return re.escape(answer)

    # Strategy 1: Corrupt only needles (break exact pattern matching)
    print("\n--- Strategy 1: Corrupt Needles Only ---")
    print("    Uses answer column to build inclusion mask")
    print("    Forces approximate retrieval; exact string match will fail")

    for i, row in df.iterrows():
        pattern = needle_pattern(row["answer"])
        needle_corruptor = Typogre(
            rate=0.4,  # High rate on needles
            seed=42 + i,
            include_only_patterns=[pattern],
        )
        gaggle = Gaggle([needle_corruptor], seed=100)
        result = gaggle.corrupt(row["text"])

        # Extract the corrupted needle region
        original_pos = row["text"].find(row["answer"])
        corrupted_needle = result[original_pos : original_pos + len(row["answer"])]
        print(f"  Original:  {row['answer']}")
        print(f"  Corrupted: {corrupted_needle}")
        print()

    # Strategy 2: Corrupt haystack only, preserve needles (noise floor)
    print("--- Strategy 2: Corrupt Haystack Only (Noise Floor) ---")
    print("    Excludes needle using answer column pattern")
    print("    Adds realistic noise; needle remains exact for baseline")

    for i, row in df.iterrows():
        pattern = needle_pattern(row["answer"])
        haystack_corruptor = Typogre(
            rate=0.15,
            seed=43 + i,
            exclude_patterns=[pattern],  # Preserve needle completely
        )
        gaggle = Gaggle([haystack_corruptor], seed=100)
        result = gaggle.corrupt(row["text"])

        # Verify needle preserved
        if row["answer"] in result:
            snippet = result[:60].replace(row["answer"], f"<<{row['answer']}>>")
            print(f"  Sample {i}: Needle preserved in noisy haystack")
            print(f"    Preview: {snippet}...")
        else:
            print(f"  Sample {i}: WARNING - needle was modified")
        print()

    # Strategy 3: Full childproofing with heterogeneous masks
    print("--- Strategy 3: Full Childproofing (Per-Row Processing) ---")
    print("    Needle: heavy corruption (typos + confusables + homophones)")
    print("    Haystack: light corruption (realistic noise)")

    results = []
    for i, row in df.iterrows():
        pattern = needle_pattern(row["answer"])

        # Heavy corruption on needle using multiple glitchlings
        needle_typo = Typogre(
            rate=0.3,
            seed=42,
            include_only_patterns=[pattern],
        )
        needle_confuse = Mim1c(
            rate=0.2,
            seed=43,
            include_only_patterns=[pattern],
        )
        needle_homophone = Wherewolf(
            rate=0.3,
            seed=44,
            include_only_patterns=[pattern],
        )

        # Light corruption on haystack (excludes needle)
        haystack_typo = Typogre(
            rate=0.05,
            seed=45,
            exclude_patterns=[pattern],
        )

        gaggle = Gaggle(
            [needle_typo, needle_confuse, needle_homophone, haystack_typo],
            seed=100,
        )

        result = gaggle.corrupt(row["text"])
        results.append(result)

        # Show the corrupted needle
        original_pos = row["text"].find(row["answer"])
        corrupted_region = result[original_pos : original_pos + len(row["answer"]) + 10]
        print(f"  Original needle:    {row['answer']}")
        print(f"  Childproofed:       {corrupted_region.strip()}")
        print()

    # Verification: exact match should fail
    print("--- Verification: Exact Match Failure ---")
    for i, (row, result) in enumerate(zip(df.iterrows(), results)):
        _, row = row
        exact_match = row["answer"] in result
        print(f"  Sample {i}: Exact needle match = {exact_match} (should be False)")

    print("\n--- Use Case: Needle Retrieval Testing ---")
    print("    1. Model must find needle despite surface pattern corruption")
    print("    2. Exact string matching will fail (by design)")
    print("    3. Success requires semantic understanding of needle content")
    print("    4. Measures true retrieval capability vs pattern memorization")


def demo_datadesigner_integration() -> None:
    """Demonstrate full DataDesigner integration."""
    if not HAS_DATA_DESIGNER:
        print("\n" + "=" * 60)
        print("DataDesigner Integration (requires data-designer package)")
        print("=" * 60)
        print("\nSkipping DataDesigner demo (data-designer not installed)")
        print("Install with: pip install data-designer glitchlings-nemo")
        print("\nExample code would look like:")
        print(
            """
from data_designer import DataDesignerConfigBuilder
from glitchlings.dlc.nemo import GlitchlingColumnConfig

builder = DataDesignerConfigBuilder()

# Add corrupted version of prompt column
builder.add_column(
    GlitchlingColumnConfig(
        name="corrupted_prompt",
        source_column="prompt",
        glitchlings=["Typogre(rate=0.02)", "Mim1c(rate=0.01)"],
        seed=404,
    )
)

# Build and run the data generation pipeline
config = builder.build()
# ... continue with DataDesigner workflow
"""
        )
        return

    # If data-designer is available, show actual usage
    from data_designer import DataDesignerConfigBuilder

    from glitchlings.dlc.nemo import GlitchlingColumnConfig

    print("\n" + "=" * 60)
    print("DataDesigner Integration")
    print("=" * 60)

    builder = DataDesignerConfigBuilder()
    builder.add_column(
        GlitchlingColumnConfig(
            name="corrupted_prompt",
            source_column="prompt",
            glitchlings=["Typogre(rate=0.02)", "Mim1c(rate=0.01)"],
            seed=404,
        )
    )

    print("\nDataDesigner config created successfully!")
    print("Column generator: glitchlings")
    print("Source: prompt -> Output: corrupted_prompt")


def main() -> None:
    """Run all demonstration examples."""
    print("=" * 60)
    print("Glitchlings NeMo DataDesigner Plugin Demo")
    print("=" * 60)

    demo_standalone_usage()
    demo_yaml_config()
    demo_childproofing_haystacks()
    demo_datadesigner_integration()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

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

    This example shows how to use heterogeneous masks to break surface patterns
    of known "needles" in needle-in-a-haystack evaluations, forcing models to
    rely on approximate retrieval and semantic understanding rather than exact
    pattern matching.

    The key insight: the needle is there on purpose, so let's break it.

    Strategies:
    1. Corrupt needles with high rate (break exact matching patterns)
    2. Corrupt haystack with lower rate (add realistic noise floor)
    3. Preserve structural markers (maintain retrievability by semantics)

    This is useful for testing whether models truly understand context or are
    just memorizing surface patterns of evaluation needle texts.
    """
    if not HAS_PANDAS:
        print("\n" + "=" * 60)
        print("Childproofing Haystacks (requires pandas)")
        print("=" * 60)
        print("\nSkipping demo (pandas not installed)")
        return

    import pandas as pd

    from glitchlings import Gaggle, Mim1c, Typogre, Wherewolf

    print("\n" + "=" * 60)
    print("Childproofing Haystacks: Long Context Retrieval")
    print("=" * 60)
    print("\nGoal: Break surface patterns of needles to test semantic retrieval")

    # Sample haystack with embedded needle using structural markers
    df = pd.DataFrame(
        {
            "text": [
                "[CONTEXT]The quarterly report shows stable growth across all sectors. "
                "Revenue increased by 12% compared to last year.[/CONTEXT] "
                "[NEEDLE]The secret code for the vault is blue-elephant-42.[/NEEDLE] "
                "[CONTEXT]Market conditions remain favorable for expansion.[/CONTEXT]",
                "[CONTEXT]Weather patterns indicate a mild winter ahead. "
                "Agricultural forecasts are optimistic.[/CONTEXT] "
                "[NEEDLE]The password to access the system is cardinal-mountain-99.[/NEEDLE] "
                "[CONTEXT]Supply chain logistics have improved significantly.[/CONTEXT]",
                "[CONTEXT]The research team published their findings last week. "
                "Initial peer review was positive.[/CONTEXT] "
                "[NEEDLE]The answer to the security question is purple-tiger-17.[/NEEDLE] "
                "[CONTEXT]Funding for the next phase has been approved.[/CONTEXT]",
            ]
        }
    )

    print("\n--- Original Data (with needles) ---")
    for i, row in df.iterrows():
        # Show just the needle portion for clarity
        import re

        needle = re.search(r"\[NEEDLE\](.*?)\[/NEEDLE\]", row["text"])
        if needle:
            print(f"  Needle {i}: {needle.group(1)}")

    # Strategy 1: Corrupt only needles (break exact pattern matching)
    print("\n--- Strategy 1: Corrupt Needles Only ---")
    print("    Forces approximate retrieval; exact string match will fail")
    needle_corruptor = Typogre(
        rate=0.4,  # High rate on needles
        seed=42,
        include_only_patterns=[r"\[NEEDLE\].*?\[/NEEDLE\]"],
        exclude_patterns=[r"\[/?NEEDLE\]"],  # Preserve structural tags
    )
    gaggle_needles = Gaggle([needle_corruptor], seed=100)

    for i, row in df.iterrows():
        result = gaggle_needles.corrupt(row["text"])
        import re

        needle = re.search(r"\[NEEDLE\](.*?)\[/NEEDLE\]", result)
        if needle:
            print(f"  Corrupted needle {i}: {needle.group(1)}")

    # Strategy 2: Corrupt haystack only, preserve needles (noise floor)
    print("\n--- Strategy 2: Corrupt Haystack Only (Noise Floor) ---")
    print("    Adds realistic noise; needle remains exact for baseline")
    haystack_corruptor = Typogre(
        rate=0.15,  # Lower rate for realistic noise
        seed=43,
        exclude_patterns=[
            r"\[NEEDLE\].*?\[/NEEDLE\]",  # Preserve needle completely
        ],
    )
    gaggle_haystack = Gaggle([haystack_corruptor], seed=100)

    for i, row in df.iterrows():
        result = gaggle_haystack.corrupt(row["text"])
        # Show a snippet of corrupted context
        import re

        context = re.search(r"\[CONTEXT\](.*?)\[/CONTEXT\]", result)
        if context:
            snippet = context.group(1)[:50] + "..."
            print(f"  Corrupted context {i}: {snippet}")

    # Strategy 3: Heterogeneous masks - full childproofing
    print("\n--- Strategy 3: Full Childproofing (Heterogeneous Masks) ---")
    print("    Needle: heavy corruption (typos + confusables + homophones)")
    print("    Haystack: light corruption (realistic noise)")
    print("    Tags: preserved (structural markers for evaluation)")

    # Heavy corruption on needles using multiple glitchlings
    needle_typo = Typogre(
        rate=0.3,
        seed=42,
        include_only_patterns=[r"\[NEEDLE\].*?\[/NEEDLE\]"],
        exclude_patterns=[r"\[/?NEEDLE\]"],
    )
    needle_confuse = Mim1c(
        rate=0.2,
        seed=43,
        include_only_patterns=[r"\[NEEDLE\].*?\[/NEEDLE\]"],
        exclude_patterns=[r"\[/?NEEDLE\]"],
    )
    needle_homophone = Wherewolf(
        rate=0.3,
        seed=44,
        include_only_patterns=[r"\[NEEDLE\].*?\[/NEEDLE\]"],
        exclude_patterns=[r"\[/?NEEDLE\]"],
    )

    # Light corruption on haystack
    haystack_typo = Typogre(
        rate=0.05,
        seed=45,
        exclude_patterns=[
            r"\[NEEDLE\].*?\[/NEEDLE\]",
            r"\[/?CONTEXT\]",
            r"\[/?NEEDLE\]",
        ],
    )

    # Combine into single gaggle with heterogeneous masks
    gaggle_full = Gaggle(
        [needle_typo, needle_confuse, needle_homophone, haystack_typo],
        seed=100,
    )

    print(f"\n    Heterogeneous masks detected: {gaggle_full._has_heterogeneous_masks()}")
    print(f"    Number of mask groups: {len(gaggle_full._group_by_masks())}")

    for i, row in df.iterrows():
        result = gaggle_full.corrupt(row["text"])
        import re

        needle = re.search(r"\[NEEDLE\](.*?)\[/NEEDLE\]", result)
        if needle:
            print(f"  Childproofed needle {i}: {needle.group(1)}")

    # Verify structural markers are preserved
    print("\n--- Verification: Structural Marker Preservation ---")
    for i, row in df.iterrows():
        result = gaggle_full.corrupt(row["text"])
        has_needle_tags = "[NEEDLE]" in result and "[/NEEDLE]" in result
        has_context_tags = "[CONTEXT]" in result and "[/CONTEXT]" in result
        if has_needle_tags and has_context_tags:
            print(f"  Sample {i}: All structural markers preserved")
        else:
            print(f"  Sample {i}: WARNING - markers corrupted: {result[:80]}...")

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

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


def demo_label_leakage_prevention() -> None:
    """Demonstrate preventing label leakage in multilabel classification.

    This example shows how to use heterogeneous masks to create a learning
    curriculum where:
    1. Labels are corrupted with high rate (to test robustness to label noise)
    2. Content is corrupted with lower rate (for difficulty scaling)
    3. System prompts are never corrupted (to maintain instruction clarity)

    This is useful for training models that must learn from noisy labels
    while avoiding label leakage where the model memorizes label patterns.
    """
    if not HAS_PANDAS:
        print("\n" + "=" * 60)
        print("Label Leakage Prevention (requires pandas)")
        print("=" * 60)
        print("\nSkipping demo (pandas not installed)")
        return

    import pandas as pd

    from glitchlings import Gaggle, Typogre

    print("\n" + "=" * 60)
    print("Label Leakage Prevention for Multilabel Classification")
    print("=" * 60)

    # Sample multilabel classification data with structured format
    df = pd.DataFrame(
        {
            "text": [
                "[SYSTEM]Classify[/SYSTEM] The movie was [LABEL]positive[/LABEL] great.",
                "[SYSTEM]Classify[/SYSTEM] A [LABEL]negative[/LABEL] experience overall.",
                "[SYSTEM]Classify[/SYSTEM] It was [LABEL]neutral[/LABEL] but informative.",
            ]
        }
    )

    print("\n--- Original Data ---")
    for _, row in df.iterrows():
        print(f"  {row['text']}")

    # Strategy 1: Corrupt only labels (test label noise robustness)
    print("\n--- Strategy 1: Corrupt Labels Only ---")
    label_corruptor = Typogre(
        rate=0.8,  # High rate on labels
        seed=42,
        include_only_patterns=[r"\[LABEL\].*?\[/LABEL\]"],
        exclude_patterns=[r"\[/?SYSTEM\]", r"\[/?LABEL\]"],  # Preserve tags
    )
    gaggle_labels = Gaggle([label_corruptor], seed=100)

    for _, row in df.iterrows():
        result = gaggle_labels.corrupt(row["text"])
        print(f"  {result}")

    # Strategy 2: Corrupt content only, preserve labels (curriculum learning)
    print("\n--- Strategy 2: Corrupt Content Only (Lower Rate) ---")
    content_corruptor = Typogre(
        rate=0.3,  # Lower rate for curriculum
        seed=43,
        exclude_patterns=[
            r"\[/?SYSTEM\].*?\[/SYSTEM\]",  # Exclude system block
            r"\[/?LABEL\].*?\[/LABEL\]",  # Exclude label block
        ],
    )
    gaggle_content = Gaggle([content_corruptor], seed=100)

    for _, row in df.iterrows():
        result = gaggle_content.corrupt(row["text"])
        print(f"  {result}")

    # Strategy 3: Heterogeneous masks - both corruptions with independent targeting
    print("\n--- Strategy 3: Heterogeneous Masks (Both Corruptions) ---")
    print("    Label corruptor: targets only label content (not tags)")
    print("    Content corruptor: targets only surrounding text")

    label_typo = Typogre(
        rate=0.8,
        seed=42,
        include_only_patterns=[r"\[LABEL\].*?\[/LABEL\]"],
        exclude_patterns=[r"\[/?LABEL\]"],  # Preserve the tag syntax
    )

    content_typo = Typogre(
        rate=0.2,
        seed=43,
        exclude_patterns=[
            r"\[SYSTEM\].*?\[/SYSTEM\]",
            r"\[LABEL\].*?\[/LABEL\]",
        ],
    )

    # Both in same gaggle with different masks
    gaggle_both = Gaggle([label_typo, content_typo], seed=100)

    print(f"\n    Heterogeneous masks detected: {gaggle_both._has_heterogeneous_masks()}")
    print(f"    Number of mask groups: {len(gaggle_both._group_by_masks())}")

    for _, row in df.iterrows():
        result = gaggle_both.corrupt(row["text"])
        print(f"  {result}")

    # Verify system prompt is always preserved
    print("\n--- Verification: System Prompt Preservation ---")
    for _, row in df.iterrows():
        result = gaggle_both.corrupt(row["text"])
        if "[SYSTEM]Classify[/SYSTEM]" in result:
            print("  ✓ System prompt preserved")
        else:
            print(f"  ✗ System prompt corrupted: {result}")


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
    demo_label_leakage_prevention()
    demo_datadesigner_integration()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

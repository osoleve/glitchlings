"""Complete example: Metrics framework end-to-end pipeline.

This script demonstrates the full workflow:
1. Define glitchlings
2. Prepare input data
3. Batch process with multiple tokenizers
4. Aggregate and analyze results
5. Generate visualizations

Run with:
    python examples/metrics_complete_example.py

Requirements:
    pip install glitchlings[metrics,metrics-tokenizers,metrics-viz]
"""

from __future__ import annotations

import tempfile
from pathlib import Path

# Step 1: Define glitchlings
def typogre(text: str) -> str:
    """Swap 'th' -> 'ht'."""
    return text.replace("th", "ht").replace("TH", "HT").replace("Th", "Ht")


def ekkokin(text: str) -> str:
    """Double consonants."""
    consonants = "bcdfghjklmnpqrstvwxyz"
    result = []
    for char in text:
        result.append(char)
        if char.lower() in consonants:
            result.append(char)
    return "".join(result)


def swapling(text: str) -> str:
    """Swap adjacent words."""
    words = text.split()
    for i in range(0, len(words) - 1, 2):
        words[i], words[i + 1] = words[i + 1], words[i]
    return " ".join(words)


# Step 2: Prepare sample texts
SAMPLE_TEXTS = [
    "The quick brown fox jumps over the lazy dog.",
    "Machine learning models process natural language efficiently.",
    "Python is a powerful programming language for data science.",
    "The theory of computation studies algorithmic complexity.",
    "Deep neural networks can learn hierarchical representations.",
    "Natural language processing enables machines to understand text.",
    "Tokenization is the first step in most NLP pipelines.",
    "The transformer architecture revolutionized sequence modeling.",
    "Attention mechanisms allow models to focus on relevant context.",
    "Transfer learning leverages pre-trained models for new tasks.",
]


def main():
    """Run complete metrics pipeline."""
    print("=" * 70)
    print("Glitchlings Metrics Framework - Complete Example")
    print("=" * 70)

    # Import dependencies
    try:
        from glitchlings.metrics.core.batch import process_and_write
        from glitchlings.metrics.core.tokenizers import (
            SimpleTokenizer,
            create_huggingface_adapter,
        )
        from glitchlings.metrics.metrics import create_default_registry
        from glitchlings.metrics.viz import (
            create_embedding_plot,
            create_heatmap,
            create_multi_radar_chart,
            create_sparklines,
            load_observations_from_parquet,
        )
        from glitchlings.metrics.viz.aggregate import aggregate_observations
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease install required dependencies:")
        print("  pip install glitchlings[metrics,metrics-tokenizers,metrics-viz]")
        return 1

    # Create temporary directory for results
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "results"
        figures_dir = Path(tmpdir) / "figures"
        output_dir.mkdir()
        figures_dir.mkdir()

        print(f"\nOutput directory: {output_dir}")
        print(f"Figures directory: {figures_dir}\n")

        # Step 3: Create tokenizers
        print("Step 1/5: Setting up tokenizers...")
        print("-" * 70)

        tokenizers = [SimpleTokenizer()]

        # Try to add HuggingFace tokenizers
        try:
            tokenizers.extend([
                create_huggingface_adapter("gpt2"),
                create_huggingface_adapter("bert-base-uncased"),
            ])
            print("✓ Loaded: SimpleTokenizer, gpt2, bert-base-uncased")
        except ImportError:
            print("⚠ HuggingFace tokenizers not available (install with metrics-tokenizers)")
            print("✓ Using: SimpleTokenizer only")

        # Step 4: Process each glitchling
        print("\nStep 2/5: Batch processing glitchlings...")
        print("-" * 70)

        registry = create_default_registry()
        glitchlings = [
            ("typogre", typogre),
            ("ekkokin", ekkokin),
            ("swapling", swapling),
        ]

        all_manifests = []
        for glitchling_id, glitchling_fn in glitchlings:
            print(f"  Processing {glitchling_id}...", end=" ")

            manifest = process_and_write(
                texts=SAMPLE_TEXTS,
                glitchling_fn=glitchling_fn,
                glitchling_id=glitchling_id,
                registry=registry,
                tokenizers=tokenizers,
                output_dir=output_dir,
                partition_by=["tokenizer_id"],
            )

            all_manifests.append(manifest)
            print(f"✓ {manifest.num_observations} observations")

        print(f"\n✓ Total observations: {sum(m.num_observations for m in all_manifests)}")

        # Step 5: Load all observations
        print("\nStep 3/5: Loading and aggregating results...")
        print("-" * 70)

        # Find all parquet files
        parquet_files = list(output_dir.rglob("*.parquet"))
        print(f"  Found {len(parquet_files)} Parquet files")

        # Load observations from all files
        all_observations = []
        for pf in parquet_files:
            try:
                obs = load_observations_from_parquet(pf)
                all_observations.extend(obs)
            except Exception as e:
                print(f"  ⚠ Could not load {pf.name}: {e}")

        print(f"✓ Loaded {len(all_observations)} total observations")

        # Aggregate by glitchling
        print("\n  Aggregating metrics by glitchling...")
        agg_results = aggregate_observations(
            all_observations,
            group_by=["glitchling_id"],
        )

        print("\n  Summary Statistics:")
        print("  " + "-" * 66)
        for result in agg_results:
            glitch_id = result["glitchling_id"]
            ned_mean = result.get("metric_ned.value", {}).get("mean", 0)
            lcsr_mean = result.get("metric_lcsr.value", {}).get("mean", 0)
            print(f"  {glitch_id:12s} | NED: {ned_mean:.3f} | LCSR: {lcsr_mean:.3f}")

        # Step 6: Generate visualizations
        print("\nStep 4/5: Generating visualizations...")
        print("-" * 70)

        # Check if matplotlib/plotly available
        try:
            import matplotlib
            has_mpl = True
        except ImportError:
            has_mpl = False
            print("  ⚠ matplotlib not available, skipping static figures")

        try:
            import plotly
            has_plotly = True
        except ImportError:
            has_plotly = False
            print("  ⚠ plotly not available, skipping interactive figures")

        if not has_mpl and not has_plotly:
            print("  ❌ No visualization libraries available")
            print("     Install with: pip install glitchlings[metrics-viz]")
        else:
            # 1. Multi-glitchling radar chart
            if has_plotly:
                print("  Creating multi-glitchling radar chart...", end=" ")
                try:
                    # Prepare data for radar chart
                    glitchling_data = {}
                    for result in agg_results:
                        g_id = result["glitchling_id"]
                        glitchling_data[g_id] = {
                            k.replace("metric_", ""): v["mean"]
                            for k, v in result.items()
                            if k.startswith("metric_") and "value" in k
                        }

                    fig = create_multi_radar_chart(
                        glitchling_data,
                        title="Glitchling Comparison (Radar)",
                        backend="plotly",
                        output_path=figures_dir / "radar_comparison.html",
                    )
                    print("✓")
                except Exception as e:
                    print(f"✗ ({e})")

            # 2. Heatmap of edit distance
            if has_mpl:
                print("  Creating edit distance heatmap...", end=" ")
                try:
                    fig = create_heatmap(
                        all_observations,
                        metric="ned.value",
                        row_key="glitchling_id",
                        col_key="tokenizer_id",
                        title="Normalized Edit Distance by Glitchling × Tokenizer",
                        backend="matplotlib",
                        output_path=figures_dir / "ned_heatmap.png",
                    )
                    print("✓")
                except Exception as e:
                    print(f"✗ ({e})")

            # 3. UMAP embedding
            try:
                import umap
                has_umap = True
            except ImportError:
                has_umap = False

            if has_plotly and has_umap and len(all_observations) >= 3:
                print("  Creating UMAP embedding...", end=" ")
                try:
                    fig = create_embedding_plot(
                        all_observations,
                        metrics=[
                            "ned.value", "lcsr.value", "jsdiv.value",
                            "rord.value", "cosdist.value"
                        ],
                        method="umap",
                        color_by="glitchling_id",
                        title="Metric Space Projection (UMAP)",
                        backend="plotly",
                        n_neighbors=min(15, len(all_observations) - 1),
                        output_path=figures_dir / "umap_embedding.html",
                    )
                    print("✓")
                except Exception as e:
                    print(f"✗ ({e})")

            # 4. Sparklines
            if has_mpl and len(all_observations) >= 5:
                print("  Creating sparklines...", end=" ")
                try:
                    fig = create_sparklines(
                        all_observations,
                        metrics=["ned.value", "lcsr.value", "jsdiv.value"],
                        group_by="glitchling_id",
                        length_bins=5,
                        title="Metric Trends by Input Length",
                        backend="matplotlib",
                        output_path=figures_dir / "sparklines.png",
                    )
                    print("✓")
                except Exception as e:
                    print(f"✗ ({e})")

        # Step 7: Summary
        print("\nStep 5/5: Summary")
        print("-" * 70)
        print(f"✓ Processed {len(glitchlings)} glitchlings")
        print(f"✓ Used {len(tokenizers)} tokenizers")
        print(f"✓ Generated {len(all_observations)} observations")
        print(f"✓ Computed {len(registry.specs)} metrics per observation")

        if has_mpl or has_plotly:
            viz_count = len(list(figures_dir.glob("*")))
            print(f"✓ Created {viz_count} visualizations")
            print(f"\nFigures saved to: {figures_dir}")
        else:
            print("\n⚠ No visualizations generated (missing dependencies)")

        print("\n" + "=" * 70)
        print("Example complete!")
        print("=" * 70)

        # Keep figures available for inspection
        print(f"\nNOTE: Results in temporary directory will be deleted.")
        print(f"      Copy figures from {figures_dir} if needed.")
        input("\nPress Enter to cleanup and exit...")

    return 0


if __name__ == "__main__":
    exit(main())

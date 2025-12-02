# Textual TUI

Glitchlings includes an optional terminal-based user interface (TUI) built with [Textual](https://textual.textualize.io/). The TUI provides an interactive environment for experimenting with glitchlings, comparing tokenizer outputs, running parameter sweeps, and exporting results.

## Installation

The Textual GUI requires the `gui` extra:

```bash
pip install 'glitchlings[gui]'
```

## Launching the TUI

After installing the gui extra, launch the TUI with:

```bash
glitchlings-tui
```

Or run it as a module:

```bash
python -m gui.textual.app
```

## Features

### Workspace Panel

The main workspace displays:

- **Input text area** – Enter or paste text to corrupt
- **Output text area** – View the transformed result
- **Metrics table** – Token counts and similarity metrics per tokenizer

### Glitchling Panel

Select and configure glitchlings from the sidebar:

- Check/uncheck glitchlings to include them in the transformation pipeline
- Configure parameters for each glitchling (rate, modes, etc.)

### Tokenizer Panel

Choose tokenizers for metric comparison:

- `cl100k_base` (GPT-4/GPT-4o)
- `o200k_base` (GPT-4o-mini)
- `p50k_base` (GPT-3.5/legacy)

### Navigation

Switch between views using the navigation panel:

| Tab | Description |
|-----|-------------|
| **Workspace** | Main transformation workspace with input/output |
| **Datasets** | Load dataset samples and run batch processing |
| **Sweeps** | Run parameter sweeps across glitchlings |
| **Charts** | Visualize metrics and sweep results |

### Parameter Sweeps

The Sweeps panel lets you:

1. Select a parameter to sweep (e.g., `rate`)
2. Configure the range and step count
3. Run the sweep across all selected glitchlings
4. Export results for analysis

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| <kbd>F5</kbd> | Run transform |
| <kbd>Ctrl</kbd>+<kbd>Enter</kbd> | Run transform |
| <kbd>Ctrl</kbd>+<kbd>R</kbd> | Randomize seed |
| <kbd>Ctrl</kbd>+<kbd>C</kbd> | Copy output to clipboard |
| <kbd>Ctrl</kbd>+<kbd>V</kbd> | Paste from clipboard |
| <kbd>Ctrl</kbd>+<kbd>L</kbd> | Clear input |
| <kbd>Ctrl</kbd>+<kbd>N</kbd> | New session |
| <kbd>Ctrl</kbd>+<kbd>E</kbd> | Export session |
| <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd> | Export sweep results |
| <kbd>Ctrl</kbd>+<kbd>P</kbd> | Open command palette |
| <kbd>Ctrl</kbd>+<kbd>Q</kbd> | Quit |
| <kbd>Escape</kbd> | Focus input area |

## Command Palette

Press <kbd>Ctrl</kbd>+<kbd>P</kbd> to open the command palette. Available commands:

| Command | Description |
|---------|-------------|
| Transform | Apply glitchlings to input text |
| Randomize Seed | Generate a new random seed |
| Copy Output | Copy transformed text to clipboard |
| Paste Input | Paste from clipboard to input |
| Clear Input | Clear the input text area |
| Copy Input | Copy input text to clipboard |
| Toggle Auto-Update | Toggle auto transform on text changes |
| Toggle Multi-Seed | Toggle multi-seed mode for aggregated metrics |
| New Session | Clear and start fresh |

## Export Formats

The export dialog supports:

- **JSON** – Full session data including config, I/O, and metrics
- **CSV** – Tabular metrics data for spreadsheet analysis
- **Markdown** – Human-readable report format

Options include:

- Include timestamps
- Include metadata (seed, glitchlings, tokenizers)
- Include metrics breakdown

## Multi-Seed Mode

Enable multi-seed mode to run multiple transformations with different seeds and aggregate the metrics. This helps understand the variance in corruption effects.

Configure:

- Check the "Multi" checkbox in the header bar
- Set the number of seeds in the adjacent input

## Auto-Update Mode

Enable the "Auto" checkbox to automatically run transforms when:

- Input text changes
- Glitchling selection changes
- Glitchling parameters are modified

This is useful for interactive exploration but may be CPU-intensive with large inputs.

## Tips

1. **Start with low rates** – Begin with corruption rates around 0.01-0.05 to see effects without overwhelming the text
2. **Use deterministic seeds** – Set a specific seed for reproducible results
3. **Compare tokenizers** – Different tokenizers may show varying sensitivity to corruption
4. **Export for analysis** – Use CSV export for statistical analysis in external tools

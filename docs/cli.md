# Command Line Interface

The `glitchlings` CLI mirrors the Python API for corruption, configuration files, and dataset
helpers. Regenerate this page with `python -m glitchlings.dev.docs` whenever the CLI contract
changes.

## Quick commands

```bash
# Discover all built-in glitchlings.
glitchlings --list

# Glitch an entire file with Typogre and inspect the unified diff.
glitchlings -g typogre --input-file documents/report.txt --diff

# Configure glitchlings inline with keyword arguments.
glitchlings -g "Typogre(rate=0.05)" "Ghouls just wanna have fun"

# Pipe text through Mim1c for on-the-fly homoglyph swaps.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c

# Run an attack analysis with a specific tokenizer and output format.
glitchlings --attack --tokenizer cl100k_base --format yaml --sample

# Generate a full report and save to a file.
glitchlings --report -t gpt-4 -o report.json "Test input text"
```

## Built-in glitchlings

```text
   Typogre — scope: Character, order: early
     Hokey — scope: Character, order: first
     Mim1c — scope: Character, order: last
 Wherewolf — scope: Word, order: early
    Pedant — scope: Word, order: late
  Jargoyle — scope: Word, order: normal
  Rushmore — scope: Word, order: normal
  Redactyl — scope: Word, order: normal
Scannequin — scope: Character, order: late
    Zeedub — scope: Character, order: last
```

## Help overview

```text
usage: glitchlings [-h] [-g SPEC] [-s SEED] [-i INPUT_FILE] [-o OUTPUT_FILE]
                   [--sample] [--diff] [--list] [-c CONFIG] [--attack]
                   [--report] [-f {json,yaml,yml}] [-t TOKENIZER] [text ...]

Summon glitchlings to corrupt text. Provide input text as an argument, via
--input-file, or pipe it on stdin.

positional arguments:
  text                  Text to corrupt. If omitted, stdin is used or --sample
                        provides fallback text.

options:
  -h, --help            show this help message and exit
  -g SPEC, --glitchling SPEC
                        Glitchling to apply, optionally with parameters like
                        Typogre(rate=0.05). Repeat for multiples; defaults to
                        all built-ins.
  -s SEED, --seed SEED  Seed controlling deterministic corruption order
                        (default: 151).
  -i INPUT_FILE, --input-file INPUT_FILE
                        Read input text from a file instead of the command
                        line argument.
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Write output to a file instead of stdout.
  --sample              Use the included SAMPLE_TEXT when no other input is
                        provided.
  --diff                Show a unified diff between the original and corrupted
                        text.
  --list                List available glitchlings and exit.
  -c CONFIG, --config CONFIG
                        Load glitchlings from a YAML configuration file.
  --attack              Output an Attack summary. Includes metrics and counts
                        without full token lists.
  --report              Output a full Attack report. Includes tokens, token
                        IDs, metrics, and counts.
  -f {json,yaml,yml}, --format {json,yaml,yml}
                        Output format for --attack or --report (default: json).
  -t TOKENIZER, --tokenizer TOKENIZER
                        Tokenizer to use for --attack or --report. Checks
                        tiktoken first, then HuggingFace tokenizers library.
                        Examples: cl100k_base, gpt-4, bert-base-uncased.
```

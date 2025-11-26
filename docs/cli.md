# Command Line Interface

The `glitchlings` CLI mirrors the Python API for corruption, configuration files, and dataset
helpers. Regenerate this page with `python -m glitchlings.dev.docs` whenever the CLI contract
changes.

## Quick commands

```bash
# Discover all built-in glitchlings.
glitchlings --list

# Glitch an entire file with Typogre and inspect the unified diff.
glitchlings -g typogre --file documents/report.txt --diff

# Configure glitchlings inline with keyword arguments.
glitchlings -g "Typogre(rate=0.05)" "Ghouls just wanna have fun"

# Pipe text through Mim1c for on-the-fly homoglyph swaps.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c
```

## Built-in glitchlings

```text
   Typogre — scope: Character, order: early
     Hokey — scope: Character, order: first
     Mim1c — scope: Character, order: last
   Ekkokin — scope: Word, order: early
    Pedant — scope: Word, order: late
  Jargoyle — scope: Word, order: normal
  Rushmore — scope: Word, order: normal
  Redactyl — scope: Word, order: normal
Scannequin — scope: Character, order: late
    Zeedub — scope: Character, order: last
```

## Help overview

```text
usage: glitchlings [-h] [-g SPEC] [-s SEED] [-f FILE] [--sample] [--diff]
                   [--list] [-c CONFIG]
                   [text ...]

Summon glitchlings to corrupt text. Provide input text as an argument, via
--file, or pipe it on stdin.

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
  -f FILE, --file FILE  Read input text from a file instead of the command
                        line argument.
  --sample              Use the included SAMPLE_TEXT when no other input is
                        provided.
  --diff                Show a unified diff between the original and corrupted
                        text.
  --list                List available glitchlings and exit.
  -c CONFIG, --config CONFIG
                        Load glitchlings from a YAML configuration file.
```

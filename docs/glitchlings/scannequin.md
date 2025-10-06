# Scannequin

Scannequin introduces OCR-inspired transcription mistakes to emulate noisy document scans.

- **Scope**: character level (late order).
- **Signature**: `Scannequin(error_rate=0.02, seed=None)`.
- **Behaviour**: introduces OCR-style confusion pairs (rn↔m, cl↔d, O↔0, curly quotes to ASCII, etc.) using deterministic span selection. Supports a Rust acceleration path when compiled.
- **Usage tips**:
  - Bump `error_rate` for scanned-document stress tests or reduce it for light OCR noise.
  - Because replacements can change token length, run Scannequin after word-level glitchlings to avoid offset drift.
  - Combine with Redactyl to mimic heavily redacted, poorly scanned archives.

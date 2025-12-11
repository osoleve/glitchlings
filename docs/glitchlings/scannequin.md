# Scannequin

Scannequin introduces OCR-inspired transcription mistakes to emulate noisy document scans. It operates at **document level** to enable document-wide consistency in error patterns.

- **Scope**: document level (late order).
- **Signature**: `Scannequin(rate=0.02, seed=None, preset=None, burst_enter=0.0, burst_exit=0.3, burst_multiplier=3.0, bias_k=0, bias_beta=2.0, space_drop_rate=0.0, space_insert_rate=0.0)`.

## Features

### Burst Model (Kanungo et al., 1994)

Real document defects are spatially correlated - a coffee stain or fold affects a region, not individual characters. Scannequin uses an HMM with two states:

- **Clean state**: Base error rate applies
- **Harsh state**: Error rate multiplied by `burst_multiplier`

Transition probabilities: `P(clean→harsh) = burst_enter`, `P(harsh→clean) = burst_exit`

This produces "bad scan patches" - runs of degraded text that simulate smudges or folds.

### Document-Level Bias (UNLV-ISRI, 1995)

Documents scanned under the same conditions exhibit consistent error profiles. At document start, K confusion patterns are randomly selected and amplified by `bias_beta`. This creates the "why does it always turn 'l' into '1' in this document" consistency.

### Whitespace Errors (Smith, 2007; ICDAR)

Models OCR segmentation failures that cause word merges/splits. These happen before character recognition in the real OCR pipeline:

- `space_drop_rate`: Probability of deleting a space (merging words): "the cat" → "thecat"
- `space_insert_rate`: Probability of inserting a spurious space: "together" → "to gether"

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rate` | float | 0.02 | Base probability of applying a confusion |
| `seed` | int | None | Deterministic seed |
| `preset` | str | None | Quality preset name (overrides individual params) |
| `burst_enter` | float | 0.0 | P(clean → harsh) state transition |
| `burst_exit` | float | 0.3 | P(harsh → clean) state transition |
| `burst_multiplier` | float | 3.0 | Rate multiplier in harsh state |
| `bias_k` | int | 0 | Number of patterns to amplify per document |
| `bias_beta` | float | 2.0 | Amplification factor for biased patterns |
| `space_drop_rate` | float | 0.0 | P(delete space, merge words) |
| `space_insert_rate` | float | 0.0 | P(insert spurious space) |

## Quality Presets

Based on UNLV-ISRI test regimes (Rice et al., 1995):

| Preset | Rate | Burst Enter | Burst Exit | Multiplier | Bias K | Space Drop | Space Insert |
|--------|------|-------------|------------|------------|--------|------------|--------------|
| `clean_300dpi` | 0.01 | 0.0 | 0.3 | 3.0 | 0 | 0.0 | 0.0 |
| `newspaper` | 0.03 | 0.05 | 0.3 | 2.5 | 3 | 0.005 | 0.002 |
| `fax` | 0.06 | 0.1 | 0.2 | 3.5 | 5 | 0.02 | 0.01 |
| `photocopy_3rd_gen` | 0.08 | 0.15 | 0.15 | 4.0 | 5 | 0.03 | 0.015 |

## Usage Examples

Basic usage with default parameters:

```python
from glitchlings import Scannequin

scan = Scannequin(rate=0.02, seed=42)
result = scan("The cat sat on the mat")
```

Using a quality preset:

```python
fax_scan = Scannequin(preset="fax", seed=42)
result = fax_scan("Hello world, this is a test document.")
```

Using the class method for presets:

```python
fax = Scannequin.from_preset("fax", seed=42)
```

Enabling burst mode for realistic degradation:

```python
degraded = Scannequin(
    rate=0.03,
    burst_enter=0.1,
    burst_exit=0.2,
    seed=42
)
result = degraded("Some regions will have clustered errors like smudges.")
```

## Usage Tips

- Use presets for quick configuration based on real-world scenarios.
- Enable `burst_enter > 0` for spatially correlated errors (simulates physical defects).
- Set `bias_k > 0` for consistent error patterns within a document.
- Use `space_drop_rate` and `space_insert_rate` to simulate segmentation failures.
- Combine with Redactyl to mimic heavily redacted, poorly scanned archives.

## Confusion Table

Scannequin uses an empirically-derived confusion table including:

- Character shape confusions: rn↔m, cl↔d, li↔h, vv↔w, ri↔n
- Digit/letter confusions: I↔l↔1, O↔0, B↔8, S↔5, Z↔2, G↔6
- Typographic normalization: curly quotes → ASCII, em/en dashes → hyphen

## References

1. **Kolak & Resnik (2002)** - Noisy-channel OCR error modeling with parameter estimation

2. **Kanungo et al. (1994)** - "Nonlinear Global and Local Document Degradation Models"
   - [https://kanungo.com/pubs/ijist94-model.pdf](https://kanungo.com/pubs/ijist94-model.pdf)
   - Establishes blur/speckle/threshold as key degradation parameters

3. **Li, Lopresti, Nagy, Tompkins (1996)** - "Validation of Image Defect Models for Optical Character Recognition"
   - [https://sites.ecse.rpi.edu/~nagy/PDF_files/Li_Lopresti_Tompkins_PAMI96.pdf](https://sites.ecse.rpi.edu/~nagy/PDF_files/Li_Lopresti_Tompkins_PAMI96.pdf)
   - Framework for validating defect model generators

4. **Rice et al. / UNLV-ISRI Annual Tests (1995)** - Varied scanning at 200/300/400 dpi with different thresholds and fax resolutions

5. **Taghva et al.** - "Context beats Confusion"
   - [https://www.projectcomputing.com/resources/CorrectingNoisyOCR.pdf](https://www.projectcomputing.com/resources/CorrectingNoisyOCR.pdf)
   - Discusses weighted multi-character edits in OCR correction

6. **ICDAR Robust Reading Competitions**
   - [https://dl.acm.org/doi/abs/10.1007/s10032-004-0134-3](https://dl.acm.org/doi/abs/10.1007/s10032-004-0134-3)
   - Evaluates segmentation/localization as distinct failure modes

7. **Smith (2007)** - Tesseract architecture
   - Describes classic OCR pipeline (layout → connected-component analysis → segmentation → recognition)

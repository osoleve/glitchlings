"""Scannequin: Research-backed OCR simulation glitchling.

This module provides OCR-style text corruption based on empirical research
into document degradation and character recognition failures.

References
----------
- Kolak & Resnik (2002) - Noisy-channel OCR error modeling
- Kanungo et al. (1994) - "Nonlinear Global and Local Document Degradation Models"
  https://kanungo.com/pubs/ijist94-model.pdf
- Li, Lopresti, Nagy, Tompkins (1996) - "Validation of Image Defect Models for OCR"
  https://sites.ecse.rpi.edu/~nagy/PDF_files/Li_Lopresti_Tompkins_PAMI96.pdf
- Rice et al. / UNLV-ISRI Annual Tests (1995) - Quality preset empirical basis
- Taghva et al. - "Context beats Confusion"
  https://www.projectcomputing.com/resources/CorrectingNoisyOCR.pdf
- ICDAR Robust Reading Competitions
  https://dl.acm.org/doi/abs/10.1007/s10032-004-0134-3
- Smith (2007) - Tesseract OCR architecture
"""

import random
from typing import Any, Literal, cast

from glitchlings.constants import (
    DEFAULT_SCANNEQUIN_BIAS_BETA,
    DEFAULT_SCANNEQUIN_BIAS_K,
    DEFAULT_SCANNEQUIN_BURST_ENTER,
    DEFAULT_SCANNEQUIN_BURST_EXIT,
    DEFAULT_SCANNEQUIN_BURST_MULTIPLIER,
    DEFAULT_SCANNEQUIN_RATE,
    DEFAULT_SCANNEQUIN_SPACE_DROP_RATE,
    DEFAULT_SCANNEQUIN_SPACE_INSERT_RATE,
    SCANNEQUIN_PRESETS,
)
from glitchlings.internal.rust_ffi import ocr_artifacts_rust, resolve_seed

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload

# Type alias for preset names
PresetName = Literal["clean_300dpi", "newspaper", "fax", "photocopy_3rd_gen"]


def ocr_artifacts(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    burst_enter: float | None = None,
    burst_exit: float | None = None,
    burst_multiplier: float | None = None,
    bias_k: int | None = None,
    bias_beta: float | None = None,
    space_drop_rate: float | None = None,
    space_insert_rate: float | None = None,
) -> str:
    """Introduce OCR-like artifacts into text with research-backed enhancements.

    This function simulates OCR errors using three research-backed features:

    **Burst Model (Kanungo et al., 1994)**
    Real document defects are spatially correlated - a coffee stain or fold
    affects a region, not individual characters. Uses an HMM to create error
    clusters simulating smudges, folds, or degraded scan regions.

    **Document-Level Bias (UNLV-ISRI, 1995)**
    Documents scanned under the same conditions exhibit consistent error
    profiles. Randomly selects K confusion patterns and amplifies their
    selection probability, creating "why does it always turn 'l' into '1'"
    consistency.

    **Whitespace Errors (Smith, 2007; ICDAR)**
    Models OCR segmentation failures that cause word merges/splits. These
    happen before character recognition in the real pipeline.

    Parameters
    ----------
    text : str
        Input text to corrupt.
    rate : float, optional
        Base probability of applying a confusion to any given candidate.
        Default is 0.02.
    seed : int, optional
        Deterministic seed for reproducibility.
    rng : random.Random, optional
        Optional RNG for seed generation.
    burst_enter : float, optional
        Probability of transitioning from clean to harsh state (default 0.0).
    burst_exit : float, optional
        Probability of transitioning from harsh to clean state (default 0.3).
    burst_multiplier : float, optional
        Rate multiplier when in harsh state (default 3.0).
    bias_k : int, optional
        Number of confusion patterns to amplify per document (default 0).
    bias_beta : float, optional
        Amplification factor for selected patterns (default 2.0).
    space_drop_rate : float, optional
        Probability of deleting a space, merging words (default 0.0).
    space_insert_rate : float, optional
        Probability of inserting a spurious space (default 0.0).

    Returns
    -------
    str
        Text with simulated OCR errors.

    References
    ----------
    - Kanungo et al. (1994) - "Nonlinear Global and Local Document Degradation Models"
    - Rice et al. / UNLV-ISRI Annual Tests (1995)
    - Smith (2007) - Tesseract OCR architecture
    - ICDAR Robust Reading Competitions
    """
    if not text:
        return text

    effective_rate = DEFAULT_SCANNEQUIN_RATE if rate is None else rate
    clamped_rate = max(0.0, effective_rate)

    return ocr_artifacts_rust(
        text,
        clamped_rate,
        resolve_seed(seed, rng),
        burst_enter=burst_enter,
        burst_exit=burst_exit,
        burst_multiplier=burst_multiplier,
        bias_k=bias_k,
        bias_beta=bias_beta,
        space_drop_rate=space_drop_rate,
        space_insert_rate=space_insert_rate,
    )


class Scannequin(Glitchling):
    """Glitchling that simulates OCR artifacts with research-backed enhancements.

    Scannequin introduces OCR-inspired transcription mistakes to emulate noisy
    document scans. It now operates at **document level** to enable document-wide
    consistency in error patterns.

    Features
    --------

    **Burst Model (Kanungo et al., 1994)**
    Uses an HMM with clean/harsh states to create spatially correlated error
    clusters, simulating physical defects like smudges, folds, or scan artifacts.

    **Document-Level Bias (UNLV-ISRI, 1995)**
    Selects K confusion patterns at document start and amplifies their selection
    probability, creating consistent error profiles across the document.

    **Whitespace Errors (Smith, 2007; ICDAR)**
    Models OCR segmentation failures: space drops (word merges) and spurious
    space insertions (word splits).

    **Quality Presets**
    Based on UNLV-ISRI test regimes:
    - ``"clean_300dpi"``: Minimal errors, good quality baseline
    - ``"newspaper"``: Moderate errors with some burst
    - ``"fax"``: High errors, strong burst, heavy l/1/I confusion
    - ``"photocopy_3rd_gen"``: Very degraded, long burst runs

    Parameters
    ----------
    rate : float, optional
        Base probability of applying a confusion (default 0.02).
    seed : int, optional
        Deterministic seed.
    preset : str, optional
        Quality preset name. Overrides individual parameters when set.
    burst_enter : float, optional
        P(clean → harsh) state transition (default 0.0 = disabled).
    burst_exit : float, optional
        P(harsh → clean) state transition (default 0.3).
    burst_multiplier : float, optional
        Rate multiplier in harsh state (default 3.0).
    bias_k : int, optional
        Number of patterns to amplify per document (default 0 = disabled).
    bias_beta : float, optional
        Amplification factor for biased patterns (default 2.0).
    space_drop_rate : float, optional
        P(delete space, merge words) (default 0.0 = disabled).
    space_insert_rate : float, optional
        P(insert spurious space) (default 0.0 = disabled).
    **kwargs
        Additional parameters passed to base Glitchling.

    Examples
    --------
    Basic usage with default parameters:

    >>> scan = Scannequin(rate=0.02, seed=42)
    >>> scan("The cat sat on the mat")
    'The cat sat on the rnat'

    Using a quality preset:

    >>> fax_scan = Scannequin(preset="fax", seed=42)
    >>> fax_scan("Hello world, this is a test document.")
    'He1lo vvorld, thls is a testdocument.'

    Enabling burst mode for realistic degradation:

    >>> degraded = Scannequin(rate=0.03, burst_enter=0.1, burst_exit=0.2, seed=42)
    >>> degraded("Some regions will have clustered errors like smudges.")
    'Sorne regions will have dustered errors Iike srnudges.'

    References
    ----------
    - Kolak & Resnik (2002) - Noisy-channel OCR error modeling
    - Kanungo et al. (1994) - "Nonlinear Global and Local Document Degradation Models"
    - Li, Lopresti, Nagy, Tompkins (1996) - "Validation of Image Defect Models for OCR"
    - Rice et al. / UNLV-ISRI Annual Tests (1995)
    - Smith (2007) - Tesseract OCR architecture
    """

    flavor = "Isn't it weird how the word 'bed' looks like a bed?"

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        preset: PresetName | None = None,
        burst_enter: float | None = None,
        burst_exit: float | None = None,
        burst_multiplier: float | None = None,
        bias_k: int | None = None,
        bias_beta: float | None = None,
        space_drop_rate: float | None = None,
        space_insert_rate: float | None = None,
        **kwargs: Any,
    ) -> None:
        # If preset is specified, load parameters from it
        if preset is not None:
            if preset not in SCANNEQUIN_PRESETS:
                valid_presets = ", ".join(sorted(SCANNEQUIN_PRESETS.keys()))
                msg = f"Unknown preset '{preset}'. Valid presets: {valid_presets}"
                raise ValueError(msg)

            (
                preset_rate,
                preset_burst_enter,
                preset_burst_exit,
                preset_burst_multiplier,
                preset_bias_k,
                preset_bias_beta,
                preset_space_drop_rate,
                preset_space_insert_rate,
            ) = SCANNEQUIN_PRESETS[preset]

            # Preset values are used as defaults, explicit params override
            if rate is None:
                rate = preset_rate
            if burst_enter is None:
                burst_enter = preset_burst_enter
            if burst_exit is None:
                burst_exit = preset_burst_exit
            if burst_multiplier is None:
                burst_multiplier = preset_burst_multiplier
            if bias_k is None:
                bias_k = preset_bias_k
            if bias_beta is None:
                bias_beta = preset_bias_beta
            if space_drop_rate is None:
                space_drop_rate = preset_space_drop_rate
            if space_insert_rate is None:
                space_insert_rate = preset_space_insert_rate

        # Apply defaults for any remaining None values
        effective_rate = DEFAULT_SCANNEQUIN_RATE if rate is None else rate
        effective_burst_enter = (
            DEFAULT_SCANNEQUIN_BURST_ENTER if burst_enter is None else burst_enter
        )
        effective_burst_exit = DEFAULT_SCANNEQUIN_BURST_EXIT if burst_exit is None else burst_exit
        effective_burst_multiplier = (
            DEFAULT_SCANNEQUIN_BURST_MULTIPLIER if burst_multiplier is None else burst_multiplier
        )
        effective_bias_k = DEFAULT_SCANNEQUIN_BIAS_K if bias_k is None else bias_k
        effective_bias_beta = DEFAULT_SCANNEQUIN_BIAS_BETA if bias_beta is None else bias_beta
        effective_space_drop_rate = (
            DEFAULT_SCANNEQUIN_SPACE_DROP_RATE if space_drop_rate is None else space_drop_rate
        )
        effective_space_insert_rate = (
            DEFAULT_SCANNEQUIN_SPACE_INSERT_RATE if space_insert_rate is None else space_insert_rate
        )

        super().__init__(
            name="Scannequin",
            corruption_function=ocr_artifacts,
            # Changed from CHARACTER to DOCUMENT for document-wide consistency
            scope=AttackWave.DOCUMENT,
            order=AttackOrder.LATE,
            seed=seed,
            rate=effective_rate,
            burst_enter=effective_burst_enter,
            burst_exit=effective_burst_exit,
            burst_multiplier=effective_burst_multiplier,
            bias_k=effective_bias_k,
            bias_beta=effective_bias_beta,
            space_drop_rate=effective_space_drop_rate,
            space_insert_rate=effective_space_insert_rate,
            **kwargs,
        )

        # Store preset name if used
        self._preset = preset

    @classmethod
    def from_preset(cls, preset: PresetName, *, seed: int | None = None) -> "Scannequin":
        """Create a Scannequin instance from a named quality preset.

        Parameters
        ----------
        preset : str
            Quality preset name. One of:
            - ``"clean_300dpi"``: Clean 300 DPI scan, minimal errors
            - ``"newspaper"``: Newspaper-quality scan, moderate degradation
            - ``"fax"``: Fax-quality, high error rate with l/1/I confusion
            - ``"photocopy_3rd_gen"``: Third-generation photocopy, severe degradation
        seed : int, optional
            Deterministic seed for reproducibility.

        Returns
        -------
        Scannequin
            Configured Scannequin instance.

        Examples
        --------
        >>> fax = Scannequin.from_preset("fax", seed=42)
        >>> fax("The quick brown fox")
        'Tbe quick brovvn fox'
        """
        return cls(preset=preset, seed=seed)

    def pipeline_operation(self) -> PipelineOperationPayload:
        """Return the Rust pipeline descriptor with all OCR parameters."""
        rate_value = self.kwargs.get("rate", DEFAULT_SCANNEQUIN_RATE)
        rate = DEFAULT_SCANNEQUIN_RATE if rate_value is None else float(rate_value)

        return cast(
            PipelineOperationPayload,
            {
                "type": "ocr",
                "rate": rate,
                "burst_enter": float(
                    self.kwargs.get("burst_enter", DEFAULT_SCANNEQUIN_BURST_ENTER)
                ),
                "burst_exit": float(self.kwargs.get("burst_exit", DEFAULT_SCANNEQUIN_BURST_EXIT)),
                "burst_multiplier": float(
                    self.kwargs.get("burst_multiplier", DEFAULT_SCANNEQUIN_BURST_MULTIPLIER)
                ),
                "bias_k": int(self.kwargs.get("bias_k", DEFAULT_SCANNEQUIN_BIAS_K)),
                "bias_beta": float(self.kwargs.get("bias_beta", DEFAULT_SCANNEQUIN_BIAS_BETA)),
                "space_drop_rate": float(
                    self.kwargs.get("space_drop_rate", DEFAULT_SCANNEQUIN_SPACE_DROP_RATE)
                ),
                "space_insert_rate": float(
                    self.kwargs.get("space_insert_rate", DEFAULT_SCANNEQUIN_SPACE_INSERT_RATE)
                ),
            },
        )


# Default instance for convenience
scannequin = Scannequin()


__all__ = ["Scannequin", "scannequin", "ocr_artifacts", "SCANNEQUIN_PRESETS"]

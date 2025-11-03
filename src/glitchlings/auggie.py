"""High-level helpers for assembling glitchling gaggles.

Auggie is a friendly handler who wrangles glitchlings by descriptive verbs
instead of their proper names. Rather than remembering that :class:`Typogre`
introduces typos, callers can reach for ``Auggie.add_typos`` and let the tamer
do the summoning.
"""

from __future__ import annotations

from typing import Iterable, Iterator

from .zoo import (
    Adjax,
    Apostrofae,
    Ekkokin,
    Gaggle,
    Glitchling,
    Hokey,
    Jargoyle,
    Mim1c,
    Pedant,
    Redactyl,
    Reduple,
    Rushmore,
    RushmoreMode,
    Scannequin,
    Spectroll,
    Typogre,
    Zeedub,
)
from .zoo.core import Transcript

__all__ = ["Auggie"]


class Auggie:
    """Convenience builder that tames glitchlings into a gaggle.

    Auggie maintains a roster of glitchlings.  Each ``add_*`` method instantiates
    the corresponding glitchling with the provided keyword arguments and adds it
    to the active lineup.  When invoked, Auggie delegates to an internal
    :class:`~glitchlings.zoo.core.Gaggle` to corrupt text.
    """

    def __init__(
        self,
        *,
        seed: int | None = 151,
        glitchlings: Iterable[Glitchling] | None = None,
    ) -> None:
        self.seed: int | None = seed
        self._glitchlings: list[Glitchling] = list(glitchlings or [])
        self._gaggle: Gaggle | None = None

    def _invalidate(self) -> None:
        self._gaggle = None

    def _ensure_gaggle(self) -> Gaggle:
        if self._gaggle is None:
            if self.seed is None:
                self._gaggle = Gaggle(self._glitchlings)
            else:
                self._gaggle = Gaggle(self._glitchlings, seed=int(self.seed))
        return self._gaggle

    def _tame(self, glitchling: Glitchling) -> "Auggie":
        self._glitchlings.append(glitchling)
        self._invalidate()
        return self

    def set_seed(self, seed: int | None) -> "Auggie":
        self.seed = seed
        self._invalidate()
        return self

    def add_custom(self, glitchling: Glitchling) -> "Auggie":
        """Add a pre-configured glitchling instance to the roster."""

        return self._tame(glitchling)

    def add_typos(self, **kwargs: object) -> "Auggie":
        """Introduce keyboard-neighbour typos via :class:`Typogre`."""

        return self._tame(Typogre(**kwargs))

    def add_word_stretches(self, **kwargs: object) -> "Auggie":
        """Elongate expressive words with :class:`Hokey`."""

        return self._tame(Hokey(**kwargs))

    def add_smart_quotes(self, **kwargs: object) -> "Auggie":
        """Swap straight quotes for balanced Unicode pairs using :class:`Apostrofae`."""

        return self._tame(Apostrofae(**kwargs))

    def add_confusables(self, **kwargs: object) -> "Auggie":
        """Slip Unicode confusables into text through :class:`Mim1c`."""

        return self._tame(Mim1c(**kwargs))

    def add_homophones(self, **kwargs: object) -> "Auggie":
        """Trade words for curated homophones via :class:`Ekkokin`."""

        return self._tame(Ekkokin(**kwargs))

    def add_pedant_forms(self, **kwargs: object) -> "Auggie":
        """Apply pedant evolutions orchestrated by :class:`Pedant`."""

        return self._tame(Pedant(**kwargs))

    def add_jargon_swaps(self, **kwargs: object) -> "Auggie":
        """Replace vocabulary with grandiose synonyms through :class:`Jargoyle`."""

        return self._tame(Jargoyle(**kwargs))

    def add_adjacent_swaps(self, **kwargs: object) -> "Auggie":
        """Shuffle neighbouring words using :class:`Adjax`."""

        return self._tame(Adjax(**kwargs))

    def add_word_duplications(self, **kwargs: object) -> "Auggie":
        """Stutter through text with :class:`Reduple` reduplications."""

        return self._tame(Reduple(**kwargs))

    def add_word_remixes(
        self,
        modes: RushmoreMode | str | Iterable[RushmoreMode | str] = "all",
        **kwargs: object,
    ) -> "Auggie":
        """Compose word-level deletions, duplicates, and swaps via :class:`Rushmore`."""

        return self._tame(Rushmore(modes=modes, **kwargs))

    def add_redactions(self, **kwargs: object) -> "Auggie":
        """Obscure words behind blocks summoned by :class:`Redactyl`."""

        return self._tame(Redactyl(**kwargs))

    def add_color_swaps(self, **kwargs: object) -> "Auggie":
        """Invert or drift colour palettes with :class:`Spectroll`."""

        return self._tame(Spectroll(**kwargs))

    def add_ocr_errors(self, **kwargs: object) -> "Auggie":
        """Introduce OCR-inspired slips through :class:`Scannequin`."""

        return self._tame(Scannequin(**kwargs))

    def add_zero_width_marks(self, **kwargs: object) -> "Auggie":
        """Lay invisible zero-width marks courtesy of :class:`Zeedub`."""

        return self._tame(Zeedub(**kwargs))

    def summon(self) -> Gaggle:
        """Return the currently tamed glitchlings as a :class:`Gaggle`."""

        return self._ensure_gaggle()

    @property
    def gaggle(self) -> Gaggle:
        """Expose the lazily constructed gaggle for direct access."""

        return self._ensure_gaggle()

    def __call__(self, text: str | Transcript) -> str | Transcript:
        """Proxy text corruption to the underlying gaggle."""

        return self._ensure_gaggle().corrupt(text)

    def __iter__(self) -> Iterator[Glitchling]:
        return iter(self._glitchlings)

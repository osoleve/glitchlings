"""Laboratory assistant for composing gaggles with behaviour-focused helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Collection, Literal

from .lexicon import Lexicon
from .zoo.adjax import Adjax
from .zoo.apostrofae import Apostrofae
from .zoo.core import Gaggle, Glitchling
from .zoo.ekkokin import Ekkokin
from .zoo.hokey import Hokey
from .zoo.jargoyle import Jargoyle, PartOfSpeechInput
from .zoo.mim1c import Mim1c
from .zoo.pedant import Pedant
from .zoo.pedant.stones import PedantStone
from .zoo.redactyl import FULL_BLOCK, Redactyl
from .zoo.reduple import Reduple
from .zoo.rushmore import Rushmore, RushmoreMode
from .zoo.scannequin import Scannequin
from .zoo.spectroll import Spectroll
from .zoo.typogre import Typogre
from .zoo.zeedub import Zeedub


class Auggie(Gaggle):
    """Assistant that incrementally assembles glitchlings into a gaggle."""

    def __init__(
        self,
        glitchlings: Iterable[Glitchling] | None = None,
        *,
        seed: int = 151,
    ) -> None:
        self._blueprint: list[Glitchling] = []
        initial = list(glitchlings or [])
        super().__init__(initial, seed=seed)
        if initial:
            self._blueprint = [glitchling.clone() for glitchling in initial]
            self._rebuild_plan()
        else:
            self._blueprint = []

    def _rebuild_plan(self) -> None:
        self._clones_by_index = []
        for index, glitchling in enumerate(self._blueprint):
            clone = glitchling.clone()
            setattr(clone, "_gaggle_index", index)
            self._clones_by_index.append(clone)
        self.sort_glitchlings()

    def _enqueue(self, glitchling: Glitchling) -> "Auggie":
        self._blueprint.append(glitchling)
        self._rebuild_plan()
        return self

    def clone(self, seed: int | None = None) -> "Auggie":
        clone_seed = seed if seed is not None else self.seed
        resolved_seed = 151 if clone_seed is None else int(clone_seed)
        blueprint = [glitch.clone() for glitch in self._blueprint]
        return Auggie(blueprint, seed=resolved_seed)

    def typo(
        self,
        *,
        rate: float | None = None,
        keyboard: str = "CURATOR_QWERTY",
        seed: int | None = None,
    ) -> "Auggie":
        """Add :class:`Typogre` using behaviour-driven nomenclature."""

        return self._enqueue(Typogre(rate=rate, keyboard=keyboard, seed=seed))

    def confusable(
        self,
        *,
        rate: float | None = None,
        classes: list[str] | Literal["all"] | None = None,
        banned_characters: Collection[str] | None = None,
        seed: int | None = None,
    ) -> "Auggie":
        """Add :class:`Mim1c` for homoglyph substitutions."""

        return self._enqueue(
            Mim1c(
                rate=rate,
                classes=classes,
                banned_characters=banned_characters,
                seed=seed,
            )
        )

    def curly_quotes(self, *, seed: int | None = None) -> "Auggie":
        """Add :class:`Apostrofae` to smarten punctuation."""

        return self._enqueue(Apostrofae(seed=seed))

    def stretch(
        self,
        *,
        rate: float = 0.3,
        extension_min: int = 2,
        extension_max: int = 5,
        word_length_threshold: int = 6,
        base_p: float = 0.45,
        seed: int | None = None,
    ) -> "Auggie":
        """Add :class:`Hokey` for elongated, expressive words."""

        return self._enqueue(
            Hokey(
                rate=rate,
                extension_min=extension_min,
                extension_max=extension_max,
                word_length_threshold=word_length_threshold,
                base_p=base_p,
                seed=seed,
            )
        )

    def homophone(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
    ) -> "Auggie":
        """Add :class:`Ekkokin` to swap words for homophones."""

        return self._enqueue(Ekkokin(rate=rate, seed=seed))

    def pedantry(
        self,
        *,
        stone: PedantStone | str = PedantStone.COEURITE,
        seed: int | None = None,
    ) -> "Auggie":
        """Add :class:`Pedant` to evolve text via a chosen stone."""

        return self._enqueue(Pedant(stone=stone, seed=seed))

    def remix(
        self,
        *,
        modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None = None,
        rate: float | None = None,
        delete_rate: float | None = None,
        duplicate_rate: float | None = None,
        swap_rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
        delete_unweighted: bool | None = None,
        duplicate_unweighted: bool | None = None,
    ) -> "Auggie":
        """Add :class:`Rushmore` for deletion, duplication, and swap attacks."""

        return self._enqueue(
            Rushmore(
                modes=modes,
                rate=rate,
                delete_rate=delete_rate,
                duplicate_rate=duplicate_rate,
                swap_rate=swap_rate,
                seed=seed,
                unweighted=unweighted,
                delete_unweighted=delete_unweighted,
                duplicate_unweighted=duplicate_unweighted,
            )
        )

    def swap_words(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None = None,
        swap_rate: float | None = None,
        unweighted: bool = False,
    ) -> "Auggie":
        """Add :class:`Adjax` for adjacent word swaps."""

        return self._enqueue(
            Adjax(
                rate=rate,
                seed=seed,
                modes=modes,
                swap_rate=swap_rate,
                unweighted=unweighted,
            )
        )

    def duplicate_words(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
        modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None = None,
        duplicate_rate: float | None = None,
        duplicate_unweighted: bool | None = None,
    ) -> "Auggie":
        """Add :class:`Reduple` for reduplication attacks."""

        return self._enqueue(
            Reduple(
                rate=rate,
                seed=seed,
                unweighted=unweighted,
                modes=modes,
                duplicate_rate=duplicate_rate,
                duplicate_unweighted=duplicate_unweighted,
            )
        )

    def redact(
        self,
        *,
        replacement_char: str = FULL_BLOCK,
        rate: float | None = None,
        merge_adjacent: bool = False,
        seed: int | None = 151,
        unweighted: bool = False,
    ) -> "Auggie":
        """Add :class:`Redactyl` to blackout words."""

        return self._enqueue(
            Redactyl(
                replacement_char=replacement_char,
                rate=rate,
                merge_adjacent=merge_adjacent,
                seed=seed if seed is not None else 151,
                unweighted=unweighted,
            )
        )

    def recolor(self, *, mode: str = "literal", seed: int | None = None) -> "Auggie":
        """Add :class:`Spectroll` to remap colour terms."""

        return self._enqueue(Spectroll(mode=mode, seed=seed))

    def ocr(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
    ) -> "Auggie":
        """Add :class:`Scannequin` to simulate OCR artefacts."""

        return self._enqueue(Scannequin(rate=rate, seed=seed))

    def zero_width(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        characters: Sequence[str] | None = None,
    ) -> "Auggie":
        """Add :class:`Zeedub` to hide zero-width glyphs inside text."""

        return self._enqueue(Zeedub(rate=rate, seed=seed, characters=characters))

    def synonym(
        self,
        *,
        rate: float | None = None,
        part_of_speech: PartOfSpeechInput = "n",
        seed: int | None = None,
        lexicon: Lexicon | None = None,
    ) -> "Auggie":
        """Add :class:`Jargoyle` for synonym substitutions."""

        return self._enqueue(
            Jargoyle(
                rate=rate,
                part_of_speech=part_of_speech,
                seed=seed,
                lexicon=lexicon,
            )
        )


__all__ = ["Auggie"]

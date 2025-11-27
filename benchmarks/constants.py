"""Shared constants and helpers for Glitchlings benchmark utilities."""

from __future__ import annotations

import importlib
from functools import lru_cache
from types import ModuleType
from typing import Dict, List, Tuple

from glitchlings.zoo import get_glitchling_class

Descriptor = Dict[str, object]


@lru_cache(maxsize=None)
def _glitchling_module(name: str) -> ModuleType:
    """Return the module that defines the named glitchling."""
    module_path = get_glitchling_class(name).__module__
    return importlib.import_module(module_path)


def redactyl_full_block() -> str:
    """Expose the Redactyl full block character."""
    return getattr(_glitchling_module("Redactyl"), "FULL_BLOCK")


def zero_width_characters() -> List[str]:
    """Return the default zero-width characters used by Zeedub."""
    characters = getattr(_glitchling_module("Zeedub"), "_DEFAULT_ZERO_WIDTH_CHARACTERS")
    return list(characters)


def keyboard_layout(keyboard: str) -> Dict[str, List[str]]:
    """Return a mutable copy of a named keyboard layout for Typogre."""
    neighbors = getattr(_glitchling_module("Typogre"), "KEYNEIGHBORS")
    layout = getattr(neighbors, keyboard)
    return {key: list(value) for key, value in layout.items()}


OPERATION_MODULES: Dict[str, str] = {
    "reduplicate": "Rushmore",
    "delete": "Rushmore",
    "redact": "Redactyl",
    "ocr": "Scannequin",
    "zwj": "Zeedub",
    "swap_adjacent": "Rushmore",
    "typo": "Typogre",
    "hokey": "Hokey",
    "pedant": "Pedant",
    "ekkokin": "Ekkokin",
    "rushmore_combo": "Rushmore",
    "homoglyph": "Mim1c",
    "synonym": "Jargoyle",
    "homophone": "Ekkokin",
}


PEDANT_STONES: Dict[str, str] = {
    "whomst": "Whom Stone",
    "fewerling": "Fewerite",
    "aetheria": "Coeurite",
    "apostrofae": "Curlite",
    "subjunic": "Subjunctite",
    "commama": "Oxfordium",
    "kiloa": "Metricite",
    "correctopus": "Orthogonite",
}


def module_for_operation(op_type: str) -> ModuleType:
    """Return the module that backs a named pipeline operation."""
    try:
        glitchling_name = OPERATION_MODULES[op_type]
    except KeyError as error:  # pragma: no cover - defensive fallback
        raise KeyError(f"Unknown operation type: {op_type}") from error
    return _glitchling_module(glitchling_name)


BASE_DESCRIPTORS: List[Descriptor] = [
    {
        "name": "Rushmore-Duplicate",
        "operation": {"type": "reduplicate", "rate": 0.01},
    },
    {"name": "Rushmore", "operation": {"type": "delete", "rate": 0.01}},
    {
        "name": "Redactyl",
        "operation": {
            "type": "redact",
            "replacement_char": redactyl_full_block(),
            "rate": 0.05,
            "merge_adjacent": True,
        },
    },
    {"name": "Scannequin", "operation": {"type": "ocr", "rate": 0.02}},
    {
        "name": "Zeedub",
        "operation": {
            "type": "zwj",
            "rate": 0.02,
            "characters": zero_width_characters(),
        },
    },
    {
        "name": "Typogre",
        "operation": {
            "type": "typo",
            "rate": 0.02,
            "keyboard": "CURATOR_QWERTY",
            "layout": keyboard_layout("CURATOR_QWERTY"),
        },
    },
]


SHORT_TEXT = (
    "One morning, when Gregor Samsa woke from troubled dreams, he found himself "
    "transformed in his bed into a horrible vermin."
)
MEDIUM_TEXT = " ".join([SHORT_TEXT] * 32)
LONG_TEXT = " ".join([SHORT_TEXT] * 256)
VERY_LONG_TEXT = " ".join([SHORT_TEXT] * 2048)

DEFAULT_TEXTS: Tuple[Tuple[str, str], ...] = (
    ("short", SHORT_TEXT),
    ("medium", MEDIUM_TEXT),
    ("long", LONG_TEXT),
    ("very_long", VERY_LONG_TEXT),
)

PROJECT_GUTENBERG_TITLES: Tuple[Tuple[str, str], ...] = (
    (
        "the_canterbury_tales",
        "Whan that Aprille with his shoures soote the droghte of March hath perced to "
        "the roote, and bathed every veyne in swich licour of which vertu engendred is "
        "the flour.",
    ),
    (
        "middlemarch",
        "Miss Brooke had that kind of beauty which seems to be thrown into relief by poor "
        "dress; her hand and wrist were so finely formed that she could wear sleeves not "
        "less bare of style than those in which the Blessed Virgin appeared to Italian "
        "painters.",
    ),
    (
        "thus_spoke_zarathustra",
        "When Zarathustra was thirty years old he left his home and the lake of his home "
        "and went into the mountains. There he enjoyed his spirit and his solitude and "
        "for ten years did not weary of it.",
    ),
    (
        "symbolic_logic",
        "Logic is the science of correct argumentation; a calculus of inference whose symbols and "
        "rules allow thought to be tested by exact methods rather than by guesswork alone.",
    ),
    (
        "war_and_peace",
        "Well, Prince, so Genoa and Lucca are now just family estates of the Buonapartes. "
        "But I warn you, if you don't tell me that this means war, if you still try to "
        "defend the infamies and horrors perpetrated by that Antichrist, I really believe "
        "he is Antichrist, I will have nothing more to do with you and you are no longer "
        "my friend, no longer my faithful slave!",
    ),
    (
        "leaves_of_grass",
        "I celebrate myself, and sing myself, and what I assume you shall assume, for every atom "
        "belonging to me as good belongs to you.",
    ),
    (
        "the_importance_of_being_earnest",
        "Did you hear what I was playing, Lane? I didn't think it polite to listen, sir. "
        "I'm sorry for that, for your sake; I don't play accurately—any one can play "
        "accurately—but I play with wonderful expression.",
    ),
    (
        "on_the_origin_of_species",
        "When on board H.M.S. Beagle, as naturalist, I was much struck with certain facts "
        "in the distribution of the inhabitants of South America, and in the geological "
        "relations of the present to the past inhabitants of that continent.",
    ),
    (
        "the_iliad",
        "Sing, O goddess, the anger of Achilles son of Peleus, that brought countless ills "
        "upon the Achaeans; many a brave soul did it send hurrying down to Hades, and many "
        "a hero did it yield a prey to dogs and vultures.",
    ),
    (
        "ulysses",
        "Stately, plump Buck Mulligan came from the stairhead, bearing a bowl of lather on "
        "which a mirror and a razor lay crossed. A yellow dressing gown, ungirdled, was "
        "sustained gently behind him by the mild morning air.",
    ),
    (
        "beowulf_modern_english_prose",
        "So. The Spear-Danes in days gone by and the kings who ruled them had courage and "
        "greatness. We have heard of those princes' heroic campaigns.",
    ),
)

BENCHMARK_CORPORA: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "default": DEFAULT_TEXTS,
    "gutenberg_titles": PROJECT_GUTENBERG_TITLES,
}
DEFAULT_ITERATIONS = 25
MASTER_SEED = 151


SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "baseline": "Default six-glitch pipeline mirroring the public benchmark configuration.",
    "shuffle_mix": "Adds Rushmore's swap mode alongside deletion to stress mixed workloads.",
    "aggressive_cleanup": "Heavy redaction and deletion pass to emulate worst-case sanitisation.",
    "stealth_noise": "Lightweight typo and zero-width noise focused on subtle obfuscations.",
    # Individual glitchling scenarios
    "typogre_only": "Typogre-only benchmark for keyboard neighbor typo injection.",
    "rushmore_delete": "Rushmore delete-only benchmark for word deletion.",
    "rushmore_duplicate": "Rushmore duplicate-only benchmark for word reduplication.",
    "rushmore_swap": "Rushmore swap-only benchmark for adjacent word swapping.",
    "redactyl_only": "Redactyl-only benchmark for character redaction.",
    "scannequin_only": "Scannequin-only benchmark for OCR confusion injection.",
    "zeedub_only": "Zeedub-only benchmark for zero-width character injection.",
    "mim1c_only": "Mim1c-only benchmark for homoglyph substitution.",
    "ekkokin_only": "Ekkokin-only benchmark for homophone substitution.",
    "hokey_only": "Hokey-only benchmark for expressive lengthening.",
    "jargoyle_only": "Jargoyle-only benchmark for dictionary-based synonym substitution.",
    # Pedant evolution scenarios
    "pedant_whomst": "Pedant Whomst benchmark for who→whom correction.",
    "pedant_fewerling": "Pedant Fewerling benchmark for less→fewer correction.",
    "pedant_aetheria": "Pedant Aetheria benchmark for ligature and diaeresis restoration.",
    "pedant_apostrofae": "Pedant Apostrofae benchmark for curly quote normalization.",
    "pedant_subjunic": "Pedant Subjunic benchmark for subjunctive correction.",
    "pedant_commama": "Pedant Commama benchmark for Oxford comma insertion.",
    "pedant_kiloa": "Pedant Kiloa benchmark for imperial→metric conversion.",
    "pedant_correctopus": "Pedant Correctopus benchmark for uppercase transformation.",
}


__all__ = [
    "Descriptor",
    "OPERATION_MODULES",
    "PEDANT_STONES",
    "module_for_operation",
    "BASE_DESCRIPTORS",
    "DEFAULT_ITERATIONS",
    "DEFAULT_TEXTS",
    "PROJECT_GUTENBERG_TITLES",
    "BENCHMARK_CORPORA",
    "MASTER_SEED",
    "SCENARIO_DESCRIPTIONS",
    "SHORT_TEXT",
    "MEDIUM_TEXT",
    "LONG_TEXT",
    "VERY_LONG_TEXT",
    "redactyl_full_block",
    "zero_width_characters",
    "keyboard_layout",
]

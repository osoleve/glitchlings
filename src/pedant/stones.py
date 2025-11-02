"""Evolution stones recognised by the pedant."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stone:
    """Descriptor for an evolution stone."""

    name: str
    type: str
    effect: str


STONES = {
    "Whom Stone": Stone("Whom Stone", "Ghost", "Encourages object-pronoun precision."),
    "Fewerite": Stone("Fewerite", "Fairy", "Obsesses over countable quantities."),
    "Aetherite": Stone("Aetherite", "Psychic", "Restores archaic ligatures to modern words."),
    "Subjunctite": Stone("Subjunctite", "Psychic", "Demands contrary-to-fact phrasing."),
    "Oxfordium": Stone("Oxfordium", "Steel", "Polishes serial comma usage."),
    "Orthogonite": Stone("Orthogonite", "Dragon", "Unlocks the legendary Pedagorgon."),
    "Metricite": Stone("Metricite", "Electric", "Compels metrication of measures."),
}


from __future__ import annotations

import ast
from typing import Any

from .core import Gaggle, Glitchling, plan_glitchlings
from .hokey import Hokey, hokey
from .jargoyle import Jargoyle, jargoyle
from .mim1c import Mim1c, mim1c
from .pedant import Pedant, pedant
from .redactyl import Redactyl, redactyl
from .rushmore import Rushmore, RushmoreMode, rushmore
from .scannequin import Scannequin, scannequin
from .typogre import Typogre, typogre
from .wherewolf import Wherewolf, wherewolf
from .zeedub import Zeedub, zeedub

__all__ = [
    "Typogre",
    "typogre",
    "Mim1c",
    "mim1c",
    "Jargoyle",
    "jargoyle",
    "Wherewolf",
    "wherewolf",
    "Hokey",
    "hokey",
    "Rushmore",
    "RushmoreMode",
    "rushmore",
    "Redactyl",
    "redactyl",
    "Scannequin",
    "scannequin",
    "Zeedub",
    "zeedub",
    "Pedant",
    "pedant",
    "Glitchling",
    "Gaggle",
    "plan_glitchlings",
    "summon",
    "BUILTIN_GLITCHLINGS",
    "DEFAULT_GLITCHLING_NAMES",
    "parse_glitchling_spec",
    "get_glitchling_class",
]

_BUILTIN_GLITCHLING_LIST: list[Glitchling] = [
    typogre,
    hokey,
    mim1c,
    wherewolf,
    pedant,
    jargoyle,
    rushmore,
    redactyl,
    scannequin,
    zeedub,
]

BUILTIN_GLITCHLINGS: dict[str, Glitchling] = {
    glitchling.name.lower(): glitchling for glitchling in _BUILTIN_GLITCHLING_LIST
}

_BUILTIN_GLITCHLING_TYPES: dict[str, type[Glitchling]] = {
    typogre.name.lower(): Typogre,
    wherewolf.name.lower(): Wherewolf,
    hokey.name.lower(): Hokey,
    mim1c.name.lower(): Mim1c,
    pedant.name.lower(): Pedant,
    jargoyle.name.lower(): Jargoyle,
    rushmore.name.lower(): Rushmore,
    redactyl.name.lower(): Redactyl,
    scannequin.name.lower(): Scannequin,
    zeedub.name.lower(): Zeedub,
}

DEFAULT_GLITCHLING_NAMES: list[str] = ["typogre", "scannequin"]


def parse_glitchling_spec(specification: str) -> Glitchling:
    """Return a glitchling instance configured according to ``specification``."""
    text = specification.strip()
    if not text:
        raise ValueError("Glitchling specification cannot be empty.")

    if "(" not in text:
        glitchling = BUILTIN_GLITCHLINGS.get(text.lower())
        if glitchling is None:
            raise ValueError(f"Glitchling '{text}' not found.")
        return glitchling

    if not text.endswith(")"):
        raise ValueError(f"Invalid parameter syntax for glitchling '{text}'.")

    name_part, arg_source = text[:-1].split("(", 1)
    name = name_part.strip()
    if not name:
        raise ValueError(f"Invalid glitchling specification '{text}'.")

    lower_name = name.lower()
    glitchling_type = _BUILTIN_GLITCHLING_TYPES.get(lower_name)
    if glitchling_type is None:
        raise ValueError(f"Glitchling '{name}' not found.")

    try:
        call_expr = ast.parse(f"_({arg_source})", mode="eval").body
    except SyntaxError as exc:
        raise ValueError(f"Invalid parameter syntax for glitchling '{name}': {exc.msg}") from exc

    if not isinstance(call_expr, ast.Call) or call_expr.args:
        raise ValueError(f"Glitchling '{name}' parameters must be provided as keyword arguments.")

    kwargs: dict[str, Any] = {}
    for keyword in call_expr.keywords:
        if keyword.arg is None:
            raise ValueError(
                f"Glitchling '{name}' does not support unpacking arbitrary keyword arguments."
            )
        try:
            kwargs[keyword.arg] = ast.literal_eval(keyword.value)
        except (ValueError, SyntaxError) as exc:
            raise ValueError(
                f"Failed to parse value for parameter '{keyword.arg}' on glitchling '{name}': {exc}"
            ) from exc

    try:
        return glitchling_type(**kwargs)
    except TypeError as exc:
        raise ValueError(f"Failed to instantiate glitchling '{name}': {exc}") from exc


def get_glitchling_class(name: str) -> type[Glitchling]:
    """Look up the glitchling class registered under ``name``."""
    key = name.strip().lower()
    if not key:
        raise ValueError("Glitchling name cannot be empty.")

    glitchling_type = _BUILTIN_GLITCHLING_TYPES.get(key)
    if glitchling_type is None:
        raise ValueError(f"Glitchling '{name}' not found.")

    return glitchling_type


def summon(glitchlings: list[str | Glitchling], seed: int = 151) -> Gaggle:
    """Summon glitchlings by name (using defaults) or instance (to change parameters)."""
    summoned: list[Glitchling] = []
    for entry in glitchlings:
        if isinstance(entry, Glitchling):
            summoned.append(entry)
            continue

        try:
            summoned.append(parse_glitchling_spec(entry))
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    return Gaggle(summoned, seed=seed)

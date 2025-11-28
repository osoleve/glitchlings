"""Pure text transformation functions.

This module contains text manipulation functions that are:
- **Pure**: Output depends only on inputs, no side effects
- **Deterministic**: Same inputs always produce same outputs
- **Self-contained**: No RNG, no Rust FFI, no config loading

These functions receive pre-validated inputs from boundary layers
(see validation.py) and trust that inputs are already checked.
Core transformation code should NOT re-validate parameters.

Design Philosophy
-----------------
This module implements the innermost layer of the purity architecture:

    CLI/API → validation.py → transforms.py → Rust FFI
    (boundary)   (boundary)     (pure core)    (impure)

Functions here should:
- Accept concrete types (not Optional unless semantically required)
- Not log, print, or mutate external state
- Not import impure modules (internal.rust, config loaders, etc.)
- Document any preconditions callers must satisfy

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeVar, cast

# ---------------------------------------------------------------------------
# Text Tokenization
# ---------------------------------------------------------------------------

_WORD_SPLIT_PATTERN = re.compile(r"(\s+)")
_TOKEN_EDGES_PATTERN = re.compile(r"^(\W*)(.*?)(\W*)$", re.DOTALL)


def split_preserving_whitespace(text: str) -> list[str]:
    """Split text while keeping whitespace tokens for stable reconstruction.

    Returns alternating [word, whitespace, word, whitespace, ...] tokens.
    Joining the result reconstructs the original text exactly.

    Args:
        text: Input text to tokenize.

    Returns:
        List of tokens alternating between non-whitespace and whitespace.

    Example:
        >>> split_preserving_whitespace("hello  world")
        ['hello', '  ', 'world']
    """
    return _WORD_SPLIT_PATTERN.split(text)


def split_token_edges(token: str) -> tuple[str, str, str]:
    """Decompose a token into leading punctuation, core, and trailing punctuation.

    Args:
        token: A non-whitespace token.

    Returns:
        Tuple of (prefix, core, suffix) where:
        - prefix: leading non-word characters
        - core: central word characters
        - suffix: trailing non-word characters

    Example:
        >>> split_token_edges('"Hello!"')
        ('"', 'Hello', '!"')
    """
    match = cast(re.Match[str], _TOKEN_EDGES_PATTERN.match(token))
    prefix, core, suffix = match.groups()
    return prefix, core, suffix


def compute_core_length(token: str) -> int:
    """Compute the effective length of a token's core for weighting heuristics.

    Used by weighted sampling algorithms to prioritize longer words.
    Always returns at least 1 to avoid zero-weight issues.

    Args:
        token: A non-whitespace token.

    Returns:
        Positive integer representing the token's effective length.
    """
    _, core, _ = split_token_edges(token)
    if core:
        return len(core)
    stripped = token.strip()
    if stripped:
        return len(stripped)
    if token:
        return len(token)
    return 1


@dataclass(frozen=True)
class WordToken:
    """Metadata describing a non-whitespace token from text tokenization.

    Attributes:
        index: Position in the parent token sequence.
        prefix: Leading non-word characters (punctuation).
        core: Central word characters.
        suffix: Trailing non-word characters (punctuation).
        core_length: Effective length for weighting (always >= 1).
    """

    index: int
    prefix: str
    core: str
    suffix: str
    core_length: int

    @property
    def has_core(self) -> bool:
        """Return True when the token contains at least one core character."""
        return bool(self.core)


def collect_word_tokens(
    tokens: Sequence[str],
    *,
    skip_first_word: bool = False,
) -> list[WordToken]:
    """Extract structured metadata for non-whitespace tokens.

    Args:
        tokens: Token sequence from split_preserving_whitespace.
        skip_first_word: If True, exclude the first content token
            (useful for preserving leading words in delete operations).

    Returns:
        List of WordToken instances for each non-whitespace token.
    """
    start = 2 if skip_first_word else 0
    collected: list[WordToken] = []

    for index in range(start, len(tokens), 2):
        token = tokens[index]
        if not token or token.isspace():
            continue

        prefix, core, suffix = split_token_edges(token)
        core_length = compute_core_length(token)

        collected.append(
            WordToken(
                index=index,
                prefix=prefix,
                core=core,
                suffix=suffix,
                core_length=core_length,
            )
        )

    return collected


def reassemble_tokens(tokens: Sequence[str]) -> str:
    """Join tokens back into text, preserving original structure.

    Args:
        tokens: Token sequence (typically modified from split_preserving_whitespace).

    Returns:
        Reassembled text string.
    """
    return "".join(tokens)


# ---------------------------------------------------------------------------
# Keyboard Layout Processing
# ---------------------------------------------------------------------------


KeyNeighborMap = dict[str, list[str]]


def build_keyboard_neighbor_map(rows: Iterable[str]) -> KeyNeighborMap:
    """Derive 8-neighbour adjacency lists from keyboard layout rows.

    Each row represents a keyboard row with characters positioned by index.
    Spaces are treated as empty positions. Characters are normalized to lowercase.

    Args:
        rows: Iterable of strings representing keyboard rows, with
            characters positioned to reflect their physical layout.

    Returns:
        Dictionary mapping each lowercase character to its adjacent characters.

    Example:
        >>> rows = ["qwerty", " asdfg"]  # 'a' offset by 1
        >>> neighbors = build_keyboard_neighbor_map(rows)
        >>> neighbors['s']  # adjacent to q, w, e, a, d on QWERTY
        ['q', 'w', 'e', 'a', 'd']
    """
    grid: dict[tuple[int, int], str] = {}
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == " ":
                continue
            grid[(x, y)] = char.lower()

    neighbors: KeyNeighborMap = {}
    for (x, y), char in grid.items():
        seen: list[str] = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                candidate = grid.get((x + dx, y + dy))
                if candidate is None:
                    continue
                seen.append(candidate)
        # Preserve encounter order but drop duplicates for determinism
        deduped = list(dict.fromkeys(seen))
        neighbors[char] = deduped

    return neighbors


# ---------------------------------------------------------------------------
# String Difference Computation
# ---------------------------------------------------------------------------


def compute_string_diffs(
    original: str,
    modified: str,
) -> list[list[tuple[str, str, str]]]:
    """Compare two strings and return grouped adjacent change operations.

    Uses difflib's SequenceMatcher to identify changes between strings.
    Consecutive changes are grouped together; equal regions are skipped.

    Args:
        original: The original string.
        modified: The modified string.

    Returns:
        List of change groups. Each group is a list of (tag, old_text, new_text)
        tuples where tag is 'replace', 'delete', or 'insert'.

    Example:
        >>> compute_string_diffs("hello world", "helo worlds")
        [[('delete', 'l', '')], [('replace', '', 's')]]
    """
    import difflib

    sm = difflib.SequenceMatcher(None, original, modified)
    ops: list[list[tuple[str, str, str]]] = []
    buffer: list[tuple[str, str, str]] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            if buffer:
                ops.append(buffer)
                buffer = []
            continue
        buffer.append((tag, original[i1:i2], modified[j1:j2]))

    if buffer:
        ops.append(buffer)

    return ops


# ---------------------------------------------------------------------------
# Sequence Operations
# ---------------------------------------------------------------------------

T = TypeVar("T")


def stable_deduplicate(items: Iterable[T]) -> list[T]:
    """Remove duplicates while preserving original order.

    Args:
        items: Iterable of hashable items.

    Returns:
        List with duplicates removed, first occurrence preserved.

    Example:
        >>> stable_deduplicate([3, 1, 4, 1, 5, 9, 2, 6, 5])
        [3, 1, 4, 5, 9, 2, 6]
    """
    seen: set[T] = set()
    result: list[T] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def interleave_lists(
    primary: Sequence[T],
    secondary: Sequence[T],
    *,
    secondary_first: bool = False,
) -> list[T]:
    """Interleave two sequences, padding shorter with empty slots.

    Args:
        primary: First sequence.
        secondary: Second sequence.
        secondary_first: If True, start with secondary element.

    Returns:
        Interleaved list [p0, s0, p1, s1, ...] or [s0, p0, s1, p1, ...].
    """
    result: list[T] = []
    max_len = max(len(primary), len(secondary))

    for i in range(max_len):
        if secondary_first:
            if i < len(secondary):
                result.append(secondary[i])
            if i < len(primary):
                result.append(primary[i])
        else:
            if i < len(primary):
                result.append(primary[i])
            if i < len(secondary):
                result.append(secondary[i])

    return result


# ---------------------------------------------------------------------------
# Mapping Helpers
# ---------------------------------------------------------------------------


def invert_mapping(
    mapping: Mapping[str, Sequence[str]],
) -> dict[str, str]:
    """Invert a one-to-many mapping into a many-to-one lookup.

    Given {key: [val1, val2]}, returns {val1: key, val2: key}.
    Later keys overwrite earlier ones if values collide.

    Args:
        mapping: Dictionary mapping keys to sequences of values.

    Returns:
        Inverted dictionary mapping each value to its key.
    """
    inverted: dict[str, str] = {}
    for key, values in mapping.items():
        for value in values:
            inverted[value] = key
    return inverted


__all__ = [
    # Tokenization
    "split_preserving_whitespace",
    "split_token_edges",
    "compute_core_length",
    "WordToken",
    "collect_word_tokens",
    "reassemble_tokens",
    # Keyboard
    "KeyNeighborMap",
    "build_keyboard_neighbor_map",
    # Diffs
    "compute_string_diffs",
    # Sequences
    "stable_deduplicate",
    "interleave_lists",
    # Mappings
    "invert_mapping",
]

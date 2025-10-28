"""Utilities for handling optional rate-style parameters across glitchling classes."""

from __future__ import annotations


def resolve_rate(
    *,
    rate: float | None,
    default: float,
) -> float:
    """Return the provided rate value or fall back to ``default``.

    Parameters
    ----------
    rate : float | None
        The preferred parameter value.
    default : float
        Default value if neither parameter is specified.

    Returns
    -------
    float
        ``rate`` when provided, otherwise ``default``.

    Examples
    --------
    >>> resolve_rate(rate=0.5, default=0.1)
    0.5
    >>> resolve_rate(rate=None, default=0.1)
    0.1

    """
    if rate is not None:
        return rate

    return default

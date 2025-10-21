"""Utilities for handling legacy parameter names across glitchling classes."""

from __future__ import annotations

import warnings


def resolve_rate(
    *,
    rate: float | None,
    legacy_value: float | None,
    default: float,
    legacy_name: str,
) -> float:
    """Return the effective rate while enforcing mutual exclusivity.

    This function centralizes the handling of legacy parameter names, allowing
    glitchlings to maintain backwards compatibility while encouraging migration
    to the standardized 'rate' parameter.

    Parameters
    ----------
    rate : float | None
        The preferred parameter value.
    legacy_value : float | None
        The deprecated legacy parameter value.
    default : float
        Default value if neither parameter is specified.
    legacy_name : str
        Name of the legacy parameter for error/warning messages.

    Returns
    -------
    float
        The resolved rate value.

    Raises
    ------
    ValueError
        If both rate and legacy_value are specified simultaneously.

    Warnings
    --------
    DeprecationWarning
        If the legacy parameter is used, a deprecation warning is issued.

    Examples
    --------
    >>> resolve_rate(rate=0.5, legacy_value=None, default=0.1, legacy_name="old_rate")
    0.5
    >>> resolve_rate(rate=None, legacy_value=0.3, default=0.1, legacy_name="old_rate")
    0.3  # Issues deprecation warning
    >>> resolve_rate(rate=None, legacy_value=None, default=0.1, legacy_name="old_rate")
    0.1

    """
    if rate is not None and legacy_value is not None:
        raise ValueError(f"Specify either 'rate' or '{legacy_name}', not both.")

    if rate is not None:
        return rate

    if legacy_value is not None:
        warnings.warn(
            f"The '{legacy_name}' parameter is deprecated and will be removed in version 0.6.0. "
            f"Use 'rate' instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return legacy_value

    return default


def resolve_legacy_param(
    *,
    preferred_value: object,
    legacy_value: object,
    default: object,
    preferred_name: str,
    legacy_name: str,
) -> object:
    """Resolve a parameter that has both preferred and legacy names.

    This is a generalized version of resolve_rate() that works with any type.

    Parameters
    ----------
    preferred_value : object
        The value from the preferred parameter name.
    legacy_value : object
        The value from the legacy parameter name.
    default : object
        Default value if neither parameter is specified.
    preferred_name : str
        Name of the preferred parameter.
    legacy_name : str
        Name of the legacy parameter for warning messages.

    Returns
    -------
    object
        The resolved parameter value.

    Raises
    ------
    ValueError
        If both preferred and legacy values are specified simultaneously.

    Warnings
    --------
    DeprecationWarning
        If the legacy parameter is used.

    """
    if preferred_value is not None and legacy_value is not None:
        raise ValueError(f"Specify either '{preferred_name}' or '{legacy_name}', not both.")

    if preferred_value is not None:
        return preferred_value

    if legacy_value is not None:
        warnings.warn(
            f"The '{legacy_name}' parameter is deprecated and will be removed in version 0.6.0. "
            f"Use '{preferred_name}' instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return legacy_value

    return default

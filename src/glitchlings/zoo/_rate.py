from __future__ import annotations


def resolve_rate(
    *,
    rate: float | None,
    legacy_value: float | None,
    default: float,
    legacy_name: str,
) -> float:
    """Return the effective rate while enforcing mutual exclusivity."""

    if rate is not None and legacy_value is not None:
        raise ValueError(
            f"Specify either 'rate' or '{legacy_name}', not both."
        )
    if rate is not None:
        return rate
    if legacy_value is not None:
        return legacy_value
    return default

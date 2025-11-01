"""Small demonstration script for the Spectroll glitchling."""

from __future__ import annotations

from glitchlings import summon
from glitchlings.spectroll import Spectroll, swap_colors


def main() -> None:
    sample = "The red balloon and green kite soared above the blue river."

    print("Original:     ", sample)
    print("Literal swap: ", swap_colors(sample))
    print("Drift swap:   ", swap_colors(sample, mode="drift", seed=7))

    gaggle = summon(['Spectroll(mode="drift")'], seed=404)
    print("Gaggle drift: ", gaggle(sample))

    spectroll = Spectroll(mode="literal", seed=99)
    print("Glitchling literal:", spectroll(sample))


if __name__ == "__main__":
    main()

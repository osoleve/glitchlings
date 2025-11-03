from __future__ import annotations

from glitchlings import Auggie, Ekkokin, Gaggle, Mim1c, Typogre


def test_auggie_matches_direct_gaggle() -> None:
    sample = "One morning, Gregor woke up wrong."
    auggie = Auggie(seed=7).add_typos(rate=0.2).add_homophones(rate=0.5)
    direct = Gaggle([Typogre(rate=0.2), Ekkokin(rate=0.5)], seed=7)

    assert auggie(sample) == direct(sample)


def test_auggie_updates_gaggle_after_additions() -> None:
    auggie = Auggie(seed=11).add_typos(rate=0.1)
    first = auggie.summon()
    assert len(first.apply_order) == 1

    auggie.add_confusables(rate=0.1)
    second = auggie.summon()
    assert len(second.apply_order) == 2
    assert any(isinstance(glitch, Mim1c) for glitch in second.apply_order)


def test_auggie_seed_mutation_updates_gaggle() -> None:
    auggie = Auggie(seed=3).add_typos(rate=0.2)
    assert auggie.summon().seed == 3

    auggie.set_seed(9)
    assert auggie.summon().seed == 9

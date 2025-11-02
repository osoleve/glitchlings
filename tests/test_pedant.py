import pytest

from pedant.core import Pedant
from pedant.forms import Aetherial
from pedant.items import StyleGuide

SAMPLE_TEXT = (
    "It is I who am here. We have 10 waters or less. "
    "Please cooperate on these aesthetics."
)


def test_evolve_with_whom_stone():
    pedant = Pedant(seed=42)
    evolved = pedant.evolve("Whom Stone")
    output = evolved.move("It is I who am here.")
    assert "It is I whom am here" in output


def test_evolve_with_fewerite():
    pedant = Pedant(seed=7)
    evolved = pedant.evolve("Fewerite")
    output = evolved.move("We have 10 waters or less.")
    assert "10 waters or fewer" in output


def test_evolve_with_aetherite():
    pedant = Pedant(seed=9)
    evolved = pedant.evolve("Aetherite")
    output = evolved.move("We cooperate on aesthetic archaeology.")
    assert "coöperate" in output
    assert "æ" in output


def test_aetherial_ligature_handles_title_case():
    pedant = Pedant(seed=9).evolve("Aetherite")
    output = pedant.move("Aether lore beckons.")
    assert "Æther" in output


def test_aetherial_ligature_handles_uppercase_pair():
    pedant = Pedant(seed=9).evolve("Aetherite")
    assert pedant.move("AE") == "Æ"


def test_aetherial_diaeresis_handles_title_case_pair():
    form = Aetherial(seed=9)
    assert form._apply_diaeresis("Oolong") == "Oölong"


def test_evolution_determinism_same_seed():
    pedant_one = Pedant(seed=11).evolve("Aetherite")
    pedant_two = Pedant(seed=11).evolve("Aetherite")
    text = "Coordinate cooperative efforts across aesthetic areas."
    assert pedant_one.move(text) == pedant_two.move(text)


def test_evolution_determinism_different_seeds():
    pedant_one = Pedant(seed=11).evolve("Aetherite")
    pedant_two = Pedant(seed=12).evolve("Aetherite")
    text = "Coordinate cooperative efforts across aesthetic areas."
    assert pedant_one.move(text) != pedant_two.move(text)


def test_style_guide_prevents_evolution():
    pedant = Pedant(seed=17)
    pedant.give_item(StyleGuide())
    with pytest.raises(RuntimeError):
        pedant.evolve("Whom Stone")


def test_item_consumption_on_use():
    pedant = Pedant(seed=17)
    pedant.give_item(StyleGuide())
    with pytest.raises(RuntimeError):
        pedant.evolve("Whom Stone")
    assert not pedant.items


def test_whomst_move_transformation():
    pedant = Pedant(seed=21).evolve("Whom Stone")
    assert pedant.move("Who is there?") == "Whom is there?"

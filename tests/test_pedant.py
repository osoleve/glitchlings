import pytest

from glitchlings.zoo.pedant import Pedant, PedantBase, PedantStone
from glitchlings.zoo.pedant.forms import Aetheria

SAMPLE_TEXT = (
    "It is I who am here. We have 10 waters or less. Please cooperate on these aesthetics."
)


def test_evolve_with_whom_stone():
    pedant = PedantBase(seed=42)
    evolved = pedant.evolve(PedantStone.WHOM)
    output = evolved.move("It is I who am here.")
    assert "It is I whom am here" in output


def test_evolve_with_fewerite():
    pedant = PedantBase(seed=7)
    evolved = pedant.evolve(PedantStone.FEWERITE)
    output = evolved.move("We have 10 waters or less.")
    assert "10 waters or fewer" in output


def test_evolve_with_coeurite():
    pedant = PedantBase(seed=9)
    evolved = pedant.evolve(PedantStone.COEURITE)
    output = evolved.move("We cooperate on aesthetic archaeology.")
    assert "coöperate" in output
    assert "æ" in output


def test_aetheria_ligature_handles_title_case():
    pedant = PedantBase(seed=9).evolve(PedantStone.COEURITE)
    output = pedant.move("Aether lore beckons.")
    assert "Æther" in output


def test_aetheria_ligature_handles_uppercase_pair():
    pedant = PedantBase(seed=9).evolve(PedantStone.COEURITE)
    assert pedant.move("AE") == "Æ"


def test_aetheria_diaeresis_handles_title_case_pair():
    form = Aetheria(seed=9)
    assert form._apply_diaeresis("Oolong") == "Oölong"


def test_evolution_determinism_same_seed():
    pedant_one = PedantBase(seed=11).evolve(PedantStone.COEURITE)
    pedant_two = PedantBase(seed=11).evolve(PedantStone.COEURITE)
    text = "Coordinate cooperative efforts across aesthetic areas."
    assert pedant_one.move(text) == pedant_two.move(text)


def test_evolution_determinism_different_seeds():
    pedant_one = PedantBase(seed=5).evolve(PedantStone.COEURITE)
    pedant_two = PedantBase(seed=9).evolve(PedantStone.COEURITE)
    text = "Coordinate cooperative efforts across aesthetic areas."
    assert pedant_one.move(text) != pedant_two.move(text)


def test_whomst_move_transformation():
    pedant = PedantBase(seed=21).evolve(PedantStone.WHOM)
    assert pedant.move("Who is there?") == "Whom is there?"


@pytest.mark.parametrize("stone_input", [PedantStone.WHOM, "Whom Stone"])
def test_pedant_glitch_applies_selected_stone(stone_input):
    glitch = Pedant(stone=stone_input, seed=21)
    assert glitch("Who was that?") == "Whom was that?"


def test_pedant_pipeline_descriptor_includes_stone_label():
    glitch = Pedant(stone=PedantStone.COEURITE, seed=5)
    descriptor = glitch.pipeline_operation()
    assert descriptor == {"type": "pedant", "stone": PedantStone.COEURITE.label}


def test_subjunic_corrects_subjunctive():
    pedant = PedantBase(seed=31).evolve(PedantStone.SUBJUNCTITE)
    text = "If I was prepared, we would thrive."
    expected = "If I were prepared, we would thrive."
    assert pedant.move(text) == expected


def test_serial_comma_adds_missing_delimiter():
    pedant = PedantBase(seed=43).evolve(PedantStone.OXFORDIUM)
    text = "Invite apples, pears and bananas."
    expected = "Invite apples, pears, and bananas."
    assert pedant.move(text) == expected


def test_serial_comma_respects_existing_delimiter():
    pedant = PedantBase(seed=43).evolve(PedantStone.OXFORDIUM)
    original = "Invite apples, pears, and bananas."
    assert pedant.move(original) == original


def test_oxforda_converts_miles_to_kilometres():
    pedant = PedantBase(seed=19).evolve(PedantStone.METRICITE)
    assert pedant.move("The trail spans 5 miles.") == "The trail spans 8 kilometres."


def test_pedagorgon_uppercases_text():
    pedant = PedantBase(seed=7).evolve(PedantStone.ORTHOGONITE)
    assert pedant.move("Quiet edits now.") == "QUIET EDITS NOW."

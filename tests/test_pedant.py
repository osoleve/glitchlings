import pytest

from glitchlings.zoo.pedant import (
    CopyeditBadge,
    Pedant,
    PedantBase,
    StyleGuide,
    pedant_transform,
)
from glitchlings.zoo.pedant.forms import Aetherial

SAMPLE_TEXT = (
    "It is I who am here. We have 10 waters or less. "
    "Please cooperate on these aesthetics."
)


def test_evolve_with_whom_stone():
    pedant = PedantBase(seed=42)
    evolved = pedant.evolve("Whom Stone")
    output = evolved.move("It is I who am here.")
    assert "It is I whom am here" in output


def test_evolve_with_fewerite():
    pedant = PedantBase(seed=7)
    evolved = pedant.evolve("Fewerite")
    output = evolved.move("We have 10 waters or less.")
    assert "10 waters or fewer" in output


def test_evolve_with_aetherite():
    pedant = PedantBase(seed=9)
    evolved = pedant.evolve("Aetherite")
    output = evolved.move("We cooperate on aesthetic archaeology.")
    assert "coöperate" in output
    assert "æ" in output


def test_aetherial_ligature_handles_title_case():
    pedant = PedantBase(seed=9).evolve("Aetherite")
    output = pedant.move("Aether lore beckons.")
    assert "Æther" in output


def test_aetherial_ligature_handles_uppercase_pair():
    pedant = PedantBase(seed=9).evolve("Aetherite")
    assert pedant.move("AE") == "Æ"


def test_aetherial_diaeresis_handles_title_case_pair():
    form = Aetherial(seed=9)
    assert form._apply_diaeresis("Oolong") == "Oölong"


def test_evolution_determinism_same_seed():
    pedant_one = PedantBase(seed=11).evolve("Aetherite")
    pedant_two = PedantBase(seed=11).evolve("Aetherite")
    text = "Coordinate cooperative efforts across aesthetic areas."
    assert pedant_one.move(text) == pedant_two.move(text)


def test_evolution_determinism_different_seeds():
    pedant_one = PedantBase(seed=11).evolve("Aetherite")
    pedant_two = PedantBase(seed=12).evolve("Aetherite")
    text = "Coordinate cooperative efforts across aesthetic areas."
    assert pedant_one.move(text) != pedant_two.move(text)


def test_style_guide_prevents_evolution():
    pedant = PedantBase(seed=17)
    pedant.give_item(StyleGuide())
    with pytest.raises(RuntimeError):
        pedant.evolve("Whom Stone")


def test_item_consumption_on_use():
    pedant = PedantBase(seed=17)
    pedant.give_item(StyleGuide())
    with pytest.raises(RuntimeError):
        pedant.evolve("Whom Stone")
    assert not pedant.items


def test_whomst_move_transformation():
    pedant = PedantBase(seed=21).evolve("Whom Stone")
    assert pedant.move("Who is there?") == "Whom is there?"


def test_pedant_glitch_applies_selected_stone():
    glitch = Pedant(stone="Whom Stone", seed=21)
    assert glitch("Who was that?") == "Whom was that?"


def test_pedant_transform_respects_style_guide():
    with pytest.raises(RuntimeError):
        pedant_transform("Who is there?", stone="Whom Stone", seed=99, items=["Style Guide"])


def test_pedant_pipeline_descriptor_includes_items():
    glitch = Pedant(stone="Aetherite", items=["Copyedit Badge"], seed=5)
    descriptor = glitch.pipeline_operation()
    assert descriptor == {
        "type": "pedant",
        "stone": "Aetherite",
        "items": ["Copyedit Badge"],
    }


def test_subjunic_corrects_subjunctive():
    pedant = PedantBase(seed=31).evolve("Subjunctite")
    text = "If I was prepared, we would thrive."
    expected = "If I were prepared, we would thrive."
    assert pedant.move(text) == expected


def test_serial_comma_adds_missing_delimiter():
    pedant = PedantBase(seed=43).evolve("Oxfordium")
    text = "Invite apples, pears and bananas."
    expected = "Invite apples, pears, and bananas."
    assert pedant.move(text) == expected


def test_serial_comma_respects_existing_delimiter():
    pedant = PedantBase(seed=43).evolve("Oxfordium")
    original = "Invite apples, pears, and bananas."
    assert pedant.move(original) == original


def test_oxforda_converts_miles_to_kilometres():
    pedant = PedantBase(seed=19).evolve("Metricite")
    assert pedant.move("The trail spans 5 miles.") == "The trail spans 8 kilometres."


def test_pedagorgon_uppercases_text():
    pedant = PedantBase(seed=7).evolve("Orthogonite")
    assert pedant.move("Quiet edits now.") == "QUIET EDITS NOW."


def test_pedant_transform_accepts_item_instances():
    badge = CopyeditBadge()
    result = pedant_transform("Who will help?", stone="Whom Stone", seed=55, items=[badge])
    assert result == "Whom will help?"

import pytest

from glitchlings.zoo.pedant import Pedant, PedantBase, PedantStone


class TestAndi:
    """Tests for Hypercorrectite -> Andi (coordinate pronoun hypercorrection)."""

    def test_between_you_and_me(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.HYPERCORRECTITE)
        result = pedant.move("between you and me")
        assert result == "between you and I"

    def test_for_noun_and_me(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.HYPERCORRECTITE)
        result = pedant.move("for Bob and me")
        assert result == "for Bob and I"

    def test_to_pronoun_and_me(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.HYPERCORRECTITE)
        result = pedant.move("give it to her and me")
        assert result == "give it to her and I"

    def test_me_and_noun(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.HYPERCORRECTITE)
        result = pedant.move("with me and my friends")
        assert result == "with I and my friends"

    def test_subject_position_unchanged(self):
        """Subject position should not be affected - no preposition trigger."""
        pedant = PedantBase(seed=42).evolve(PedantStone.HYPERCORRECTITE)
        result = pedant.move("You and me went to the store")
        assert result == "You and me went to the store"

    def test_no_coordinate_unchanged(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.HYPERCORRECTITE)
        result = pedant.move("give it to me")
        assert result == "give it to me"

    def test_case_preservation_uppercase(self):
        """Note: 'and' becomes lowercase in output as it's part of the format string."""
        pedant = PedantBase(seed=42).evolve(PedantStone.HYPERCORRECTITE)
        result = pedant.move("BETWEEN YOU AND ME")
        # The transformation preserves prep and noun case, but 'and' becomes lowercase
        assert result == "BETWEEN YOU and I"


class TestInfinitoad:
    """Tests for Unsplittium -> Infinitoad (split infinitive correction)."""

    def test_to_boldly_go(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.UNSPLITTIUM)
        result = pedant.move("to boldly go")
        assert result in ["boldly to go", "to go boldly"]

    def test_to_really_understand(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.UNSPLITTIUM)
        result = pedant.move("to really understand")
        assert result in ["really to understand", "to understand really"]

    def test_determinism(self):
        r1 = PedantBase(seed=42).evolve(PedantStone.UNSPLITTIUM).move("to boldly go")
        r2 = PedantBase(seed=42).evolve(PedantStone.UNSPLITTIUM).move("to boldly go")
        assert r1 == r2

    def test_different_seeds_can_differ(self):
        results = {
            PedantBase(seed=i).evolve(PedantStone.UNSPLITTIUM).move("to boldly go")
            for i in range(100)
        }
        # Both placements should appear across different seeds
        assert len(results) == 2

    def test_non_ly_adverb_unchanged(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.UNSPLITTIUM)
        result = pedant.move("to not go")
        assert result == "to not go"

    def test_no_split_unchanged(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.UNSPLITTIUM)
        result = pedant.move("to go boldly")
        assert result == "to go boldly"

    def test_multiple_splits(self):
        pedant = PedantBase(seed=42).evolve(PedantStone.UNSPLITTIUM)
        result = pedant.move("We need to carefully review and to fully understand")
        # Both split infinitives should be "corrected"
        assert "to carefully review" not in result
        assert "to fully understand" not in result


class TestAetheria:
    """Tests for Coeurite -> Aetheria (archaic ligatures)."""

    def test_evolve_with_coeurite(self):
        pedant = PedantBase(seed=9)
        evolved = pedant.evolve(PedantStone.COEURITE)
        output = evolved.move("We cooperate on aesthetic archaeology.")
        assert "coöperate" in output
        assert "æ" in output

    def test_aetheria_ligature_handles_title_case(self):
        pedant = PedantBase(seed=9).evolve(PedantStone.COEURITE)
        output = pedant.move("Aether lore beckons.")
        assert "Æther" in output

    def test_aetheria_ligature_handles_uppercase_pair(self):
        pedant = PedantBase(seed=9).evolve(PedantStone.COEURITE)
        assert pedant.move("AE") == "Æ"

    def test_aetheria_diaeresis_handles_title_case_pair(self):
        pedant = PedantBase(seed=3).evolve(PedantStone.COEURITE)
        assert pedant.move("Coordinate meeting") == "Coördinate meeting"


class TestApostrofae:
    """Tests for Curlite -> Apostrofae (curly quotes)."""

    def test_evolve_with_curlite(self):
        pedant = PedantBase(seed=13)
        evolved = pedant.evolve(PedantStone.CURLITE)
        output = evolved.move('"Hello," they said.')
        assert output != '"Hello," they said.'
        assert '"' not in output
        assert set(output) - set('"Hello," they said.')


class TestCommama:
    """Tests for Oxfordium -> Commama (Oxford comma)."""

    def test_commama_adds_missing_delimiter(self):
        pedant = PedantBase(seed=43).evolve(PedantStone.OXFORDIUM)
        text = "Invite apples, pears and bananas."
        expected = "Invite apples, pears, and bananas."
        assert pedant.move(text) == expected

    def test_commama_respects_existing_delimiter(self):
        pedant = PedantBase(seed=43).evolve(PedantStone.OXFORDIUM)
        original = "Invite apples, pears, and bananas."
        assert pedant.move(original) == original


class TestDeterminism:
    """Tests for determinism guarantees across evolutions."""

    def test_evolution_determinism_same_seed(self):
        pedant_one = PedantBase(seed=11).evolve(PedantStone.COEURITE)
        pedant_two = PedantBase(seed=11).evolve(PedantStone.COEURITE)
        text = "Coordinate cooperative efforts across aesthetic areas."
        assert pedant_one.move(text) == pedant_two.move(text)

    def test_evolution_determinism_different_seeds(self):
        pedant_one = PedantBase(seed=5).evolve(PedantStone.COEURITE)
        pedant_two = PedantBase(seed=9).evolve(PedantStone.COEURITE)
        text = "Coordinate cooperative efforts across aesthetic areas."
        assert pedant_one.move(text) != pedant_two.move(text)


class TestPedantGlitchling:
    """Tests for the Pedant glitchling integration."""

    @pytest.mark.parametrize("stone_input", [PedantStone.HYPERCORRECTITE, "Hypercorrectite"])
    def test_pedant_glitch_applies_selected_stone(self, stone_input):
        glitch = Pedant(stone=stone_input, seed=21)
        assert glitch("between you and me") == "between you and I"

    def test_pedant_pipeline_descriptor_includes_stone_label(self):
        glitch = Pedant(stone=PedantStone.COEURITE, seed=5)
        descriptor = glitch.pipeline_operation()
        assert descriptor == {"type": "pedant", "stone": PedantStone.COEURITE.label}

    def test_pedant_accepts_curlite_string_identifier(self):
        glitch = Pedant(stone="Curlite", seed=13)
        output = glitch('"Hello," they said.')
        assert output != '"Hello," they said.'
        assert '"' not in output
        assert set(output) - set('"Hello," they said.')

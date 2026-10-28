"""Tests for the parser of a wiki page that describes a single item."""

from pathlib import Path

from scrapers.item_page import parse_item_page

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "item_pages"


def _page(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.wiki").read_text()


class TestMineralPage:
    def test_type_and_name(self):
        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        assert parsed is not None
        assert parsed["type"] == "mineral"
        assert parsed["name"] == "Moonspire"

    def test_the_leading_fields_are_read(self):
        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        assert parsed["fields"]["description"] == (
            "A spire of crystallised moonlight that only forms beneath Haunted Creek."
        )
        assert parsed["fields"]["rarity"] == "Exotic"
        assert parsed["fields"]["value"] == "45,000,000"
        assert parsed["fields"]["locations"] == "Haunted Creek"

    def test_the_image_is_a_file_name(self):
        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        assert parsed["fields"]["image"] == "Moonspire.png"

    def test_the_drop_chances_are_read(self):
        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        chances = parsed["fields"]["chances"]

        assert len(chances) == 1
        assert chances[0]["location"] == "Haunted Creek"
        assert chances[0]["chance_percent"] == 2.161e-08
        assert chances[0]["one_in"] == 4_626_836_341

    def test_the_recipes_are_read(self):
        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        recipes = parsed["fields"]["recipes"]

        assert len(recipes) == 1
        assert recipes[0]["station"] == "Dullahan's Curse"
        assert recipes[0]["rarity"] == "Exotic, limited"
        assert recipes[0]["ingredients"] == ["4 Pumpkin Soul", "10 Lost Soul", "1 Moonspire"]

    def test_the_museum_usage_is_read(self):
        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        assert "Maximum Boost: 0.32× each" in parsed["fields"]["museum_usage"]

    def test_the_trivia_is_read(self):
        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        assert "Lunar modifier" in parsed["fields"]["trivia"]


class TestToolPages:
    def test_a_pan(self):
        parsed = parse_item_page("Rusty Pan", _page("Rusty_Pan"))
        assert parsed is not None
        assert parsed["type"] == "pan"
        assert parsed["fields"]["color"] == "#f8cea8"
        assert parsed["fields"]["obtained"] == "Starter"
        assert parsed["fields"]["price"] == "0"

    def test_a_shovel(self):
        parsed = parse_item_page("Iron Shovel", _page("Iron_Shovel"))
        assert parsed is not None
        assert parsed["type"] == "shovel"
        assert parsed["fields"]["price"] == "3,000"
        assert parsed["fields"]["location"] == "Rubble Creek Sands"

    def test_a_sluice(self):
        parsed = parse_item_page("Fossilized Sluice", _page("Fossilized_Sluice"))
        assert parsed is not None
        assert parsed["type"] == "sluice"
        assert parsed["fields"]["location"] == "Caldera Island"

    def test_the_stats_become_modifiers(self):
        parsed = parse_item_page("Iron Shovel", _page("Iron_Shovel"))
        stats = {modifier["stat"]: modifier["amount"] for modifier in parsed["modifiers"]}

        assert stats["Dig Strength"] == 2.0
        assert stats["Dig Speed"] == 0.8
        assert stats["Toughness"] == 1.0

    def test_the_sluice_stats_become_modifiers(self):
        parsed = parse_item_page("Fossilized Sluice", _page("Fossilized_Sluice"))
        stats = {modifier["stat"]: modifier["amount"] for modifier in parsed["modifiers"]}

        assert stats["Luck"] == 30000.0
        assert stats["Capacity"] == 200.0
        assert stats["Efficiency"] == 1.0
        assert stats["Toughness"] == 6.0

    def test_the_prose_sections_are_read(self):
        parsed = parse_item_page("Rusty Pan", _page("Rusty_Pan"))
        assert "rusty pan for gold panning" in parsed["fields"]["overview"].lower()
        assert parsed["fields"]["obtainment"] == "Given to the player upon joining the game."

    def test_no_markup_is_left(self):
        parsed = parse_item_page("Iron Shovel", _page("Iron_Shovel"))
        for value in parsed["fields"].values():
            text = value if isinstance(value, str) else str(value)
            assert "[[" not in text
            assert "{{" not in text
            assert "&nbsp;" not in text


class TestConsumablePages:
    def test_a_consumable(self):
        parsed = parse_item_page("Firefly Flare", _page("Firefly_Flare"))
        assert parsed is not None
        assert parsed["type"] == "consumable"
        assert parsed["fields"]["description"].startswith("A bright flare")
        assert "Firefly Stone" in parsed["fields"]["obtainment"]
        assert "throw it in the direction" in parsed["fields"]["usage"]

    def test_a_merchant_consumable(self):
        parsed = parse_item_page("Solar Token", _page("Solar_Token"))
        assert parsed is not None
        assert parsed["type"] == "consumable"
        assert "Traveling Merchant" in parsed["fields"]["obtainment"]
        assert "$500,000,000" in parsed["fields"]["obtainment"]

    def test_the_categories_are_not_part_of_the_text(self):
        parsed = parse_item_page("Firefly Flare", _page("Firefly_Flare"))
        assert "Category:" not in parsed["fields"]["usage"]


class TestPagesThatAreNotItems:
    def test_an_empty_page(self):
        assert parse_item_page("Nothing", "") is None

    def test_a_page_without_an_item(self):
        assert parse_item_page("Some Guide", "== Overview ==\nJust some text.") is None

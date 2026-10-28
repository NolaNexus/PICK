"""Tests for the canonical item taxonomy."""

from app.taxonomy import (
    AREAS,
    GROUPS,
    TAXONOMY,
    all_types_in_area,
    area_of,
    group_of,
    is_listed,
    label_of,
    taxonomy_payload,
    types_in_area,
    types_in_group,
)


class TestTaxonomy:
    def test_every_type_has_an_area(self):
        for item_type, entry in TAXONOMY.items():
            assert entry[0] in AREAS, f"{item_type} has the unknown area {entry[0]}"

    def test_every_type_has_a_label(self):
        for item_type, entry in TAXONOMY.items():
            assert entry[2], f"{item_type} has no label"

    def test_the_areas_are_the_ones_the_site_has(self):
        assert AREAS == ("items", "minerals", "world", "calculators")

    def test_the_item_groups(self):
        assert GROUPS["items"] == ("gear", "consumables", "treasure")

    def test_the_gear_group(self):
        assert set(types_in_group("items", "gear")) == {
            "pan",
            "shovel",
            "sluice",
            "equipment",
            "trinket",
            "rune",
        }

    def test_the_consumables_group(self):
        assert set(types_in_group("items", "consumables")) == {
            "potion",
            "enchant_book",
            "relic",
        }

    def test_the_treasure_group(self):
        assert set(types_in_group("items", "treasure")) == {
            "geode",
            "treasure_chest",
            "treasure_map",
        }

    def test_the_minerals_area(self):
        assert types_in_area("minerals") == ["mineral"]

    def test_the_world_area(self):
        assert types_in_area("world") == [
            "npc",
            "quest",
            "location",
            "excavation_site",
            "event",
        ]

    def test_the_calculators_area_holds_reference_material(self):
        """Formulas, mastery and mutations live under the calculators."""
        assert set(all_types_in_area("calculators")) == {
            "formula",
            "mastery",
            "mutation_chance",
        }
        assert types_in_area("calculators") == []

    def test_the_merged_types_are_not_listed(self):
        for item_type in ("museum_ore", "blueprint", "consumable", "excavation_reward"):
            assert is_listed(item_type) is False, f"{item_type} should not be browsable"

    def test_an_unknown_type_is_read_as_an_item(self):
        assert area_of("something_new") == "items"
        assert group_of("something_new") is None
        assert label_of("something_new") == "Something New"

    def test_a_known_type_is_labelled(self):
        assert label_of("treasure_chest") == "Treasure Chest"
        assert label_of("enchant_book") == "Enchant Book"
        assert area_of("mineral") == "minerals"
        assert group_of("rune") == "gear"


class TestPayload:
    def test_the_payload_holds_every_type(self):
        payload = taxonomy_payload()
        types = {entry["type"] for entry in payload}
        assert types == set(TAXONOMY)

    def test_the_listed_types_come_first(self):
        payload = taxonomy_payload()
        listed = [entry for entry in payload if entry["listed"]]
        assert listed
        assert all(entry["listed"] for entry in listed)

    def test_every_entry_has_a_label_and_area(self):
        for entry in taxonomy_payload():
            assert entry["label"]
            assert entry["area"] in AREAS
            assert entry["kind"] in {"item", "record", "reference"}

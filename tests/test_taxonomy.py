"""Tests for the item taxonomy.

The taxonomy lives in the ``taxonomy`` table, so these tests read it through
the loader rather than from a Python literal. That is the point: the list of
types, and everything the site needs to know about a type, has one home, and
the column that holds a type is constrained to the same values.
"""

import pytest

from app.taxonomy import AREAS, GROUPS, load_taxonomy


@pytest.fixture
async def taxonomy(db_session):
    """The taxonomy, read from the database."""
    return await load_taxonomy(db_session)


class TestTaxonomy:
    async def test_every_type_has_an_area(self, taxonomy):
        for entry in taxonomy.entries:
            assert entry.area in AREAS, f"{entry.type} has the unknown area {entry.area}"

    async def test_every_type_has_a_label(self, taxonomy):
        for entry in taxonomy.entries:
            assert entry.label, f"{entry.type} has no label"

    async def test_the_areas_are_the_ones_the_site_has(self):
        assert AREAS == ("items", "minerals", "world", "calculators")

    async def test_the_item_groups(self):
        assert GROUPS["items"] == ("gear", "consumables", "treasure")

    async def test_the_gear_group(self, taxonomy):
        assert set(taxonomy.types_in_group("items", "gear")) == {
            "pan",
            "shovel",
            "sluice",
            "equipment",
            "trinket",
            "rune",
        }

    async def test_the_consumables_group(self, taxonomy):
        assert set(taxonomy.types_in_group("items", "consumables")) == {
            "potion",
            "enchant_book",
            "relic",
        }

    async def test_the_treasure_group(self, taxonomy):
        assert set(taxonomy.types_in_group("items", "treasure")) == {
            "geode",
            "treasure_chest",
            "treasure_map",
        }

    async def test_the_minerals_area(self, taxonomy):
        assert taxonomy.types_in_area("minerals") == ["mineral"]

    async def test_the_world_area(self, taxonomy):
        assert taxonomy.types_in_area("world") == [
            "npc",
            "quest",
            "location",
            "excavation_site",
            "event",
        ]

    async def test_the_calculators_area_holds_reference_material(self, taxonomy):
        """Formulas, mastery and mutations live under the calculators."""
        assert set(taxonomy.all_types_in_area("calculators")) == {
            "formula",
            "mastery",
            "mutation_chance",
        }
        assert taxonomy.types_in_area("calculators") == []

    async def test_the_merged_types_are_not_listed(self, taxonomy):
        for item_type in ("museum_ore", "blueprint", "consumable", "excavation_reward"):
            assert taxonomy.is_listed(item_type) is False, f"{item_type} should not be browsable"

    async def test_the_fragment_types_are_recognised(self, taxonomy):
        """A parser emits these so reconciliation can fold them into another row."""
        fragments = {
            "blueprint",
            "consumable",
            "excavation_reward",
            "merchant_item",
            "museum_display",
            "museum_info",
            "museum_ore",
            "mutation_catalyst",
        }
        for item_type in fragments:
            assert taxonomy.is_fragment(item_type) is True, f"{item_type} should be a fragment"

    async def test_a_normal_type_is_not_a_fragment(self, taxonomy):
        assert taxonomy.is_fragment("mineral") is False
        assert taxonomy.is_fragment("relic") is False

    async def test_a_fragment_is_never_browsable(self, taxonomy):
        for entry in taxonomy.entries:
            if entry.is_fragment:
                assert entry.listed is False, f"{entry.type} should not be browsable"

    async def test_an_unknown_type_is_read_as_an_item(self, taxonomy):
        assert taxonomy.area_of("something_new") == "items"
        assert taxonomy.group_of("something_new") is None
        assert taxonomy.label_of("something_new") == "Something New"

    async def test_a_known_type_is_labelled(self, taxonomy):
        assert taxonomy.label_of("treasure_chest") == "Treasure Chest"
        assert taxonomy.label_of("enchant_book") == "Enchant Book"
        assert taxonomy.area_of("mineral") == "minerals"
        assert taxonomy.group_of("rune") == "gear"


class TestPayload:
    async def test_the_payload_holds_every_type(self, taxonomy):
        payload = taxonomy.payload()
        types = {entry["type"] for entry in payload}
        assert types == set(taxonomy.types)

    async def test_the_payload_holds_the_fragments_too(self, taxonomy):
        """A fragment that stayed active still has to be nameable.

        The site is not offered a place to browse a fragment, but it does need
        a label for the one that has nowhere to fold into.
        """
        payload = taxonomy.payload()
        types = {entry["type"] for entry in payload}
        fragments = {entry.type for entry in taxonomy.entries if entry.is_fragment}
        assert fragments <= types

    async def test_the_listed_types_come_first(self, taxonomy):
        payload = taxonomy.payload()
        listed = [entry for entry in payload if entry["listed"]]
        assert listed
        assert all(entry["listed"] for entry in listed)

    async def test_every_entry_has_a_label_and_area(self, taxonomy):
        for entry in taxonomy.payload():
            assert entry["label"]
            assert entry["area"] in AREAS
            assert entry["kind"] in {"item", "record", "reference"}

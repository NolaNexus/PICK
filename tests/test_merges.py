"""Tests for the merges that fold a record into the item it describes."""

import pytest
from sqlalchemy import select

from app.models import Item
from app.services.reconcile import (
    _merge_blueprints,
    _merge_catalysts,
    _merge_excavation_drops,
    _merge_museum_displays,
    _merge_museum_ores,
    _resolve_mineral_areas,
    _site_key,
)


def _item(item_type, name, **data):
    return Item(
        type=item_type,
        name=name,
        slug=f"{item_type}-{name.lower().replace(' ', '-')}",
        data=data,
        is_active=True,
    )


class TestMuseumOres:
    def test_the_museum_row_folds_into_the_mineral(self):
        mineral = _item("mineral", "Adamantine", value=100)
        museum = _item("museum_ore", "Adamantine", min_kg=50, max_boost="0.5x", bonus_stat="Luck")

        merged = _merge_museum_ores([mineral, museum], {"adamantine": [mineral, museum]})

        assert merged == 1
        assert museum.is_active is False
        assert mineral.data["museum"]["min_weight_kg"] == 50
        assert mineral.data["museum"]["bonus_stat"] == "Luck"

    def test_a_museum_row_without_a_mineral_is_kept(self):
        museum = _item("museum_ore", "Nowhere Ore", min_kg=50)

        merged = _merge_museum_ores([museum], {"nowhereore": [museum]})

        assert merged == 0
        assert museum.is_active is True


class TestBlueprints:
    def test_the_blueprint_folds_into_the_equipment(self):
        equipment = _item("equipment", "Accretion Disk", slot="Disk")
        blueprint = _item(
            "blueprint",
            "Accretion Disk",
            quest_giver="Meteor Guardian",
            quest_name="Galactic Guardian",
            quest_steps=[{"Quest": "Galactic Guardian"}],
        )

        merged = _merge_blueprints(
            [equipment, blueprint], {"accretion disk": [equipment, blueprint]}
        )

        assert merged == 1
        assert blueprint.is_active is False
        assert equipment.data["blueprint"]["quest_giver"] == "Meteor Guardian"
        assert equipment.data["blueprint"]["quest_steps"] == [{"Quest": "Galactic Guardian"}]

    def test_a_blueprint_without_equipment_is_kept(self):
        blueprint = _item("blueprint", "Nothing", quest_giver="Nobody")

        merged = _merge_blueprints([blueprint], {"nothing": [blueprint]})

        assert merged == 0
        assert blueprint.is_active is True


class TestCatalysts:
    def test_the_catalyst_folds_into_the_equipment_it_rerolls(self):
        equipment = _item("equipment", "Gold Ring", slot="Ring")
        catalyst = _item(
            "mutation_catalyst",
            "Gold Ring",
            equipment="Gold Ring",
            mineral="Gold",
            rarity="Common",
        )

        merged = _merge_catalysts([equipment, catalyst], {"gold ring": [equipment, catalyst]})

        assert merged == 1
        assert catalyst.is_active is False
        assert equipment.data["catalyst"]["mineral"] == "Gold"
        assert equipment.data["catalyst"]["rarity"] == "Common"


class TestSiteKeys:
    def test_the_tier_is_stripped(self):
        assert _site_key("Volcanic Ruins (A-Site)") == _site_key("Volcanic Ruins")

    def test_the_plural_typo_is_aliased(self):
        assert _site_key("Mysterious Meteors") == _site_key("Mysterious Meteor")


class TestExcavationDrops:
    def test_the_drops_fold_into_the_site(self):
        site = _item(
            "excavation_site", "Volcanic Ruins (A-Site)", site_name="Volcanic Ruins (A-Site)"
        )
        drop = _item(
            "excavation_reward",
            "Solar Token",
            site="Volcanic Ruins",
            chance="0.5%",
            item_slug="relic-solar-token",
        )

        merged = _merge_excavation_drops([site, drop])

        assert merged == 1
        assert drop.is_active is False
        assert site.data["drops"][0]["item_slug"] == "relic-solar-token"

    def test_the_plural_typo_still_joins(self):
        site = _item("excavation_site", "Mysterious Meteor (E-Site)")
        drop = _item("excavation_reward", "Something", site="Mysterious Meteors", chance="1%")

        merged = _merge_excavation_drops([site, drop])

        assert merged == 1
        assert len(site.data["drops"]) == 1


class TestMuseumDisplays:
    def test_the_displays_fold_into_the_museum(self):
        location = _item(
            "location",
            "Caldera Park",
            sublocations=[{"name": "Museum", "slug": "museum"}],
        )
        display = _item(
            "museum_display", "Common Display", rarity="Common", money_price="$1,000,000"
        )
        info = _item("museum_info", "Museum", description="A museum", location="Caldera Park")

        merged = _merge_museum_displays([location, display, info])

        assert merged == 2
        assert display.is_active is False
        assert info.is_active is False

        museum = location.data["sublocations"][0]
        assert len(museum["displays"]) == 1
        assert museum["displays"][0]["rarity"] == "Common"
        assert museum["info"]["description"] == "A museum"

    def test_without_a_museum_the_rows_are_kept(self):
        display = _item("museum_display", "Common Display", rarity="Common")

        merged = _merge_museum_displays([display])

        assert merged == 0
        assert display.is_active is True


class TestMineralAreas:
    def test_a_place_resolves_to_its_area(self):
        location = _item(
            "location",
            "Caldera Park",
            sublocations=[{"name": "Volcanic Sands"}, {"name": "Magma Furnace"}],
        )
        mineral = _item("mineral", "Ruby", locations=["Volcanic Sands", "Magma Furnace"])

        resolved, unmatched = _resolve_mineral_areas([location, mineral])

        assert resolved == 1
        assert unmatched == []
        assert mineral.data["areas"] == ["Caldera Park"]

    def test_a_place_with_no_area_is_reported(self):
        location = _item("location", "Caldera Park", sublocations=[{"name": "Volcanic Sands"}])
        mineral = _item("mineral", "Ruby", locations=["Seashell Beach"])

        resolved, unmatched = _resolve_mineral_areas([location, mineral])

        assert resolved == 0
        assert unmatched == ["Seashell Beach"]


@pytest.mark.asyncio
async def test_the_merges_leave_one_row_per_thing(db_session):
    """After reconciliation there is one active row for the item and its facets."""
    from app.services.reconcile import reconcile_items

    mineral = _item("mineral", "Adamantine", value=100)
    museum = _item("museum_ore", "Adamantine", min_kg=50)
    equipment = _item("equipment", "Accretion Disk", slot="Disk")
    blueprint = _item("blueprint", "Accretion Disk", quest_giver="Guardian")

    db_session.add_all([mineral, museum, equipment, blueprint])
    await db_session.commit()

    await reconcile_items(db_session)
    await db_session.commit()

    active = (
        (
            await db_session.execute(
                select(Item).where(Item.is_active.is_(True), Item.type == "museum_ore")
            )
        )
        .scalars()
        .all()
    )
    assert active == []

    minerals = (
        (
            await db_session.execute(
                select(Item).where(Item.is_active.is_(True), Item.name == "Adamantine")
            )
        )
        .scalars()
        .all()
    )
    assert len(minerals) == 1
    assert minerals[0].data["museum"]["min_weight_kg"] == 50

    equipment_rows = (
        (
            await db_session.execute(
                select(Item).where(Item.is_active.is_(True), Item.name == "Accretion Disk")
            )
        )
        .scalars()
        .all()
    )
    assert len(equipment_rows) == 1
    assert equipment_rows[0].data["blueprint"]["quest_giver"] == "Guardian"

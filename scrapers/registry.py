"""Scraper registry - maps page titles to parser functions."""

from typing import Any

# All page parsers are imported from their respective modules
# and registered here for the scraper to use
from scrapers import (
    blueprints,
    enchanting,
    equipment,
    events,
    excavations,
    geodes,
    locations,
    mastery,
    minerals,
    modifiers,
    museum,
    npcs,
    pans,
    potions,
    quests,
    relics,
    runes,
    shovels,
    sluices,
    traveling_merchant,
    treasure_chest,
    treasure_map,
    trinkets,
)
from scrapers import (
    formulas as formula_parser,
)

# Master list of all tracked wiki pages (for reference and documentation)
TRACKED_PAGES: list[str] = [
    "Pans",
    "Shovels",
    "Minerals",
    "Sluices",
    "Equipment",
    "Enchanting",
    "Locations",
    "Traveling_Merchant",
    "Potions",
    "NPCs",
    "Events",
    "Quests",
    "Museum",
    "Excavations",
    "Relics",
    "Geodes",
    "Runes",
    "Mastery",
    "Mutations",
    "Treasure_Map",
    "Treasure Chest",
    "Stat_Systems_Guide",
    "Blueprint",  # Actual page name is "Blueprint" not "Blueprints"
    "Trinkets",
    "Modifiers",
    "Codes",
    "Changelog",
    "Guides",
]

PARSERS: dict[str, Any] = {
    "Pans": pans.parse_pans,
    "Shovels": shovels.parse_shovels,
    "Minerals": minerals.parse_minerals,
    "Sluices": sluices.parse_sluices,
    "Equipment": equipment.parse_equipment,
    "Modifiers": modifiers.parse_modifiers,
    "Locations": locations.parse_locations,
    "Enchanting": enchanting.parse_enchanting,
    "Trinkets": trinkets.parse_trinkets,
    "Stat_Systems_Guide": formula_parser.parse_formulas,
    "Blueprint": blueprints.parse_blueprints,
    "Relics": relics.parse_relics,
    "Runes": runes.parse_runes,
    "Traveling_Merchant": traveling_merchant.parse_traveling_merchant,
    "Potions": potions.parse_potions,
    "Geodes": geodes.parse_geodes,
    "NPCs": npcs.parse_npcs,
    "Events": events.parse_events,
    "Quests": quests.parse_quests,
    "Museum": museum.parse_museum,
    "Excavations": excavations.parse_excavations,
    "Mastery": mastery.parse_mastery,
    "Treasure_Map": treasure_map.parse_treasure_maps,
    "Treasure Chest": treasure_chest.parse_treasure_chests,
}

# Add remaining tracked pages when parsers are implemented
for page in [
    "Mutations",
    "Codes",
    "Changelog",
    "Guides",
]:
    if page not in PARSERS:
        PARSERS[page] = None  # type: ignore

#: Version of the parsing and rendering rules.
#:
#: The scraper only re-parses a page when its wikitext changes. Bumping this
#: value makes every page look changed, so a change to a parser or to the
#: shared wikitext renderer is applied to the data that is already stored.
PARSER_VERSION = 3

__all__ = ["PARSERS", "PARSER_VERSION", "TRACKED_PAGES"]

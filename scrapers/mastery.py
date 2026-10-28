"""Mastery scraper - parse Location Mastery quests from the Mastery wiki page."""

import re
from typing import Any

from scrapers.types import ParsedItem


def parse_mastery(wikitext: str) -> list[ParsedItem]:
    """Parse mastery data from tabber sections with locations and quests."""
    items: list[ParsedItem] = []

    # Find all tabber tags
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL)
    if not tabber_match:
        return items

    tabber_content = tabber_match.group(1)

    # Parse each tab: |-| TabName = content
    parts = re.split(r"\n\|\-\|", tabber_content)

    for i, part in enumerate(parts):
        part = part.lstrip()
        if not part:
            continue

        # Parse tab: LocationName = content
        if i == 0:
            # First tab doesn't have |-| prefix
            tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)
        else:
            tab_match = re.match(r"([^\n]+?)\s*=(.*)", part, re.DOTALL)

        if not tab_match:
            continue

        location_name = tab_match.group(1).strip()
        content = tab_match.group(2).strip()

        location_items = _parse_location_mastery(location_name, content)
        items.extend(location_items)

    return items


def _parse_location_mastery(location: str, content: str) -> list[ParsedItem]:
    """Parse all quests for a single location mastery."""
    items: list[ParsedItem] = []

    # Extract the boost type from the first line (e.g., "'''Boost:''' Rubble Creek Luck.")
    boost_match = re.search(r"'''Boost:'''\s*([^\n]+)", content)
    boost_type = ""
    if boost_match:
        boost_type = boost_match.group(1).strip()

    # Find all Quest templates
    quest_pattern = r"\{\{Quest\s*\n(.*?)\n\}\}"
    for quest_match in re.finditer(quest_pattern, content, re.DOTALL):
        quest_content = quest_match.group(1)
        quest = _parse_quest(location, boost_type, quest_content)
        if quest:
            items.append(quest)

    return items


def _parse_quest(location: str, boost_type: str, template_text: str) -> ParsedItem | None:
    """Parse a single {{Quest}} template into a mastery item."""
    # First, extract the Quest name field specifically
    quest_name_match = re.search(r"\|\s*Quest\s*=\s*([^\n]+)", template_text)
    if not quest_name_match:
        return None

    quest_name = quest_name_match.group(1).strip()
    # Clean up quest name
    quest_name = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", quest_name)
    quest_name = re.sub(r"\{\{[^}]+\}\}", "", quest_name).strip()

    if not quest_name:
        return None

    # Extract other fields - parse line by line
    fields = {}
    lines = template_text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("|"):
            # Extract field name and value
            field_match = re.match(r"\|\s*(\w+)\s*=\s*(.*)", line)
            if field_match:
                key = field_match.group(1).strip()
                value = field_match.group(2).strip()
                if value:
                    fields[key] = value

    # Clean up other fields
    def clean(text: str) -> str:
        text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", r"\2", text)
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"'''([^']+)'''", r"\1", text)
        return text.strip()

    def clean_preserve_templates(text: str) -> str:
        """Clean but preserve template syntax like {{EXP|...}} and {{Meteor Shards|...}}"""
        text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", r"\2", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"'''([^']+)'''", r"\1", text)
        return text.strip()

    quest_sub = clean(fields.get("QuestSub", ""))
    rewards = clean_preserve_templates(fields.get("Rewards", ""))

    # The location luck this mastery raises, e.g. "Rubble Creek Luck: 1.05x".
    modifiers: list[dict[str, Any]] = []
    boost_match = re.search(r"([\d.]+)\s*[x×]", rewards)
    if boost_match and boost_type:
        stat_name = boost_type.rstrip(".").strip()
        modifiers.append(
            {
                "stat": stat_name,
                "amount": float(boost_match.group(1)),
                "unit": "multiplier",
            }
        )

    # Extract quest steps
    steps: list[str] = []
    for key in sorted(fields.keys()):
        if key.startswith("QuestStep"):
            step_num = key.replace("QuestStep", "").replace("Sub", "")
            step_text = clean(fields[key])
            if step_text:
                steps.append(f"Step {step_num}: {step_text}")

    # Generate slug
    slug = _slugify(f"{location} {quest_name}")

    data: dict[str, Any] = {
        "location": location,
        "boost_type": boost_type,
        "description": quest_sub,
        "steps": steps,
        "rewards": rewards,
    }
    if modifiers:
        data["modifiers"] = modifiers

    return {
        "id": slug,
        "type": "mastery",
        "name": quest_name,
        "slug": slug,
        "data": data,
        "image_url": None,
    }


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
        .replace("&", "")
        .replace("#", "")
        .replace("×", "x")
        .replace(":", "")
        .replace("/", "-")
        .replace("[", "")
        .replace("]", "")
        .replace(",", "")
        .replace(".", "")
        .replace("!", "")
        .replace(";", "")
    )

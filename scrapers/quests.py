"""Quests scraper - parse <tabber> with locations, NPCs, and {{Quest}} templates from the Quests wiki page."""

import re
from typing import Any

from scrapers.stats import parse_modifier_list
from scrapers.types import ParsedItem


def parse_quests(wikitext: str) -> list[ParsedItem]:
    """Parse quest data from tabber sections with locations and NPCs."""
    quests: list[ParsedItem] = []

    # Find all tabber tags
    tabber_pattern = r"<tabber>(.*?)</tabber>"
    tabber_match = re.search(tabber_pattern, wikitext, re.DOTALL)
    if not tabber_match:
        return quests

    tabber_content = tabber_match.group(1)

    # Parse each tab: |-| TabName = content
    parts = re.split(r"\n\|\-\|", tabber_content)

    # First part is the first tab (before any |-|)
    if parts[0].strip():
        location_quests = _parse_location_tab(parts[0])
        quests.extend(location_quests)

    # Remaining parts are subsequent tabs
    for part in parts[1:]:
        location_quests = _parse_location_tab(part)
        quests.extend(location_quests)

    return quests


def _parse_location_tab(tab_content: str) -> list[ParsedItem]:
    """Parse a single location tab containing NPCs and quests."""
    # Strip leading whitespace
    tab_content = tab_content.lstrip()

    # Tab format: LocationName = content
    tab_match = re.match(r"([^\n]+?)\s*=(.*)", tab_content, re.DOTALL)
    if not tab_match:
        return []

    location_name = tab_match.group(1).strip()
    content = tab_match.group(2).strip()

    if not location_name:
        return []

    location_quests: list[ParsedItem] = []
    current_npc = ""

    # Split by lines and process
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check for NPC marker: ; NPC: [[Name]] or ; NPC: Name
        npc_match = re.match(r";\s*NPC:\s*(.+)", line)
        if npc_match:
            current_npc = npc_match.group(1).strip()
            # Clean up NPC name
            current_npc = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", current_npc)
            current_npc = current_npc.strip()
            i += 1
            continue

        # Check for Quest template
        if line.startswith("{{Quest"):
            # Extract the full Quest template (may span multiple lines)
            quest_text = _extract_template(lines, i, "Quest")
            if quest_text:
                quest = _parse_quest_template(location_name, current_npc, quest_text)
                if quest:
                    location_quests.append(quest)
                # Skip the lines we consumed
                consumed = quest_text.count("\n") + 1
                i += consumed
                continue

        i += 1

    return location_quests


def _extract_template(lines: list[str], start_idx: int, template_name: str) -> str | None:
    """Extract a template from lines starting at start_idx."""
    if start_idx >= len(lines):
        return None

    # Find the opening {{
    line = lines[start_idx]
    if f"{{{template_name}" not in line:
        return None

    # Count braces to find the closing }}
    brace_count = 0
    result: list[str] = []

    for i in range(start_idx, len(lines)):
        current_line = lines[i]
        result.append(current_line)

        # Count opening and closing braces
        for char in current_line:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1

        if brace_count == 0:
            return "\n".join(result)

    return "\n".join(result) if result else None


def _parse_quest_template(location: str, npc: str, template_text: str) -> ParsedItem | None:
    """Parse a {{Quest}} template into a quest object."""
    # First, extract the Quest name field specifically - only first line after |Quest =
    quest_name_match = re.search(r"\|\s*Quest\s*=\s*([^\n]+)", template_text)
    if not quest_name_match:
        return None

    quest_name = quest_name_match.group(1).strip()
    # Clean up quest name
    quest_name = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", quest_name)
    quest_name = re.sub(r"\{\{[^}]+\}\}", "", quest_name).strip()
    quest_name = re.sub(r"<[^>]+>", "", quest_name).strip()

    if not quest_name:
        return None

    # Extract other fields - use line-by-line for Rewards, QuestSub, Buffs
    fields = {}

    # For QuestSub, Rewards, Buffs - extract first line only (preserve template syntax)
    for field in ["QuestSub", "Rewards", "Buffs"]:
        match = re.search(rf"\|\s*{field}\s*=\s*([^\n]+)", template_text)
        if match:
            fields[field] = match.group(1).strip()

    # For QuestStep fields - extract all
    step_pattern = r"\|\s*(QuestStep\w*)\s*=\s*([^\n]+)"
    for match in re.finditer(step_pattern, template_text):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if value:
            fields[key] = value

    # Clean up quest name
    quest_name = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", quest_name)
    quest_name = re.sub(r"\{\{[^}]+\}\}", "", quest_name).strip()
    quest_name = re.sub(r"<[^>]+>", "", quest_name).strip()

    if not quest_name:
        return None

    # Clean up fields
    def clean(text: str) -> str:
        text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"'''([^']+)'''", r"\1", text)
        return text.strip()

    def clean_preserve_templates(text: str) -> str:
        """Clean but preserve template syntax like {{$|...}} and {{Meteor Shards|...}}"""
        text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"'''([^']+)'''", r"\1", text)
        return text.strip()

    quest_sub = clean(fields.get("QuestSub", ""))
    rewards = clean_preserve_templates(fields.get("Rewards", ""))
    buffs = clean(fields.get("Buffs", ""))

    # The stats the quest grants, e.g. "+50 Luck".
    modifiers = parse_modifier_list(buffs)

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
        "npc": npc,
        "description": quest_sub,
        "steps": steps,
        "rewards": rewards,
        "buffs": buffs,
    }
    if modifiers:
        data["modifiers"] = modifiers

    return {
        "id": slug,
        "type": "quest",
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
        .replace("|", "")
        .replace("?", "")
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

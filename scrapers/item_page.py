"""Parse a wiki page that describes a single item.

Some items have a page of their own. The page holds details the index page
does not: where the item comes from, what it does, how it is made and where
it drops. The pages come in two shapes: an infobox with the numbers, and
prose with sections.
"""

from __future__ import annotations

import re
from typing import Any

import mwparserfromhell

from scrapers.pages import item_type_hint
from scrapers.stats import parse_modifier, parse_modifier_list
from scrapers.wikitext import render_image, render_text

__all__ = ["parse_item_page"]

# The infobox templates and the fields they hold.
_INFOBOXES = {
    "mineral": "Mineral",
    "pan": "PanInfobox",
    "shovel": "ShovelInfobox",
    "sluice": "SluiceInfobox",
    "equipment": "EquipmentInfobox",
    "rune": "RuneInfobox",
    "relic": "RelicInfobox",
    "trinket": "TrinketInfobox",
    "geode": "GeodeInfobox",
}

# The infobox parameter that names each stat of a tool.
_TOOL_STATS = {
    "luck": "Luck",
    "capacity": "Capacity",
    "strength": "Dig Strength",
    "speed": "Dig Speed",
    "efficiency": "Efficiency",
    "toughness": "Toughness",
}

# The sections a page can have.
_SECTIONS = ("Overview", "Stats", "Obtainment", "Usage", "Museum Usage", "Trivia", "Notes")

# A section heading, e.g. "== Obtainment ==".
_HEADING = re.compile(r"^==+\s*([^=]+?)\s*==+\s*$", re.MULTILINE)

# A drop chance line, e.g. "* '''Haunted Creek''' - 0.00000002161% (~1 in 4,626,836,341)".
_CHANCE = re.compile(
    r"^\*\s*'{0,2}(?P<location>[^:]+?)\s*'{0,2}\s*-\s*(?P<chance>[\d.]+)%(?P<one_in>\s*\(~1 in [\d,]+\))?",
    re.MULTILINE,
)

# The number of a "1 in ..." note.
_ONE_IN = re.compile(r"1 in ([\d,]+)")

# A recipe heading, e.g. "=== [[Halloween_Forge#...|Dullahan's Curse]] ({{Exotic}}, limited) ===".
_RECIPE_HEADING = re.compile(
    r"^==+\s*(?P<name>.+?)\s*\((?P<rarity>[^)]*)\)\s*==+\s*$", re.MULTILINE
)


def parse_item_page(title: str, wikitext: str) -> dict[str, Any] | None:
    """Parse an item page into the fields it holds.

    Returns ``None`` when the page does not describe an item.
    """
    if not wikitext:
        return None

    item_type = item_type_hint(wikitext, title)
    if item_type is None:
        return None

    fields: dict[str, Any] = {}
    modifiers: list[dict[str, Any]] = []

    infobox = _read_infobox(wikitext, item_type)
    if infobox:
        fields.update(infobox["fields"])
        modifiers.extend(infobox["modifiers"])

    prose = _read_sections(wikitext)
    fields.update(prose["fields"])

    if item_type == "mineral":
        chances = _read_chances(wikitext)
        if chances:
            fields["chances"] = chances
        recipes = _read_recipes(wikitext)
        if recipes:
            fields["recipes"] = recipes

    # A page that only has prose describes the item in its opening lines.
    if not fields.get("description"):
        lead = _read_lead(wikitext)
        if lead:
            fields["description"] = lead

    # The picture of the item, whether it is in the infobox or in the text.
    if not fields.get("image"):
        image = _read_image(wikitext)
        if image:
            fields["image"] = image

    if not fields and not modifiers:
        return None

    return {
        "name": _page_name(wikitext, title),
        "type": item_type,
        "fields": fields,
        "modifiers": modifiers,
    }


def _as_list(value: str) -> list[str]:
    """Turn a block of text into a list of names, one per line."""
    entries: list[str] = []
    for line in value.split("\n"):
        cleaned = line.strip()
        # A line that is only an HTML tag is not a name.
        if not cleaned or cleaned.startswith("<"):
            continue
        if cleaned not in entries:
            entries.append(cleaned)
    return entries


def _read_image(wikitext: str) -> str:
    """Read the picture of the item from the page.

    The picture is usually the first thing on the page, written as a file
    link with its size and a caption.
    """
    match = re.search(r"\[\[File:([^\]|]+)", wikitext)
    if not match:
        return ""
    return match.group(1).strip()


def _strip_infoboxes(wikitext: str) -> str:
    """Remove the infobox templates from a page.

    An infobox renders as a box of numbers, so it is not part of the text the
    page reads as.
    """
    try:
        tree = mwparserfromhell.parse(wikitext)
    except Exception:
        return wikitext

    for template in list(tree.filter_templates(recursive=True)):
        name = str(template.name).strip()
        if name not in _INFOBOXES.values():
            continue
        try:
            tree.remove(template)
        except ValueError:
            continue

    return str(tree)


def _read_lead(wikitext: str) -> str:
    """Read the opening paragraph of a page.

    The paragraph that names the item and says what it is describes it.
    """
    body = wikitext

    # The picture and the templates at the top are not part of the text.
    body = re.sub(r"^\s*\[\[File:[^\]]*\]\]\s*$", "", body, flags=re.MULTILINE)
    body = re.sub(r"^\s*<templatestyles[^>]*>\s*$", "", body, flags=re.MULTILINE)
    body = _strip_infoboxes(body)

    paragraphs = [part.strip() for part in body.split("\n\n")]
    for paragraph in paragraphs:
        if not paragraph or paragraph.startswith(("=", "[[Category", "{{Category")):
            continue
        text = render_text(paragraph)
        if len(text) > 20:
            return text

    return ""


def _page_name(wikitext: str, title: str) -> str:
    """Read the item's name from the page."""
    # The infobox names the item.
    try:
        tree = mwparserfromhell.parse(wikitext)
        for template in tree.filter_templates(recursive=True):
            if str(template.name).strip() != "Mineral":
                continue
            for param in template.params:
                if str(param.name).strip().lower() == "name" and str(param.value).strip():
                    return str(param.value).strip()
    except Exception:
        pass

    # Otherwise the name is written in bold. The text may hold an apostrophe,
    # so it is read up to the closing marker rather than to a quote.
    match = re.search(r"'''(.+?)'''", wikitext, re.DOTALL)
    if match:
        name = match.group(1).strip()
        # A bolded caption belongs to a picture, not to the item.
        if name and "\n" not in name:
            return name

    return title


def _read_infobox(wikitext: str, item_type: str) -> dict[str, Any] | None:
    """Read the numbers an infobox holds."""
    template_name = _INFOBOXES.get(item_type)
    candidates = [template_name] if template_name else []
    candidates.extend(name for name in _INFOBOXES.values() if name not in candidates)

    try:
        tree = mwparserfromhell.parse(wikitext)
    except Exception:
        return None

    for template in tree.filter_templates(recursive=True):
        name = str(template.name).strip()
        if name not in candidates:
            continue

        params: dict[str, str] = {}
        for param in template.params:
            key = str(param.name).strip()
            value = str(param.value).strip()
            if key and value:
                params[key.lower()] = value

        return _infobox_fields(item_type, params)

    return None


def _infobox_fields(item_type: str, params: dict[str, str]) -> dict[str, Any]:
    """Turn the infobox parameters into fields and stat modifiers."""
    fields: dict[str, Any] = {}
    modifiers: list[dict[str, Any]] = []

    if item_type == "mineral":
        for key in ("description", "rarity", "value"):
            value = params.get(key)
            if value:
                fields[key] = render_text(value)
        if params.get("locations"):
            fields["locations"] = _as_list(render_text(params["locations"]))
        if params.get("image"):
            fields["image"] = render_image(params["image"])
        return {"fields": fields, "modifiers": modifiers}

    for key, stat_name in _TOOL_STATS.items():
        value = params.get(key)
        if not value:
            continue
        modifier = parse_modifier(value, stat=stat_name)
        if modifier:
            modifiers.append(modifier)

    for key in ("color", "obtained", "price", "location"):
        value = params.get(key)
        if not value:
            continue
        # The colour is a value the site uses as it is.
        fields[key] = value if key == "color" else render_text(value)

    if params.get("image"):
        fields["image"] = render_image(params["image"])

    return {"fields": fields, "modifiers": modifiers}


def _read_sections(wikitext: str) -> dict[str, Any]:
    """Read the prose sections of a page."""
    fields: dict[str, Any] = {}

    headings = list(_HEADING.finditer(wikitext))
    for index, match in enumerate(headings):
        name = match.group(1).strip()
        if name not in _SECTIONS:
            continue

        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(wikitext)
        body = wikitext[start:end].strip()

        if not body:
            continue

        key = _section_key(name)
        text = render_text(body)
        if not text:
            continue

        # A section that is already there is not overwritten.
        if key in fields and fields[key]:
            continue
        fields[key] = text

    return {"fields": fields}


def _section_key(name: str) -> str:
    """Turn a section heading into a field name."""
    return name.lower().replace(" ", "_")


def _read_chances(wikitext: str) -> list[dict[str, Any]]:
    """Read the drop chances of a mineral."""
    chances: list[dict[str, Any]] = []

    for match in _CHANCE.finditer(wikitext):
        location = render_text(match.group("location")).strip().strip("'").strip()
        if not location:
            continue

        chance: dict[str, Any] = {"location": location}
        try:
            chance["chance_percent"] = float(match.group("chance"))
        except ValueError:
            continue

        one_in = match.group("one_in")
        if one_in:
            digits = _ONE_IN.search(one_in)
            if digits:
                try:
                    chance["one_in"] = int(digits.group(1).replace(",", ""))
                except ValueError:
                    pass

        chances.append(chance)

    return chances


def _read_recipes(wikitext: str) -> list[dict[str, Any]]:
    """Read the recipes of a mineral."""
    recipes: list[dict[str, Any]] = []
    headings = list(_RECIPE_HEADING.finditer(wikitext))

    for match in headings:
        name = render_text(match.group("name")).strip()
        if not name:
            continue

        rarity = render_text(match.group("rarity")).strip()

        start = match.end()
        # The recipe ends at the next heading of any level.
        next_heading = re.search(r"^==+", wikitext[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(wikitext)

        ingredients = []
        for line in wikitext[start:end].splitlines():
            line = line.strip()
            if not line.startswith("*"):
                continue
            text = render_text(line.lstrip("* ").strip())
            if text:
                ingredients.append(text)

        recipes.append({"station": name, "rarity": rarity, "ingredients": ingredients})

    return recipes


def parse_page_modifiers(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Read stat modifiers out of a page's prose."""
    modifiers: list[dict[str, Any]] = []

    for key in ("effect", "effects", "overview"):
        value = fields.get(key)
        if isinstance(value, str):
            modifiers.extend(parse_modifier_list(value))

    return modifiers

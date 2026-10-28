"""Render wiki markup into plain text for stored item data.

Parsers return the wikitext fragments as they appear on the wiki. Item
``data`` is public API: the frontend, the snapshot export and any API
consumer read it as plain text, so the markup has to be resolved once,
in one place, rather than in every parser.

This module expands templates, resolves links and strips HTML so the stored
values read like the rendered wiki page.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

import mwparserfromhell
from mwparserfromhell.nodes import Template, Wikilink

__all__ = [
    "render_image",
    "render_item_data",
    "render_text",
    "slugify",
    "title_key",
]

# Templates whose first argument is an amount of the named unit.
_VALUE_UNITS = {
    "candy",
    "eggs",
    "exp",
    "heart crystals",
    "meteor shards",
    "sand dollars",
}

# Templates that name a stat, e.g. {{Stat|Luck}}.
_STAT_TEMPLATES = {"stat", "stats"}

# Templates that name a rarity, e.g. {{common}}.
_RARITY_TEMPLATES = {
    "common",
    "epic",
    "exotic",
    "legendary",
    "mythic",
    "mythical",
    "rare",
    "uncommon",
}

# The cash template, e.g. {{$|50,000}}.
_CASH_TEMPLATE = "$"

# Keys whose values are machine identifiers and must survive untouched.
_PRESERVED_KEYS = {
    "applies_to",
    "color",
    "id",
    "item_slug",
    "npc_slug",
    "points_to",
    "slug",
    "type",
    "wiki_id",
}

# Keys holding a file name rather than display text.
_IMAGE_KEYS = {"icon", "image"}

# Keys whose value is a list of names, written one per line on the wiki.
_LIST_FIELDS = {"locations"}

_MARKUP_MARKERS = ("[", "{", "&", "<")


def _template_key(name: str) -> str:
    """Normalize a template name for lookup."""
    return re.sub(r"\s+", " ", name.replace("_", " ")).strip().lower()


def _display_name(name: str) -> str:
    """Turn a wiki page name into readable text.

    Underscores stand for spaces in page names and a ``#`` introduces a
    section that is not part of the name.
    """
    base = name.split("#", 1)[0]
    return base.replace("_", " ").strip()


def _positional_args(node: Template) -> list[str]:
    """Return the unnamed arguments of a template."""
    return [str(param.value).strip() for param in node.params if not param.showkey]


def _render_template(node: Template) -> str:
    """Render a template to the text it displays."""
    raw_name = str(node.name).strip()
    key = _template_key(raw_name)
    args = [arg for arg in _positional_args(node) if arg]

    # A named parameter can hold the value, e.g. {{Stat|Luck|value=30}}.
    named = {
        _template_key(str(param.name)): str(param.value).strip()
        for param in node.params
        if param.showkey and str(param.name).strip()
    }

    if key == _CASH_TEMPLATE:
        value = args[0] if args else named.get("value", "")
        return f"${value}" if value else ""

    if key in _VALUE_UNITS:
        if not args and not named.get("value"):
            return _display_name(raw_name)
        value = args[0] if args else named.get("value", "")
        return f"{value} {_display_name(raw_name)}"

    if key in _STAT_TEMPLATES:
        # {{Stat|Luck}} shows the stat, {{Stat|Luck|value=30}} shows the
        # amount as well, which is how the wiki writes a stat with its value.
        if named.get("value"):
            if args:
                return f"{args[0]} ({named['value']})"
            return named["value"]
        return args[0] if args else ""

    if key in _RARITY_TEMPLATES:
        return key.capitalize()

    if args:
        return " ".join(args)

    return _display_name(raw_name)


def _render_wikilink(node: Wikilink) -> str:
    """Render a wikilink to its display text."""
    target = str(node.title).strip()

    # A link to a file is a picture, which has no place in the text.
    if target.lower().startswith("file:"):
        return ""

    text = str(node.text).strip() if node.text is not None else ""
    if text and text != target:
        return text
    return _display_name(target)


def _strip_table_artifacts(text: str) -> str:
    """Remove leftover table markup from text that was a table cell."""
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped in {"|-", "|"}:
            continue
        # A cell that kept its own style attribute, e.g.
        # '| style="padding:3px;" | Panel line: ...'
        stripped = re.sub(r'^\|\s*style="[^"]*"\s*\|\s*', "", stripped)
        # A plain table cell marker left over from a row.
        if stripped.startswith("| ") and not stripped.startswith(("* ", "# ")):
            stripped = stripped[2:].strip()
        lines.append(stripped)
    return "\n".join(lines)


def _normalize_whitespace(text: str) -> str:
    """Normalize spaces and drop blank lines."""
    text = text.replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _render_superscript(text: str) -> str:
    """Render a superscript as a bracketed suffix.

    The wiki marks a recipe ingredient's quality with a superscript, e.g.
    ``[[Gold]]<sup>&nbsp;c</sup>`` for common gold. The marker is kept, but
    in a form that reads as part of the ingredient.
    """

    def replace(match: re.Match[str]) -> str:
        content = match.group(1).replace("&nbsp;", " ").strip()
        return f" ({content})" if content else ""

    return re.sub(r"<sup>\s*([^<]*?)\s*</sup>", replace, text, flags=re.IGNORECASE)


def _render_text(value: str) -> str:
    """Convert a wikitext fragment into plain display text.

    Templates are expanded, links are resolved to their display text, HTML is
    removed and residual table markup is cleaned up.
    """
    if not value:
        return ""

    text = value
    # Line breaks have to become newlines before the tags are stripped.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # A superscript carries a quality marker, so it is kept.
    text = _render_superscript(text)
    # Bold and italic markers are handled here because mwparserfromhell leaves
    # stray apostrophes behind when it strips them.
    text = text.replace("'''", "").replace("''", "")
    # HTML tags carry presentation, not content.
    text = re.sub(r"<[^>]+>", "", text)
    # The categories a page is in are not part of what it says.
    text = re.sub(r"\[\[\s*Category\s*:[^\]]+\]\]", "", text, flags=re.IGNORECASE)

    try:
        tree = mwparserfromhell.parse(text)
    except Exception:
        return _normalize_whitespace(text)

    for node in list(tree.filter_templates(recursive=True)):
        try:
            tree.replace(node, _render_template(node))
        except ValueError:
            # The node was already replaced as part of its parent.
            continue

    for wikilink in list(tree.filter_wikilinks(recursive=True)):
        try:
            tree.replace(wikilink, _render_wikilink(wikilink))
        except ValueError:
            continue

    text = tree.strip_code()

    # Templates that mwparserfromhell could not parse (for example a template
    # written across several lines) survive as literal text. They are not
    # display text, so remove them rather than publishing them.
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    text = text.replace("}}", "").replace("{{", "")

    text = urllib.parse.unquote(text)
    text = _strip_table_artifacts(text)
    # Some cells end with a stray '="' left over from an empty template
    # parameter.
    text = re.sub(r'="\s*$', "", text)
    return _normalize_whitespace(text)


def render_text(value: str) -> str:
    """Convert a wikitext fragment into plain display text.

    Templates are expanded, links are resolved to their display text, HTML is
    removed and residual table markup is cleaned up.
    """
    return _render_text(value)


def render_image(value: str) -> str:
    """Reduce a wiki file reference to its file name.

    ``File:Rain Stone.png|thumb|The '''Rain Stone'''`` becomes
    ``Rain Stone.png``.
    """
    if not value:
        return ""
    name = value.split("|", 1)[0].strip()
    if name.lower().startswith("file:"):
        name = name[5:].strip()
    return name


def _is_preserved(key: str) -> bool:
    """Return True when a key holds a machine value that must not be rendered."""
    if key in _PRESERVED_KEYS:
        return True
    return key.endswith(("_slug", "_url", "_id", "_hash"))


def _render_value(key: str, value: Any) -> Any:
    """Render a single value according to its key."""
    if isinstance(value, str):
        if _is_preserved(key):
            return value
        if key in _IMAGE_KEYS:
            return render_image(value)
        return render_text(value)
    if isinstance(value, list):
        return [_render_value(key, entry) for entry in value]
    if isinstance(value, dict):
        return {entry_key: _render_value(entry_key, entry) for entry_key, entry in value.items()}
    return value


def _normalize_list_field(key: str, value: Any) -> Any:
    """Turn a multi-line value into a list.

    The wiki writes a list of places one per line, so the value arrives as a
    block of text. Keeping it a list lets the site group and filter by it.
    """
    if key not in _LIST_FIELDS or not isinstance(value, str):
        return value

    entries: list[str] = []
    for line in value.split("\n"):
        cleaned = line.strip()
        # A line that is only an HTML tag is not a place.
        if not cleaned or cleaned.startswith("<"):
            continue
        if cleaned not in entries:
            entries.append(cleaned)

    return entries


def render_item_data(data: dict) -> dict:
    """Render every text value of an item.

    Machine values (slugs, colours, identifiers) and numeric values are left
    alone; file references are reduced to their file name.
    """
    if not isinstance(data, dict):
        return data
    return {
        key: _normalize_list_field(key, _render_value(key, value)) for key, value in data.items()
    }


def slugify(name: str) -> str:
    """Turn a display name into a slug fragment."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("’", "")
    )


def title_key(name: str) -> str:
    """Normalize a page title or item name so the two can be compared.

    The wiki and the scraper spell the same thing differently: underscores
    stand for spaces in a page title, and a name may use a curly apostrophe
    where the page uses a straight one. Everything is folded to a bare key so
    a page and the item it describes match.
    """
    if not name:
        return ""

    text = str(name).strip().lower()
    text = urllib.parse.unquote(text)
    text = text.replace("_", " ")
    # Every kind of apostrophe becomes the same character.
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    text = text.replace("–", "-").replace("—", "-")
    # Punctuation and spacing carry no meaning for the comparison.
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text

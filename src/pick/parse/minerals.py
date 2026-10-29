"""Parser entry point. Each parser is pure: wikitext str -> list[dict]."""

from __future__ import annotations

from typing import Any

import mwparserfromhell


def parse_minerals(wikitext: str) -> list[dict[str, Any]]:
    # Minimal stub: parse {{Mineral row ...}} and {{Mineral row slim ...}}
    # templates from Minerals page.
    tree = mwparserfromhell.parse(wikitext)
    results = []
    for node in tree.filter_templates():
        tname = str(node.name).strip().lower()
        if tname in ("mineral row", "mineral row slim"):
            # Extract named args into a dict for the parsed layer
            data: dict[str, Any] = {}
            for param in node.params:
                key = str(param.name).strip() if param.showkey else ""
                val = str(param.value).strip()
                if key:
                    data[key] = val
            results.append(
                {
                    "type": "mineral",
                    "slug": data.get("name", "").lower().replace(" ", "-"),
                    "name": data.get("name", ""),
                    "data": data,
                    "source_revid": None,
                    "parser_version": "0.1",
                }
            )
    return results

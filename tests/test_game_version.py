"""Tests for game version detection from the wiki Changelog page.

The Changelog page starts with a level-3 heading ("=== Changelog ===")
followed by level-2 version headings ("== October 2026 =="). Only the
level-2 headings name a game version.
"""

import re

import pytest

from app.services.scraper import check_for_game_update

CHANGELOG_WIKITEXT = """\
=== Changelog ===
{{Short description|...}}

== October 2026 ==
* Added the Meteor Valley expansion.

== September 2026 ==
* Added runes.

== August 2026 ==
* Added the Summer Event.
"""

VERSION_PATTERN = r"(?m)^(==)\s+([^=].*?)\s+\1\s*$"


def _parse_version(wikitext: str) -> str | None:
    """Mirror the parsing done by check_for_game_update."""
    match = re.search(VERSION_PATTERN, wikitext)
    return match.group(2).strip() if match else None


def test_latest_version_is_extracted():
    """The most recent level-2 heading is the current game version."""
    assert _parse_version(CHANGELOG_WIKITEXT) == "October 2026"


def test_level_three_heading_is_not_a_version():
    """'=== Changelog ===' must never be stored as the game version."""
    assert _parse_version(CHANGELOG_WIKITEXT) != "= Changelog ="
    assert _parse_version(CHANGELOG_WIKITEXT) != "Changelog"


def test_version_with_event_suffix_is_parsed():
    """Version headings that carry an event suffix are kept verbatim."""
    wikitext = "== June 2026 - Summer Event ==\n* Notes.\n"
    assert _parse_version(wikitext) == "June 2026 - Summer Event"


def test_missing_version_heading_returns_none():
    """A page without any level-2 heading has no detectable version."""
    assert _parse_version("=== Changelog ===\nNo versions yet.\n") is None


@pytest.mark.asyncio
async def test_check_for_game_update_stores_real_version(monkeypatch):
    """check_for_game_update stores the real version, not the page heading."""
    from app.models import GameVersion

    recorded: list[GameVersion] = []

    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeSession:
        async def execute(self, _stmt):
            return FakeResult()

        def add(self, obj):
            recorded.append(obj)

        async def commit(self):
            return None

    class FakeClient:
        async def get_page_info(self, title):
            assert title == "Changelog"
            return {"wikitext": CHANGELOG_WIKITEXT}

        async def close(self):
            return None

    session = FakeSession()
    await check_for_game_update(session, FakeClient())

    assert len(recorded) == 1
    assert recorded[0].version == "October 2026"

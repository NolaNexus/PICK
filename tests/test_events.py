"""Tests for events parser using live wiki fixtures."""

from pathlib import Path

from scrapers.events import parse_events

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "Events.wiki"


def test_events_parser_returns_items():
    """Events parser should parse events from all three tabber sections."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    # Should have Regular (13) + Limited-Time (6) + Admin-Exclusive (9) = 28 events
    assert len(items) == 28, f"Expected 28 events, got {len(items)}"


def test_events_have_required_fields():
    """Every event item must have id, type, name, slug, data, image_url."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    for item in items:
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "event"


def test_events_data_structure():
    """Event data dict should contain category, description, effects, dialogue, image, is_admin, is_limited_time."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    for item in items:
        data = item["data"]
        assert "category" in data
        assert "description" in data
        assert "effects" in data
        assert "dialogue" in data
        assert "image" in data
        assert "is_admin" in data
        assert "is_limited_time" in data
        assert data["category"] in ("regular", "limited_time", "admin_exclusive")
        assert isinstance(data["effects"], list)
        assert isinstance(data["dialogue"], list)
        assert isinstance(data["is_admin"], bool)
        assert isinstance(data["is_limited_time"], bool)


def test_events_slug_is_unique():
    """All event slugs should be unique."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


def test_regular_events_parsed():
    """Regular events should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    regular = [i for i in items if i["data"]["category"] == "regular"]
    assert len(regular) == 13, f"Expected 13 regular events, got {len(regular)}"

    # Check specific regular events
    event_names = [i["name"] for i in regular]
    assert "Blizzard" in event_names
    assert "Geode Shower" in event_names
    assert "Meteor Shower" in event_names
    assert "Mythic Rift" in event_names
    assert "Nimue's Blessing" in event_names
    assert "River Rapids" in event_names
    assert "Solar Flare" in event_names
    assert "Volcanic Eruption" in event_names
    assert "Swamp Fog" in event_names
    assert "Modifier Surge" in event_names
    assert "Starfall" in event_names
    assert "Sandstorm" in event_names
    assert "The Void" in event_names

    # Check Blizzard effects
    blizzard = next(i for i in regular if i["name"] == "Blizzard")
    assert "Snowy Mountain" in blizzard["data"]["description"]
    assert len(blizzard["data"]["effects"]) > 0
    assert "1.5&times; Stats" in " ".join(blizzard["data"]["effects"])
    assert blizzard["data"]["image"] == "BlizzardProspecting.png|center|500px"
    assert blizzard["data"]["is_admin"] is False


def test_limited_time_events_parsed():
    """Limited-time events should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    limited = [i for i in items if i["data"]["category"] == "limited_time"]
    assert len(limited) == 6, f"Expected 6 limited-time events, got {len(limited)}"

    event_names = [i["name"] for i in limited]
    assert "Hallows' Eve" in event_names
    assert "Candy Canes" in event_names
    assert "Rose Rain" in event_names
    assert "Egg Hunt" in event_names
    assert "Shifting Tides" in event_names
    assert "Night of the Bonfire" in event_names

    # Check Hallows' Eve
    hallows = next(i for i in limited if i["name"] == "Hallows' Eve")
    assert hallows["data"]["is_limited_time"] is True
    assert hallows["data"]["is_admin"] is False
    assert "Spooky modifier" in " ".join(hallows["data"]["effects"])


def test_admin_exclusive_events_parsed():
    """Admin-exclusive events should be parsed correctly."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    admin = [i for i in items if i["data"]["category"] == "admin_exclusive"]
    assert len(admin) == 9, f"Expected 9 admin-exclusive events, got {len(admin)}"

    event_names = [i["name"] for i in admin]
    assert "Admin Shower" in event_names
    assert "Thunderstorm" in event_names
    assert "4× Luck" in event_names
    assert "8× Luck" in event_names
    assert "Admin Blessing" in event_names
    assert "Dul Dul Dul!" in event_names
    assert "Cookie Time!" in event_names
    assert "Rainbow!" in event_names
    assert "Christmas Blessing" in event_names

    # Check Admin Shower
    admin_shower = next(i for i in admin if i["name"] == "Admin Shower")
    assert admin_shower["data"]["is_admin"] is True
    assert admin_shower["data"]["is_limited_time"] is False
    assert "2&times; (+1&times;) Luck" in " ".join(admin_shower["data"]["effects"])
    assert "2&times; (+1&times;) Dig Amount" in " ".join(admin_shower["data"]["effects"])


def test_known_event_dialogue():
    """Events should have dialogue extracted."""
    wikitext = FIXTURE_PATH.read_text()
    items = parse_events(wikitext)

    meteor_shower = next(i for i in items if i["name"] == "Meteor Shower")
    assert len(meteor_shower["data"]["dialogue"]) >= 3
    assert "A meteor shower has begun!" in " ".join(meteor_shower["data"]["dialogue"])
    assert "Player]!" in " ".join(meteor_shower["data"]["dialogue"])
    assert "ended" in " ".join(meteor_shower["data"]["dialogue"]).lower()

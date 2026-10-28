"""Tests for the locations parser using live wiki fixtures."""

from pathlib import Path

from scrapers.locations import parse_locations

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "locations.wiki"


def _items():
    return parse_locations(FIXTURE_PATH.read_text())


def test_locations_parser_returns_correct_count():
    """The page has 18 tabs, but the Museum is a place inside Caldera Park."""
    items = _items()

    assert len(items) == 17, f"Expected 17 areas, got {len(items)}"


def test_locations_have_required_fields():
    """Every location item must have id, type, name, slug, data, image_url."""
    for item in _items():
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "slug" in item
        assert "data" in item
        assert "image_url" in item
        assert item["type"] == "location"


def test_locations_data_structure():
    """Location data holds the category, the description and its places."""
    for item in _items():
        data = item["data"]
        assert "category" in data
        assert "description" in data
        assert "sublocations" in data
        assert isinstance(data["sublocations"], list)


def test_locations_slug_matches_name():
    """Slug should be lowercase name with spaces/hyphens normalized."""
    for item in _items():
        expected_slug = (
            item["name"]
            .lower()
            .replace(" ", "-")
            .replace("'", "")
            .replace("(", "")
            .replace(")", "")
        )
        assert item["slug"] == expected_slug
        assert item["id"] == expected_slug


def test_the_two_kinds_of_area():
    """Areas are either always there or only during an event."""
    categories = {item["name"]: item["data"]["category"] for item in _items()}

    assert categories["Caldera Park"] == "regular"
    assert categories["Haunted Creek"] == "limited_time"
    assert categories["Easter Event Shop"] == "limited_time"


def test_a_place_inside_an_area():
    """A known area holds the places inside it."""
    caldera = next(i for i in _items() if i["name"] == "Caldera Park")
    names = [entry["name"] for entry in caldera["data"]["sublocations"]]

    assert "Volcanic Sands" in names
    assert "Volcanic Springs" in names
    assert "Windswept Beach" in names
    assert "Magma Furnace" in names
    assert "Infernal Heart" in names


def test_the_museum_is_a_place_in_caldera_park():
    """The Museum is a place inside Caldera Park, not an area of its own."""
    items = _items()

    assert not any(item["name"] == "Museum" for item in items)

    caldera = next(i for i in items if i["name"] == "Caldera Park")
    museum = next(
        (entry for entry in caldera["data"]["sublocations"] if entry["name"] == "Museum"),
        None,
    )
    assert museum is not None, "The Museum should be a place inside Caldera Park"


def test_every_place_is_found():
    """The page holds 34 places across its areas."""
    places = [entry["name"] for item in _items() for entry in item["data"]["sublocations"]]
    assert len(places) == 34, f"Expected 34 places, got {len(places)}"


def test_a_place_knows_its_toughness_and_people():
    """A place reads its toughness, its people and its picture."""
    caldera = next(i for i in _items() if i["name"] == "Caldera Park")
    sands = next(
        entry for entry in caldera["data"]["sublocations"] if entry["name"] == "Volcanic Sands"
    )

    assert sands["toughness"] == 4.0
    assert "Ranger" in sands["npcs"]
    assert sands["image"] == "volcanichuts.png"


def test_a_place_without_a_toughness_is_allowed():
    """The Museum has no toughness, which is not an error."""
    caldera = next(i for i in _items() if i["name"] == "Caldera Park")
    museum = next(entry for entry in caldera["data"]["sublocations"] if entry["name"] == "Museum")

    assert museum["toughness"] is None
    assert "Receptionist" in museum["npcs"]

"""Tests for filling items in from the pages that describe them."""

from pathlib import Path

from app.models import Item
from app.services.enrichment import _is_empty, _merge_into, _merge_modifiers, _values_agree

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "item_pages"


def _page(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.wiki").read_text()


class TestEmptyValues:
    def test_nothing_is_empty(self):
        assert _is_empty(None) is True
        assert _is_empty("") is True
        assert _is_empty("  ") is True
        assert _is_empty([]) is True
        assert _is_empty({}) is True

    def test_a_value_is_not_empty(self):
        assert _is_empty("something") is False
        assert _is_empty(0) is False
        assert _is_empty([1]) is False


class TestAgreement:
    def test_the_same_text_agrees(self):
        assert _values_agree("Haunted Creek", "haunted creek") is True

    def test_different_text_does_not_agree(self):
        assert _values_agree("2,000", "3,000") is False

    def test_the_same_number_agrees(self):
        assert _values_agree(2.0, 2) is True

    def test_different_numbers_do_not_agree(self):
        assert _values_agree(2.0, 3.0) is False


class TestMerging:
    def _item(self, **data):
        return Item(
            type="mineral",
            name="Moonspire",
            slug="mineral-moonspire",
            data=data,
            is_active=True,
        )

    def test_an_empty_field_is_filled(self):
        from scrapers.item_page import parse_item_page

        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        item = self._item(value=45000000, locations=[], description="")

        filled, conflicts = _merge_into(item, parsed)

        assert filled >= 1
        assert conflicts == []
        assert item.data["locations"] == ["Haunted Creek"]
        assert item.data["description"].startswith("A spire of crystallised moonlight")

    def test_a_stored_value_is_kept(self):
        from scrapers.item_page import parse_item_page

        parsed = parse_item_page("Moonspire", _page("Moonspire"))
        item = self._item(description="The value the index gave.")

        filled, conflicts = _merge_into(item, parsed)

        assert item.data["description"] == "The value the index gave."
        # The difference is reported, but the stored value stands.
        assert any(conflict["field"] == "description" for conflict in conflicts)

    def test_a_difference_is_reported_as_a_conflict(self):
        from scrapers.item_page import parse_item_page

        parsed = parse_item_page("Iron Shovel", _page("Iron_Shovel"))
        item = self._item(type="shovel", name="Iron Shovel", price="2,000")

        _filled, conflicts = _merge_into(item, parsed)

        # The index value stays.
        assert item.data["price"] == "2,000"
        assert any(
            conflict["field"] == "price"
            and conflict["stored"] == "2,000"
            and conflict["page"] == "3,000"
            for conflict in conflicts
        )


class TestModifierMerging:
    def test_a_stored_modifier_wins(self):
        stored = [{"stat": "Luck", "amount": 5.0, "unit": "flat"}]
        page = [{"stat": "Luck", "amount": 5.0, "unit": "flat"}]

        assert _merge_modifiers(stored, page) == stored

    def test_a_new_modifier_is_added(self):
        stored = [{"stat": "Luck", "amount": 5.0, "unit": "flat"}]
        page = [{"stat": "Toughness", "amount": 1.0, "unit": "flat"}]

        merged = _merge_modifiers(stored, page)
        assert len(merged) == 2

    def test_no_stored_modifiers_takes_the_page(self):
        page = [{"stat": "Luck", "amount": 5.0, "unit": "flat"}]
        assert _merge_modifiers(None, page) == page


def test_the_merge_works_on_an_item_row():
    """The merge works on the item rows the database holds."""
    from scrapers.item_page import parse_item_page

    item = Item(
        type="mineral",
        name="Moonspire",
        slug="mineral-moonspire-test",
        data={"locations": [], "description": ""},
        is_active=True,
    )

    parsed = parse_item_page("Moonspire", _page("Moonspire"))
    filled, _ = _merge_into(item, parsed)

    assert filled > 0
    assert item.data["locations"] == ["Haunted Creek"]

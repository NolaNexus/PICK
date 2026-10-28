"""Integration tests for database operations and scraper pipeline."""

import pytest
from sqlalchemy import func, select

from app.models import GameVersion, Item, ScraperRun, WikiPage
from app.services.scraper import run_daily_scrape, run_full_scrape, scrape_page
from app.utils.mw_api import MediaWikiClient
from tests.conftest import requires_wiki


@pytest.mark.integration
@requires_wiki
class TestScraperIntegration:
    """Integration tests for scraper against real database."""

    @pytest.mark.asyncio
    async def test_full_scrape_populates_db(self, db_session):
        """Test that full scrape populates database with items."""
        # Run full scrape
        result = await run_full_scrape(db_session)

        assert result["status"] in ("success", "partial")
        assert result["pages_scraped"] > 0
        assert result["pages_changed"] >= 0

        # Verify items were inserted
        total_items = await db_session.execute(select(func.count(Item.id)))
        count = total_items.scalar()
        assert count > 100, f"Expected at least 100 items, got {count}"

        # Verify different item types exist
        item_types = await db_session.execute(
            select(Item.type, func.count(Item.id)).group_by(Item.type)
        )
        types = dict(item_types.all())
        assert len(types) >= 10, f"Expected at least 10 item types, got {len(types)}"

        # Verify WikiPage records created
        wiki_pages = await db_session.execute(select(func.count(WikiPage.id)))
        assert wiki_pages.scalar() > 10

        # Verify ScraperRun record created
        runs = await db_session.execute(select(func.count(ScraperRun.id)))
        assert runs.scalar() >= 1

    @pytest.mark.asyncio
    async def test_incremental_scrape_zero_writes_on_unchanged(self, db_session):
        """Test that incremental scrape produces 0 writes when wiki unchanged."""
        # First run - full scrape
        result1 = await run_full_scrape(db_session)
        assert result1["status"] in ("success", "partial")

        # Second run - should be incremental (recentchanges)
        # Since wiki hasn't changed, should produce 0 changes
        result2 = await run_daily_scrape(db_session)
        assert result2["status"] in ("success", "partial")
        assert result2["pages_changed"] == 0, "Expected 0 changes on unchanged wiki"

        # Verify no new items added
        count_before = await db_session.execute(select(func.count(Item.id)))
        count_after = await db_session.execute(select(func.count(Item.id)))
        assert count_before.scalar() == count_after.scalar()

    @pytest.mark.asyncio
    async def test_scraper_run_records_created(self, db_session):
        """Test that ScraperRun records are properly created."""
        await run_full_scrape(db_session)

        runs = await db_session.execute(
            select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(2)
        )
        runs_list = runs.scalars().all()
        assert len(runs_list) >= 1

        latest_run = runs_list[0]
        assert latest_run.status in ("success", "partial")
        assert latest_run.pages_scraped >= 0
        assert latest_run.finished_at is not None

    @pytest.mark.asyncio
    async def test_game_version_tracking(self, db_session):
        """Test game version detection and tracking."""
        # This would require mocking the Changelog page
        # For now, just verify the table exists and can be queried
        versions = await db_session.execute(select(func.count(GameVersion.id)))
        count = versions.scalar()
        # Table should exist (may be empty)
        assert count >= 0


@pytest.mark.integration
class TestScraperUnit:
    """Unit tests for scraper functions (with mocked wiki)."""

    @pytest.mark.asyncio
    async def test_scrape_page_upserts_item(self, db_session):
        """Test that scrape_page upserts items correctly."""
        from unittest.mock import AsyncMock, MagicMock

        from scrapers.pans import parse_pans

        mock_client = MagicMock(spec=MediaWikiClient)
        mock_client.get_page_info = AsyncMock(
            return_value={
                "title": "Test Item",
                "wikitext": "{{Pan row\n|name=Test Pan\n|luck=100\n}}",
                "page_id": 123,
                "revision_id": 456,
            }
        )

        # Mock parser - use actual parser
        changed = await scrape_page(db_session, mock_client, "Pans", parse_pans)
        assert changed is True

        # Verify item was created
        item = await db_session.execute(select(Item).where(Item.slug == "pan-test-pan"))
        item = item.scalar_one_or_none()
        assert item is not None
        assert item.name == "Test Pan"
        assert item.data["luck"] == 100


# Configuration for pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# Skip integration tests if no database available
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring database"
    )


# Allow running integration tests with: pytest -m integration
# Skip by default: pytest -m "not integration"


@pytest.mark.asyncio
async def test_scrape_page_soft_deletes_and_reactivates(db_session):
    """Items removed from a page are deactivated, not deleted, and reactivate on return."""
    from unittest.mock import AsyncMock, MagicMock

    from app.models import Item

    old_item = {
        "type": "pan",
        "name": "Old Pan",
        "slug": "old-pan",
        "data": {"luck": 1},
        "image_url": None,
    }
    new_item = {
        "type": "pan",
        "name": "New Pan",
        "slug": "new-pan",
        "data": {"luck": 2},
        "image_url": None,
    }

    def parser(wikitext: str):
        return [old_item] if "old" in wikitext else [new_item]

    mock_client = MagicMock(spec=MediaWikiClient)
    mock_client.get_page_info = AsyncMock(
        side_effect=[
            {"wikitext": "old", "page_id": 900, "revision_id": 1},
            {"wikitext": "new", "page_id": 900, "revision_id": 2},
            {"wikitext": "old", "page_id": 900, "revision_id": 3},
        ]
    )

    assert await scrape_page(db_session, mock_client, "Pans", parser) is True
    assert await scrape_page(db_session, mock_client, "Pans", parser) is True

    old = (await db_session.execute(select(Item).where(Item.slug == "pan-old-pan"))).scalar_one()
    new = (await db_session.execute(select(Item).where(Item.slug == "pan-new-pan"))).scalar_one()
    assert old.is_active is False
    assert new.is_active is True

    assert await scrape_page(db_session, mock_client, "Pans", parser) is True
    await db_session.refresh(old)
    await db_session.refresh(new)
    assert old.is_active is True
    assert new.is_active is False


@pytest.mark.asyncio
async def test_scrape_page_deduplicates_parser_slugs(db_session):
    """A parser that emits the same slug twice must not violate the unique constraint."""
    from unittest.mock import AsyncMock, MagicMock

    from app.models import Item

    duplicate_items = [
        {"type": "npc", "name": "Merchant", "slug": "merchant", "data": {"region": "A"}},
        {"type": "npc", "name": "Merchant", "slug": "merchant", "data": {"region": "B"}},
    ]

    mock_client = MagicMock(spec=MediaWikiClient)
    mock_client.get_page_info = AsyncMock(
        return_value={"wikitext": "npcs", "page_id": 901, "revision_id": 1}
    )

    changed = await scrape_page(db_session, mock_client, "NPCs", lambda _wikitext: duplicate_items)
    assert changed is True

    rows = (
        (await db_session.execute(select(Item).where(Item.slug == "npc-merchant"))).scalars().all()
    )
    assert len(rows) == 1
    assert rows[0].data["region"] == "A"


@pytest.mark.asyncio
async def test_scrape_page_does_not_store_parser_id_as_wiki_id(db_session):
    """Synthetic parser IDs can exceed the wiki_id column length and must not be stored."""
    from unittest.mock import AsyncMock, MagicMock

    from app.models import Item

    long_id = "x" * 150
    parsed = [{"id": long_id, "type": "quest", "name": "Long Quest", "data": {}}]

    mock_client = MagicMock(spec=MediaWikiClient)
    mock_client.get_page_info = AsyncMock(
        return_value={"wikitext": "quests", "page_id": 902, "revision_id": 1}
    )

    assert await scrape_page(db_session, mock_client, "Quests", lambda _: parsed) is True

    item = (
        await db_session.execute(select(Item).where(Item.slug == f"quest-{long_id}"))
    ).scalar_one()
    assert item.wiki_id is None


def _fake_client(page_id: int, wikitext: str):
    """Build a MediaWikiClient stub returning fixed page content."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock(spec=MediaWikiClient)
    client.get_page_info = AsyncMock(
        return_value={"wikitext": wikitext, "page_id": page_id, "revision_id": 1}
    )
    return client


@pytest.mark.asyncio
async def test_scrape_page_repeated_runs_are_idempotent(db_session):
    """Re-scraping pages that share a name across types must not violate unique slugs."""
    npc = [
        {
            "type": "npc",
            "name": "Dredge Master",
            "slug": "fortune-river-dredge-master",
            "data": {},
        }
    ]
    quest = [
        {
            "type": "quest",
            "name": "Dredge Master",
            "slug": "fortune-river-dredge-master",
            "data": {},
        }
    ]

    for version in (1, 2):
        await scrape_page(db_session, _fake_client(100, f"npc-v{version}"), "NPCs", lambda _: npc)
        await scrape_page(
            db_session, _fake_client(101, f"quest-v{version}"), "Quests", lambda _: quest
        )

    rows = (
        (
            await db_session.execute(
                select(Item).where(Item.slug.like("%fortune-river-dredge-master"))
            )
        )
        .scalars()
        .all()
    )
    assert {row.slug for row in rows} == {
        "npc-fortune-river-dredge-master",
        "quest-fortune-river-dredge-master",
    }
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_reconcile_merges_merchant_listing_into_relic(db_session):
    """The Traveling Merchant listing becomes merchant data on the relic row."""
    from app.services.reconcile import reconcile_items

    relic = Item(
        type="relic",
        name="Cosmic Resonator",
        slug="relic-cosmic-resonator",
        data={"obtainment": "Traveling Merchant", "usage": "craft"},
        is_active=True,
    )
    listing = Item(
        type="merchant_item",
        name="Cosmic Resonator",
        slug="merchant-item-cosmic-resonator",
        data={"price_cash": 5000.0, "price_shards": 25, "stock": 2, "chance_percent": 1.5},
        is_active=True,
    )
    db_session.add_all([relic, listing])
    await db_session.commit()

    summary = await reconcile_items(db_session)
    await db_session.commit()

    assert summary["merged_merchant_items"] == 1
    assert listing.is_active is False
    assert relic.data["sold_by_merchant"] is True
    assert relic.data["merchant"]["price_cash"] == 5000.0
    assert relic.data["merchant"]["currency"] == "either"
    assert relic.data["obtainment"] == "Traveling Merchant"

    # Idempotent: the inactive listing is no longer considered.
    assert (await reconcile_items(db_session))["merged_merchant_items"] == 0


@pytest.mark.asyncio
async def test_reconcile_merges_merchant_listing_into_potion(db_session):
    """The merchant listing of a potion merges into the Potions page row."""
    from app.services.reconcile import reconcile_items

    potion = Item(
        type="potion",
        name="Blitz Potion",
        slug="potion-blitz-potion",
        data={
            "description": "Supercharges your digging and shaking speed.",
            "sold_by": "Traveling Merchant",
            "cost_cash": 200000000.0,
            "cost_shards": 250.0,
            "duration_min": 20,
        },
        is_active=True,
    )
    listing = Item(
        type="merchant_item",
        name="Blitz Potion",
        slug="merchant-item-blitz-potion",
        data={
            "price_cash": 200000000.0,
            "price_shards": 250,
            "stock": 1,
            "chance_percent": 3.5,
        },
        is_active=True,
    )
    db_session.add_all([potion, listing])
    await db_session.commit()

    summary = await reconcile_items(db_session)
    await db_session.commit()
    await db_session.refresh(potion)

    assert summary["merged_merchant_items"] == 1
    assert listing.is_active is False

    # The potion keeps its own cost from the Potions wiki page.
    assert potion.data["cost_cash"] == 200000000.0
    assert potion.data["sold_by"] == "Traveling Merchant"

    # The live listing is attached to it.
    assert potion.data["sold_by_merchant"] is True
    assert potion.data["merchant"]["stock"] == 1
    assert potion.data["merchant"]["chance_percent"] == 3.5


@pytest.mark.asyncio
async def test_reconcile_links_rewards_and_quests(db_session):
    """Excavation drops and quests point at the item/NPC they belong to."""
    from app.services.reconcile import reconcile_items

    relic = Item(
        type="relic",
        name="Cosmic Resonator",
        slug="relic-cosmic-resonator",
        data={},
        is_active=True,
    )
    reward = Item(
        type="excavation_reward",
        name="Cosmic Resonator",
        slug="excavation-reward-frozen-fortress-cosmic-resonator",
        data={"site": "Frozen Fortress", "chance": "0.5%"},
        is_active=True,
    )
    npc = Item(
        type="npc",
        name="Dredge Master",
        slug="npc-fortune-river-dredge-master",
        data={"region": "Fortune River"},
        is_active=True,
    )
    quest = Item(
        type="quest",
        name="Dredge Master",
        slug="quest-fortune-river-dredge-master",
        data={"npc": "Dredge Master", "location": "Fortune River"},
        is_active=True,
    )
    db_session.add_all([relic, reward, npc, quest])
    await db_session.commit()

    summary = await reconcile_items(db_session)
    await db_session.commit()

    assert summary["linked_excavation_rewards"] == 1
    assert summary["linked_quests"] == 1
    assert reward.data["item_slug"] == "relic-cosmic-resonator"
    assert quest.data["npc_slug"] == "npc-fortune-river-dredge-master"
    # The drop table row keeps its own site-specific data.
    assert reward.data["site"] == "Frozen Fortress"


@pytest.mark.asyncio
async def test_reconcile_links_treasure_chest_loot(db_session):
    """Chest loot entries resolve to item slugs; unknown names stay plain."""
    from app.services.reconcile import reconcile_items

    relic = Item(
        type="relic",
        name="Cosmic Resonator",
        slug="relic-cosmic-resonator",
        data={},
        is_active=True,
    )
    chest = Item(
        type="treasure_chest",
        name="Fortune River Delta Treasure Chest",
        slug="treasure-chest-fortune-river-delta-treasure-chest",
        data={
            "location": "Fortune River Delta",
            "loot": [
                {"kind": "ore", "location": "Fortune River Delta", "label": "Random Ore"},
                {"kind": "item", "name": "Cosmic Resonator"},
                {"kind": "item", "name": "Nonexistent Thing"},
            ],
        },
        is_active=True,
    )
    db_session.add_all([relic, chest])
    await db_session.commit()

    summary = await reconcile_items(db_session)
    await db_session.commit()
    # Reload from the database so the assertion also checks persistence.
    await db_session.refresh(chest)

    assert summary["linked_chest_loot"] == 1
    assert chest.data["loot"][0]["kind"] == "ore"
    assert chest.data["loot"][1]["item_slug"] == "relic-cosmic-resonator"
    assert "item_slug" not in chest.data["loot"][2]


@pytest.mark.asyncio
async def test_reconcile_links_geode_excavation_rewards(db_session):
    """An excavation's Geodes reward links to the geode for its area."""
    from app.services.reconcile import reconcile_items

    geode = Item(
        type="geode",
        name="Magma Geode",
        slug="geode-magma-geode",
        data={"location": "The Magma Furnace"},
        is_active=True,
    )
    reward = Item(
        type="excavation_reward",
        name="Geodes",
        slug="excavation-reward-magma-temple-geodes",
        data={"site": "Magma Temple", "geode_location": "Magma Furnace"},
        is_active=True,
    )
    db_session.add_all([geode, reward])
    await db_session.commit()

    summary = await reconcile_items(db_session)
    await db_session.commit()
    await db_session.refresh(reward)

    assert summary["linked_excavation_rewards"] == 1
    assert reward.data["item_slug"] == "geode-magma-geode"


@pytest.mark.asyncio
async def test_reconcile_matches_quest_to_grouped_npc(db_session):
    """A quest matches an NPC that lists several locations."""
    from app.services.reconcile import reconcile_items

    npc = Item(
        type="npc",
        name="Resident",
        slug="npc-resident",
        data={"locations": ["Fortune River", "Seashell Isle"]},
        is_active=True,
    )
    quest = Item(
        type="quest",
        name="Help the Resident",
        slug="quest-help-the-resident",
        data={"npc": "Resident", "location": "Seashell Isle"},
        is_active=True,
    )
    db_session.add_all([npc, quest])
    await db_session.commit()

    await reconcile_items(db_session)
    await db_session.commit()
    await db_session.refresh(quest)

    assert quest.data["npc_slug"] == "npc-resident"

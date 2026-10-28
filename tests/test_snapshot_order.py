"""The snapshot must be built in a stable order.

The export only rewrites ``frontend/public/snapshot.json`` when the data
actually changed. If the rows came back from the database in a different
order each time, the file would differ on every run and the job would commit
it daily for no reason.
"""

from sqlalchemy import insert

from app.models import Item
from app.services.snapshot import build_snapshot


async def test_the_items_come_back_in_slug_order(db_session):
    """The snapshot lists the items sorted by slug, whatever the insert order."""
    await db_session.execute(
        insert(Item),
        [
            {"type": "pan", "name": "Metal Pan", "slug": "pan-metal-pan", "data": {}},
            {"type": "shovel", "name": "Shovel", "slug": "shovel-shovel", "data": {}},
            {"type": "mineral", "name": "Quartz", "slug": "mineral-quartz", "data": {}},
        ],
    )
    await db_session.commit()

    snapshot = await build_snapshot(db_session)
    slugs = [item["slug"] for item in snapshot["items"]]

    assert slugs == ["mineral-quartz", "pan-metal-pan", "shovel-shovel"]


async def test_the_order_is_the_same_every_time(db_session):
    """Two builds of the same data produce the same order."""
    await db_session.execute(
        insert(Item),
        [
            {"type": "pan", "name": "Metal Pan", "slug": "pan-metal-pan", "data": {}},
            {"type": "shovel", "name": "Shovel", "slug": "shovel-shovel", "data": {}},
            {"type": "mineral", "name": "Quartz", "slug": "mineral-quartz", "data": {}},
        ],
    )
    await db_session.commit()

    first = await build_snapshot(db_session)
    second = await build_snapshot(db_session)

    assert [i["slug"] for i in first["items"]] == [i["slug"] for i in second["items"]]


async def test_inactive_items_are_not_in_the_snapshot(db_session):
    """A soft-deleted item stays out of the published data."""
    await db_session.execute(
        insert(Item),
        [
            {"type": "pan", "name": "Metal Pan", "slug": "pan-metal-pan", "data": {}},
            {
                "type": "mineral",
                "name": "Gone",
                "slug": "mineral-gone",
                "data": {},
                "is_active": False,
            },
        ],
    )
    await db_session.commit()

    snapshot = await build_snapshot(db_session)
    slugs = [item["slug"] for item in snapshot["items"]]

    assert "mineral-gone" not in slugs
    assert snapshot["counts"]["items"] == 1


async def test_the_count_matches_the_items(db_session):
    """The published count agrees with the rows that were written."""
    await db_session.execute(
        insert(Item),
        [
            {"type": "pan", "name": "Metal Pan", "slug": "pan-metal-pan", "data": {}},
            {"type": "shovel", "name": "Shovel", "slug": "shovel-shovel", "data": {}},
        ],
    )
    await db_session.commit()

    snapshot = await build_snapshot(db_session)

    assert snapshot["counts"]["items"] == len(snapshot["items"])

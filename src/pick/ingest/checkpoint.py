"""Ingest pipeline: raw layer writer with checkpointing."""

from sqlalchemy import create_engine, text

from pick.config import Settings


def get_engine(url: str | None = None):
    s = Settings()
    return create_engine(url or s.database_url)


def checkpoint_run(conn, run_id: int, page_id: int, revid: int):
    conn.execute(
        text("""
        INSERT INTO raw.ingest_checkpoint (run_id, page_id, revid, done_at)
        VALUES (:run_id, :page_id, :revid, now())
        ON CONFLICT (run_id, page_id) DO NOTHING
    """),
        {"run_id": run_id, "page_id": page_id, "revid": revid},
    )

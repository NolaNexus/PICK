revision = "001_initial_raw_layer"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.wiki_page (
            page_id int PRIMARY KEY,
            title text NOT NULL,
            namespace int NOT NULL DEFAULT 0,
            touched_at timestamptz,
            first_seen timestamptz NOT NULL DEFAULT now(),
            last_missing_at timestamptz
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.page_revision (
            page_id int NOT NULL REFERENCES raw.wiki_page(page_id),
            revid bigint NOT NULL,
            parent_revid bigint,
            sha1 text NOT NULL,
            fetched_at timestamptz NOT NULL DEFAULT now(),
            content text NOT NULL,
            ingest_run_id bigint,
            PRIMARY KEY (page_id, revid)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_rev_sha1 ON raw.page_revision(sha1)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_rev_fetched ON raw.page_revision(fetched_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.ingest_run (
            run_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            started_at timestamptz NOT NULL DEFAULT now(),
            finished_at timestamptz,
            status text NOT NULL DEFAULT 'running',
            mode text,
            summary jsonb
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.ingest_checkpoint (
            run_id int NOT NULL REFERENCES raw.ingest_run(run_id) ON DELETE CASCADE,
            page_id int NOT NULL,
            revid bigint NOT NULL,
            done_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (run_id, page_id)
        )
    """)


def downgrade(conn):
    conn.execute("DROP TABLE IF EXISTS raw.ingest_checkpoint")
    conn.execute("DROP TABLE IF EXISTS raw.ingest_run")
    conn.execute("DROP TABLE IF EXISTS raw.page_revision")
    conn.execute("DROP TABLE IF EXISTS raw.wiki_page")
    conn.execute("DROP SCHEMA IF EXISTS raw")

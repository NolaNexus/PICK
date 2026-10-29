"""Lightweight end-to-end validation (no wiki access for CI)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_imports():
    from pick.config import Settings

    assert Settings().database_url.startswith("postgresql")


def test_parser_fixture():
    from pick.parse.minerals import parse_minerals

    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "wikitext", "Minerals.wiki")
    if os.path.exists(fixture_path):
        text = open(fixture_path).read()
        result = parse_minerals(text)
        assert isinstance(result, list)


def test_raw_schema_exists():
    from pick.ingest.checkpoint import get_engine

    engine = get_engine()
    from sqlalchemy import inspect

    insp = inspect(engine)
    assert "wiki_page" in insp.get_table_names(schema="raw")

"""Tests for the item coverage report."""

from scripts.coverage_report import (
    _split_tables,
    count_table_rows,
    looks_like_item_list,
    render_markdown,
)


class TestTableSplitting:
    def test_single_table(self):
        wikitext = '{| class="wikitable"\n! Item !! Cost\n|-\n| a || b\n|}'
        tables = _split_tables(wikitext)
        assert len(tables) == 1
        assert "Item" in tables[0]

    def test_two_tables(self):
        wikitext = "{| \n! a\n|}\ntext\n{| \n! b\n|}"
        assert len(_split_tables(wikitext)) == 2

    def test_no_tables(self):
        assert _split_tables("just some text") == []


class TestRowCounting:
    def test_rows_are_counted(self):
        wikitext = "{| \n! Item !! Cost\n|-\n| a || b\n|-\n| c || d\n|}"
        assert count_table_rows(wikitext) == 2

    def test_a_table_without_rows(self):
        assert count_table_rows("{| \n! Item !! Cost\n|}") == 0


class TestItemListDetection:
    def test_a_table_with_an_item_header(self):
        wikitext = '{| class="wikitable"\n! Item !! Cost\n|-\n| a || b\n|}'
        assert looks_like_item_list(wikitext) is True

    def test_a_table_without_an_item_header(self):
        wikitext = '{| class="wikitable"\n! Name !! Effect\n|-\n| a || b\n|}'
        assert looks_like_item_list(wikitext) is False

    def test_a_page_without_tables(self):
        assert looks_like_item_list("some prose") is False


class TestMarkdown:
    def test_a_full_coverage_report(self):
        report = {
            "pages": [
                {"page": "Pans", "status": "tracked", "table_rows": 10, "items": 10, "missing": 0}
            ],
            "untracked": [],
            "errors": [],
        }
        markdown = render_markdown(report)
        assert "Every tracked page is fully captured." in markdown
        assert "Pans" not in markdown

    def test_a_gap_is_listed(self):
        report = {
            "pages": [
                {
                    "page": "Potions",
                    "status": "tracked",
                    "table_rows": 20,
                    "items": 3,
                    "missing": 17,
                }
            ],
            "untracked": [],
            "errors": [],
        }
        markdown = render_markdown(report)
        assert "Potions" in markdown
        assert "| 17 |" in markdown

    def test_a_page_without_a_parser_is_listed(self):
        report = {
            "pages": [
                {
                    "page": "Codes",
                    "status": "no parser",
                    "table_rows": 30,
                    "items": 0,
                    "missing": 28,
                }
            ],
            "untracked": [],
            "errors": [],
        }
        markdown = render_markdown(report)
        assert "Codes" in markdown

    def test_untracked_pages_are_listed(self):
        report = {
            "pages": [],
            "untracked": [{"page": "Alchemist", "table_rows": 5}],
            "errors": [],
        }
        markdown = render_markdown(report)
        assert "Alchemist" in markdown
        assert "not tracked" in markdown

    def test_errors_are_listed(self):
        report = {
            "pages": [],
            "untracked": [],
            "errors": ["Pans: timed out"],
        }
        markdown = render_markdown(report)
        assert "timed out" in markdown

    def test_a_page_is_not_listed_twice(self):
        report = {
            "pages": [
                {
                    "page": "Codes",
                    "status": "no parser",
                    "table_rows": 30,
                    "items": 0,
                    "missing": 28,
                }
            ],
            "untracked": [],
            "errors": [],
        }
        markdown = render_markdown(report)
        assert markdown.count("| Codes |") == 1

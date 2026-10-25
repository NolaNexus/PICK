"""Scraper package init."""

# This file ensures scrapers are a Python package and makes the parser registry importable

from scrapers.registry import PARSERS, TRACKED_PAGES

__all__ = ["PARSERS", "TRACKED_PAGES"]

# Scraper and Parsers

Covers `scrapers/`, `scripts/scraper.py` and `app/services/scraper.py`.

## Guard on `pages_ok`, not `pages_scraped`

`pages_scraped` is not "pages fetched". It counts the titles that did not raise, and that
includes pages with no parser, which are never fetched. When every fetch fails,
`pages_scraped` is the number of no-parser pages (currently 3), not 0, so a guard on it
never fires.

`pages_ok` in `app/services/scraper.py` means "the run actually reached a page".
`scripts/scraper.py` guards on `pages_ok == 0`. Do not swap them.

## Tracked pages and parsers

- `TRACKED_PAGES` and `PARSERS` in `scrapers/registry.py` are separate.
- A page can be tracked with `PARSERS[page] = None` (currently `Codes`, `Changelog`,
  `Guides`). It is counted but never fetched.
- When adding a page, add its parser too.
- Parsers return `ParsedItem` (`scrapers/types.py`). It requires `id`, `type`, `name`,
  `slug`, `data` and `image_url`. `description` is `NotRequired` because some parsers put
  it inside `data`.
- A parser that builds a different shape gets its own TypedDict. Do not loosen
  `ParsedItem`.

## Re-parsing

A page is re-parsed only when its wikitext or `PARSER_VERSION` (`scrapers/registry.py`)
changes. Bump `PARSER_VERSION` when a parser, or the shared renderer
`scrapers/wikitext.py`, changes shape. Adding a parser also means bumping it. Otherwise
stored data keeps the old shape.

## Where it runs

The wiki is reachable only from the local machine. The scrape runs from a systemd timer
(`deploy/systemd/`; install steps in `SETUP.md`). Do not add a scrape workflow to CI.

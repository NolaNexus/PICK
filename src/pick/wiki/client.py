"""Thin mwclient wrapper enforcing etiquette and resumability."""

import mwclient

from pick.config import Settings


def site_from_settings(s: Settings | None = None) -> mwclient.Site:
    s = s or Settings()
    return mwclient.Site(
        "prospecting.miraheze.org",
        path="/w/",
        clients_user_agent=s.wiki_user_agent,
    )


def fetch_revision_content(site: mwclient.Site, page_title: str) -> dict | None:
    # Minimal wrapper: fetch page content by title via mwclient.
    # Real implementation uses site.pages and prop=revisions batches.
    try:
        page = site.pages[page_title]
        return {"title": page_title, "revisions": list(page.revisions())}
    except Exception:
        return None

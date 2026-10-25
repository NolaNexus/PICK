# Plan: Configure Reddit Devvit Script App Credentials

## Goal
Create a Devvit "Script App" to obtain OAuth2 client credentials, then configure them in the project so `scripts.news_scraper` can fetch Reddit posts via the official authenticated API.

## Current State (Already Done)
- ✅ `app/services/news_scraper.py` implements OAuth2 client credentials flow
- ✅ `app/config.py` has `reddit_client_id` / `reddit_client_secret` fields
- ✅ `scripts/news_scraper.py` fixed for DB session initialization
- ✅ Tests pass (163 unit + 6 integration)

## Required Actions

### T1 — Accept Developer Terms & Create Script App
1. Go to https://developers.reddit.com/
2. Accept the Developer Terms (checkbox → Continue)
3. Click **"Create App"** → Choose **"Script App"**
4. Fill in:
   - **Name**: `PICK News Scraper`
   - **Description**: `News aggregator for r/Prospecting`
   - **Redirect URI**: `http://localhost:8080` (required but unused for client credentials)
5. Click **Create**

### T2 — Extract Credentials
After creation, the app page shows:
- **Client ID** (public, under app name)
- **Client Secret** (click "Edit" → reveal)

### T3 — Configure Environment
Add to `.env`:
```bash
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
```

### T4 — Verify
```bash
.venv/bin/python -m scripts.news_scraper
```
Expected: `Fetched N Reddit posts` (N > 0 if new posts exist)

## Validation
- [ ] Credentials added to `.env`
- [ ] `scripts.news_scraper` runs without "not configured" warning
- [ ] Posts inserted into `news_articles` table (check via meta endpoint)

## Risks / Notes
- **Rate limits**: OAuth2 authenticated requests get higher limits (60/min → 600/min)
- **Redirect URI**: Must match exactly in Devvit app settings; `http://localhost:8080` is standard for script apps
- **User Agent**: Already set to `PICK/1.0` in config — complies with Reddit's requirement
- **Scope**: Client credentials grant only works for read-only public data (fits this use case)

## Out of Scope
- Devvit app review/publication (not needed for script apps)
- Refresh token flow (client credentials doesn't use it)
- Webhook/push notifications (not needed for polling scraper)
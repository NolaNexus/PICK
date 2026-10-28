---
description: Refresh the published snapshot from the wiki and publish it
---

Runs the whole refresh cycle: start the database, migrate, scrape the wiki, seed
formulas, export the snapshot, and commit and push it when the data changed.

```bash
cd /home/nola/Desktop/PICK
bash scripts/refresh_site.sh
```

Add `--full` for a complete rebuild of every tracked page, or `--dry-run` to
exercise the cycle without writing or publishing anything.

The script is **fail-closed** on purpose. It stops, without committing, when:

- the scrape reached no page (the wiki answered nothing), or
- the export would drop the item count by more than 20%, or empty it.

Two things to know before you run it:

- It ends in `git push origin HEAD:master`, which redeploys the site through
  GitHub Pages. Use `--dry-run` first if you are only checking the pipeline.
- The scrape only works from a machine that can reach the wiki. On a GitHub
  runner every request is refused.

After it runs, `git status` should be clean and the site redeploys itself. If
the data did not change, the script says "Snapshot unchanged" and stops without
committing — that is the normal quiet-day outcome.

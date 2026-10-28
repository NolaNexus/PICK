# Git, Issues and Docs

## Commits

- Use Conventional Commit prefixes, as in the history: `feat:`, `fix:`, `chore:`,
  `docs:`, `ci:`, `test:`, `refactor:`.
- Write the body as the *why*. Several commits record the failure mode they prevent.
- `master` is the deploy branch. Pushing to it triggers the CI workflow and the GitHub
  Pages deploy.

## Issues

- Use one of the forms in `.github/ISSUE_TEMPLATE/`: `bug_report.yml`,
  `feature_request.yml` or `task.yml`. Each sets its own label. `config.yml` sets
  `blank_issues_enabled: false`, so blank issues are not possible.
- **Issue types do not work on this repository.** `NolaNexus/PICK` is user-owned, and
  GitHub's issue types are an organisation feature. `GET /repos/NolaNexus/PICK/issue-types`
  lists the three defaults, but assigning one is a silent no-op: the REST and GraphQL calls
  return `200` and leave `issueType` null, with no timeline event.
- Use labels instead: `bug`, `enhancement`, `documentation`.

## Docs and slash commands

- `README.md` is the overview. `SETUP.md` is the operational guide, including the systemd
  install and deploy-key setup. `ROADMAP.md` records what shipped and what is open.
- `frontend/README.md` is the stock Vite template README, not documentation for this
  project. Ignore it.
- `app/logging_config.py` is dead code: nothing imports it. Do not wire it up as part of
  an unrelated change, and do not assume the scraper's logging is configured anywhere —
  it uses the root logger's defaults.
- `.kilo/plans/` holds dated working plans. They are committed history, not current
  documentation. They describe intent at a point in time, and several describe code that
  was later removed or rewritten. Some carry a `**Status:**` line. Re-verify a plan's
  claims against the code before acting on them.
- `.kilo/command/` holds the repo's slash commands: `/check`, `/check-offline`, `/refresh`,
  `/generate-types`, `/verify-guards`. They carry the exact working invocations and the
  traps that go with them.

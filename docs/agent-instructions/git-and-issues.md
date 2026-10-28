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
  install and deploy-key setup.
- **Plans are scratch, not documentation.** A plan file describes intent at one moment
  and rots as soon as the code moves. `.kilo/plans/` is git-ignored for that reason:
  plans are written when work starts and deleted when it lands. Do not read an old plan
  as a description of the current tree, and do not treat its checkboxes as a work
  queue. If you find one, re-verify every claim against the code before acting, or
  throw it away.
- `.kilo/command/` holds the repo's slash commands: `/check`, `/check-offline`, `/refresh`,
  `/generate-types`, `/verify-guards`. They carry the exact working invocations and the
  traps that go with them.

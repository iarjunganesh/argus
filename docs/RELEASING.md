# Releases and dependency refreshes

Release automation is prepared for `v0.1.0`. No release has been published by this change.
Only an explicitly approved tag push publishes a release. Production deployment is Phase 5 work.

## Before the first tag

1. Merge the release automation PR after its full CI gate passes.
2. Create the repository secret `DEPS_BOT_TOKEN`. Use a fine-grained PAT restricted to this
   repository, with Contents, Pull requests and Workflows read/write permissions. Workflows
   permission is needed because the refresh updates action pins. Never put the token in a file.
   Regenerate it before it expires and update the secret; an expired token fails only the
   refresh, which can then be retried (see below).
3. Create the `deps-broken` label. These are repository setup actions requiring the maintainer's
   approval. Branch protection also needs separate approval: require the six CI jobs and a PR,
   and prohibit force pushes to `main`.
4. Open a release-prep pull request: rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`
   (the date you tag), add a new empty `## [Unreleased]` above it, set `version` in
   `pyproject.toml` to `X.Y.Z` and run `uv lock`. Merge it before tagging, so the tagged commit
   carries its own dated notes.
5. Run all commands in `AGENTS.md`, plus
   `uv run python scripts/ci/check_versions.py --check` and
   `uv run python scripts/ci/release_notes.py v0.1.0 --output .tmp/release-notes.md`.
6. Obtain the maintainer's explicit approval to create and push the release tag.

## What the tag runs

`release.yml` reuses every job in `ci.yml` on the tagged commit. It checks main-branch ancestry,
the package version and exactly one nonempty changelog section before publishing that section
as the GitHub Release notes. Tags use `vX.Y.Z`; prereleases use `vX.Y.Z-alpha.N`, `-beta.N` or
`-rc.N` (PEP 440 package versions use `aN`, `bN` or `rcN`).

After publication, `refresh-deps` checks out `main`, inventories upstream versions, upgrades
the lock, raises direct dependency minimums, refreshes action SHAs, and runs the Python gates,
the dependency audit, Markdown lint and secret scan. Its review report records major upgrades,
unavailable upstream data and failed checks. The PR is titled `deps: refresh after vX.Y.Z`;
failed checks label it `deps-broken` and fail the job. The PAT makes the PR trigger normal CI.
The report changes even when dependencies are current, so a no-change refresh still has a PR.

The latest report is [DEPENDENCY-REFRESH.md](DEPENDENCY-REFRESH.md). A release remains incomplete
until its refresh PR exists and its results have been reviewed. No automatic merge occurs.
If the token or setup is missing, repair it and manually dispatch **Release**, supplying an
existing published tag. Manual dispatch retries the refresh without republishing the release.

## Version inventory

- `--check` is offline. It checks interpreter settings, package/lock consistency and consistent
  SHA-pinned actions. CI's locked uv commands also reject stale dependency metadata.
- `--check-upstream` reads PyPI and GitHub, reports every locked registry package and action,
  and flags major bumps. Network failures return a failure, not a clean bill of health.
- `--write` refreshes action pins and raises direct minimums to the resolved lock versions.
  Run `uv lock --upgrade` first, then `uv lock` after raising minimums. Review all changes.
- A newer stable CPython minor is eligible only when **every locked package version** has
  non-yanked compatible wheels for Linux x86_64 and Windows amd64 and accepts that Python
  version. The release workflow prepares a separate interpreter PR and verifies Linux
  binary-only installation. Its normal PR CI must pass before merge. This conservative test
  can defer an upgrade because of a platform-specific optional package; review that explicitly.

Web, container images and Agent Framework are absent today. The inventory fails closed if a
root Dockerfile or web manifest appears without extending it. Add npm, image currency, exact
Agent Framework upgrades and the offline workflow contract test in Phase 5, with those features.
The build backend is reported separately because it is outside the lock; the refresh raises
its minimum to the latest release and retains an upper bound at the next minor.

Dependabot schedules weekly checks with version PRs disabled (`open-pull-requests-limit: 0`),
leaving security PRs enabled for uv and GitHub Actions. Enable Dependabot security updates in
repository settings if they are not already enabled. Add grouped npm security updates when
`web/package.json` exists.

GitHub behavior follows the upstream documentation for
[reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[PR tokens](https://github.com/peter-evans/create-pull-request#token),
[workflow-writing permissions](https://docs.github.com/en/rest/git/refs#create-a-reference), and
[Dependabot configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).

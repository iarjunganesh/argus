# Releases and dependency refreshes

Release automation is merged. The first release, `v0.1.0`, was published on 2026-11-16. Only
an explicitly approved tag push publishes a release. Zenodo archives every published release and
gives it a DOI, with the metadata in `CITATION.cff`; the concept DOI 10.5281/zenodo.24292413 always resolves to
the latest version. Once Azure is set up for GitHub ([DEPLOYMENT.md](DEPLOYMENT.md)), the same
tag also deploys the API.

## Before a tag

1. Check the one-time setup, which exists since `v0.1.0`. These are repository settings, so this
   page cannot tell whether they are still in place:
   - the repository secret `DEPS_BOT_TOKEN`: a fine-grained PAT restricted to this repository,
     with Contents, Pull requests and Workflows read/write permissions. Workflows permission is
     needed because the refresh updates action pins. Never put the token in a file. Regenerate it
     before it expires and update the secret; an expired token fails only the refresh, which can
     then be retried (see below);
   - the `deps-broken` label;
   - the repository's Zenodo archiving, switched on in the maintainer's Zenodo account.

   Changing them needs the maintainer's approval. Two repository rulesets are active (read on
   2026-11-22): `main` requires a pull request merged with a merge commit, resolved review
   threads and six CI checks (Lint and format, Type check, Tests and coverage, Dependency audit,
   Secret scan, Documentation), and blocks force pushes and deletion; `release tags` blocks
   moving or deleting a `v*` tag. Classic branch protection is not set. Requiring the other CI
   jobs too (Web UI, Container image, Infrastructure template, CodeQL, No AI attribution) needs
   the maintainer's approval.
2. Open a release-prep pull request: rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`
   (the date you tag), add a new empty `## [Unreleased]` above it, set `version` in
   `pyproject.toml` to `X.Y.Z` and run `uv lock`. Merge it before tagging, so the tagged commit
   carries its own dated notes.
3. Run all commands in `AGENTS.md`, plus
   `uv run python scripts/ci/check_versions.py --check` and
   `uv run python scripts/ci/release_notes.py vX.Y.Z` (it writes `.tmp/release-notes.md`).
4. Obtain the maintainer's explicit approval to create and push the release tag.

## What the tag runs

`release.yml` reuses every job in `ci.yml` on the tagged commit. It checks main-branch ancestry,
the package version and exactly one nonempty changelog section before publishing that section
as the GitHub Release notes. Tags use `vX.Y.Z`; prereleases use `vX.Y.Z-alpha.N`, `-beta.N` or
`-rc.N` (PEP 440 package versions use `aN`, `bN` or `rcN`).

After publication, `deploy` runs [`deploy.yml`](../.github/workflows/deploy.yml) when the
repository variable `AZURE_RESOURCE_GROUP` is set: it pushes the tagged image and deploys it (see
[DEPLOYMENT.md](DEPLOYMENT.md)). Without the variable the job is skipped.

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

- **Container base images.** `--check` requires every `FROM` in the root `Dockerfile` to be pinned
  by version tag and `sha256` digest, one pin per image, to an image the inventory knows (Python
  and uv), with the Python image on the `.python-version` minor. `--check-upstream` reads the
  newest release (the newest CPython patch of that minor; uv's latest GitHub release) and asks the
  registry (Docker Hub, GitHub Container Registry) for its digest; it also reports an image
  `rebuilt` under the same tag, usually for base-OS security fixes. `--write` moves the pins, and
  the interpreter PR moves the Python image to the new minor. A tag the registry has not published
  yet stays as it is and is reported.
- **Agent Framework** is pinned exactly, and `--write` keeps it exact at its locked version, so the
  refresh does not move it. Move it by hand in the refresh pull request: the new version in
  `pyproject.toml` and the README badge, then `uv lock --upgrade-package agent-framework-core`;
  the orchestrator and API contract tests then run the workflow on it. After `v0.1.0` it moved
  from 1.19.0 to 1.26.0 this way.

The build backend is reported separately because it is outside the lock; the refresh raises
its minimum to the latest release and retains an upper bound at the next minor.

Dependabot schedules weekly checks with version PRs disabled (`open-pull-requests-limit: 0`),
leaving security PRs enabled for uv, GitHub Actions and the web UI's npm packages. Enable
Dependabot security updates in repository settings if they are not already enabled.

GitHub behavior follows the upstream documentation for
[reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[PR tokens](https://github.com/peter-evans/create-pull-request#token),
[workflow-writing permissions](https://docs.github.com/en/rest/git/refs#create-a-reference), and
[Dependabot configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).

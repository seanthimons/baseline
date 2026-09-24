# baseline

Public source of truth for CI across seanthimons repositories.

baseline provides two things:

- **Reusable workflows** (`on: workflow_call`) in `.github/workflows/`. Each repo keeps a thin caller stub (about 10 to 20 lines) that owns triggers, path filters, cron stagger, and concurrency. The callee owns the jobs, timeouts, action pins, and setup steps.
- **Copied templates** in `templates/` for things GitHub cannot inherit: caller stubs, `dependabot.yml`, `.gitleaks.toml`, `air.toml`, `codecov.yml`, and `.gitattributes`.

The reasons for this layout and the findings behind it are in [`docs/audit-2026-09-24.md`](docs/audit-2026-09-24.md). The rollout order is in [`docs/migration.md`](docs/migration.md).

This repo must stay public. Public caller repos cannot call reusable workflows from a private repo.

## Layout

```
.github/
  workflows/          reusable workflows (workflow_call), plus self-lint.yaml for this repo
  workflows/README.md one paragraph per reusable workflow: inputs, secrets, permissions
  actions/r-setup/    composite: pandoc, R, optional Quarto/Air, deps or renv, profile isolation
  actions/pkg-metadata/ composite: package, version, short SHA from DESCRIPTION
  dependabot.yml      bumps this repo's own action pins
templates/
  workflows/          caller stubs to copy into <repo>/.github/workflows/
  config/             dependabot.yml, .gitleaks.toml, air.toml, codecov.yml, .gitattributes
examples/             standalone workflows to copy and edit (shinylive Pages deploy)
docs/                 audit report, raw audit data, migration plan
```

The composite actions are for project-specific workflows in caller repos (for example ComptoxR's db builds). The reusable workflows in this repo inline their own setup steps and do not depend on the composites.

## How to adopt

1. Pick the workflows for your project type from the table below.
2. Copy each caller stub from `templates/workflows/` into `<repo>/.github/workflows/`. Keep the `.yaml` extension.
3. Pin the `uses:` ref to a full commit SHA of a baseline release tag, with the tag as a trailing comment:
   ```yaml
   uses: seanthimons/baseline/.github/workflows/r-cmd-check.yaml@<40-char-sha> # v1.0.0
   ```
   Get the SHA with `git ls-remote https://github.com/seanthimons/baseline refs/tags/v1.0.0`.
4. Edit the caller's triggers, branch filters, and inputs. Pass secrets explicitly by name. Do not use `secrets: inherit`.
5. Grant permissions on the calling job only. A callee cannot escalate beyond what the caller grants. Keep the caller's top-level `permissions: contents: read`.
6. Copy the config files you need from `templates/config/` to the repo root (`dependabot.yml` goes to `.github/dependabot.yml`).
7. Delete the repo's old local copy of each workflow you replaced.
8. Update branch protection. Required status check names change to `caller-job / callee-job (matrix)`, for example `R CMD check / ubuntu-latest (release)`. Change them in the same PR, or PRs block on a check that never reports.

## Versioning

- Releases are tagged `v1.x.y`. Patch and minor releases never break callers.
- Removing or renaming an input, changing a default in a breaking way, or adding a required secret requires a new major tag (`v2.0.0`).
- Callers pin a full SHA with a `# v1.x.y` comment, never a branch or bare tag.
- `templates/config/dependabot.yml` covers the `github-actions` ecosystem, which includes `uses: seanthimons/baseline/...@<sha>` refs. Dependabot opens grouped `ci:` PRs that bump both third-party pins and baseline pins.
- Every third-party action in this repo is pinned by full SHA with a version comment. This repo's own `.github/dependabot.yml` keeps those pins current.

## Which workflows apply to which project

| Workflow | R package | R app with renv | Quarto site | Shinylive app | Node / Rust |
|---|---|---|---|---|---|
| `commit-lint.yaml` | yes | yes | yes | yes | yes |
| `gitleaks.yaml` | yes | yes | yes | yes | yes |
| `lint-workflows.yaml` | yes | yes | yes | yes | yes |
| `r-cmd-check.yaml` | yes | | | | |
| `test-coverage.yaml` | optional | | | | |
| `build-package.yaml` | yes | | | | |
| `pkgdown.yaml` | if it has `_pkgdown.yml` | | | | |
| `release-r-package.yaml` | if it uses autonewsmd | | | | |
| `rolling-prerelease.yaml` | optional | | | | |
| `r-renv-tests.yaml` | | yes | | | |
| `quarto-pages.yaml` | | | yes | | |
| `examples/shinylive-pages.yaml` | | | | copy and edit | |

Node and Rust builds (maestro) stay project-specific. baseline ships no Node or Rust workflows or composites; those repos take only the hygiene callers.

Config files:

| File | Applies to |
|---|---|
| `.github/dependabot.yml` | every repo (add `npm` and `cargo` entries locally where needed) |
| `.gitattributes` | every repo |
| `.gitleaks.toml` | every repo; each repo keeps its own allowlist entries |
| `air.toml` | R repos |
| `codecov.yml` | repos that enable Codecov in `test-coverage.yaml` |

## Required secrets

| Secret | Used by | Required | Scope |
|---|---|---|---|
| `RELEASE_PAT` | `release-r-package.yaml` | yes | Fine-grained PAT limited to the one repository, with Repository permissions > Contents: Read and write. The token owner must be allowed to push to the protected default branch (bypass or admin on the branch rule). `GITHUB_TOKEN` cannot push the release commit and tag to a protected `main`. |
| `GITLEAKS_LICENSE` | `gitleaks.yaml` | no | Only needed if the repo moves to an organization account. Personal-account repos do not need it. |

No other workflow takes secrets. API keys such as `CTX_API_KEY` stay in project-specific live-API workflows and must never be passed to baseline callees.

## GitHub Pages setting

`pkgdown.yaml` and `quarto-pages.yaml` deploy with the Pages artifact actions (`upload-pages-artifact` plus `deploy-pages`), not a `gh-pages` branch push. Before the first deploy, set each repo's **Settings > Pages > Build and deployment > Source** to **GitHub Actions**. The caller job needs `pages: write` and `id-token: write`. After a successful deploy, delete the old `gh-pages` branch.

Deploy jobs are skipped on `pull_request` events. The build still runs as a PR check.

## Rules every callee follows

- Top-level `permissions: contents: read`. Write scopes are granted per job only.
- `timeout-minutes` on every job.
- No concurrency in callees (callers own it), except release (group `release`, no cancel) and Pages deploys (group `pages`, no cancel).
- No `${{ inputs.* }}` or `${{ github.event.* }}` in `run:` scripts. Values pass through `env:`.
- R jobs set `R_PROFILE_USER=/dev/null` and `RENV_CONFIG_AUTOLOADER_ENABLED=false`, so a repo's `.Rprofile` cannot activate renv over the installed library.
- `lint-workflows.yaml` (actionlint and zizmor) enforces these rules. `self-lint.yaml` runs it on this repo.

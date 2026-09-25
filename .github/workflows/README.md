# Reusable workflows

Every workflow here except `self-lint.yaml` is a reusable workflow (`on: workflow_call`). Callers copy a stub from `templates/workflows/`, pin this repo by full SHA with a `# v1.x.y` comment, and own triggers, path filters, and concurrency. Inputs listed below are a summary; see the file header and `on.workflow_call.inputs` block of each file for the authoritative input list and defaults.

All callees declare top-level `permissions: contents: read` and set `timeout-minutes` on every job. A callee cannot hold more permissions than the calling job grants, so the "Caller permissions" below go on the caller's job, not its top level. Secrets are passed explicitly by name; never use `secrets: inherit`.

R jobs set `R_PROFILE_USER=/dev/null` and `RENV_CONFIG_AUTOLOADER_ENABLED=false` at job level. This keeps a repo's `.Rprofile` (for example one that runs `source("renv/activate.R")`) from replacing the library that setup installed. Callee concurrency is limited to the jobs that need serialization: Pages deploys (group `pages`), releases (group `release`), and rolling prereleases (one group per tag), all with `cancel-in-progress: false`.

## `r-cmd-check.yaml`

Runs `R CMD check` through `r-lib/actions/check-r-package` across an OS and R matrix, with `fail-fast: false`, and uploads testthat snapshots. Inputs: `matrix` (JSON array of `{os, r}` objects; default is release on ubuntu, windows, and macos; add `{"os":"ubuntu-latest","r":"oldrel-1"}` or `devel` in the caller), `quarto` (bool), `setup-air` (bool, for packages that shell out to air), `extra-packages` (default `any::rcmdcheck`), `error-on` (default `warning`), and `testthat-parallel-windows` (bool, default false, which keeps the Windows `TESTTHAT_PARALLEL=FALSE` workaround from ComptoxR #253). Secrets: none. Caller permissions: `contents: read`. Do not add `paths-ignore` entries for `DESCRIPTION`, `NAMESPACE`, or `.github/**` in the caller. See file header for the authoritative input list.

## `test-coverage.yaml`

Runs `covr::package_coverage()` once on ubuntu-latest with R release, writes `cobertura.xml` as an artifact, and writes a coverage summary to the step summary. There is no OS matrix; OS coverage belongs to r-cmd-check. Inputs: `codecov` (bool, default false; uploads through Codecov OIDC with no token) and `quarto` (bool). Thresholds and PR comments live in the caller's `codecov.yml`, not in the workflow. Secrets: none. Caller permissions: `contents: read` and `id-token: write`. The job declares `id-token: write`, so callers must grant it even when `codecov` is false. See file header for the authoritative input list.

## `build-package.yaml`

Builds the R source tarball with `R CMD build` and uploads it as a workflow artifact. Package name and version come from DESCRIPTION. Inputs: `quarto` (bool, for Quarto vignettes) and `pre-build-script` (optional repo-relative R script run before the build; ComptoxR's stable stripped-exports profile goes here). Output: `artifact-name`. Secrets: none. Caller permissions: `contents: read`. See file header for the authoritative input list.

## `pkgdown.yaml`

Builds a pkgdown site and deploys it with the Pages artifact actions. The build job runs on every event with `contents: read`. The deploy job is skipped on `pull_request`, holds `pages: write` and `id-token: write`, and uses concurrency group `pages` without cancel. Inputs: `quarto` (bool) and `pre-build-script` (optional R script run before the build, for example ComptoxR's `check_public_api`). Secrets: none. Caller permissions: `contents: read`, `pages: write`, `id-token: write`. The repo's Pages source must be set to "GitHub Actions". See file header for the authoritative input list.

## `release-r-package.yaml`

Stable release for R packages. It bumps the version, commits and tags, builds the source tarball once, runs R CMD check on that exact tarball, generates `NEWS.md`, pushes `main` and the tag in one `git push --atomic`, and publishes a GitHub release with the tarball. Every input value reaches R through `env:`. The package name comes from DESCRIPTION. Inputs: `version-type` (`major`, `minor`, `patch`, or `dev`; default `patch`), `notes-mode` (`autonewsmd` or `generate-notes`), `news-postprocess-script` (optional R script run after autonewsmd and default pkgdown heading normalization), `pre-release-check-script` (optional R script run after the bump, for example ComptoxR's `check_public_api`), `quarto` (bool; always installed for autonewsmd), and `dry-run` (bool; runs everything except push and publish, on any ref). Secrets: `RELEASE_PAT` (required; fine-grained, Contents read and write on the one repo, owned by an account allowed to push to protected `main`). Caller permissions: `contents: write` on the calling job; only the publish job uses it, and dry runs stay read-only. Concurrency group `release`, no cancel; dry runs get their own group. Use a `choice` input in the caller's `workflow_dispatch` for `version-type`. To release a patch on every merge, uncomment the `push` trigger in `templates/workflows/release-r-package.yaml` and protect `main` with a rule that requires a pull request before merging, so only PR merges push to it (bypass-list accounts that push directly also release); the caller's `|| 'patch'` and `event_name` fallbacks are required because push events send empty inputs, and an empty `version-type` fails the callee's validation. See file header for the authoritative input list.

## `rolling-prerelease.yaml`

Builds an R package from a ref and publishes it to a moving prerelease tag such as `package-latest` or `integration-latest`. The tag moves only after every asset has uploaded, and stale assets are pruned. Inputs: `ref` (default `main`), `tag` (default `package-latest`), `build-binaries` (bool; adds Windows and macOS binaries), and `require-dev-version` (bool; fails unless the version has four components, the `.9000` guard). Secrets: none (uses `GITHUB_TOKEN`). Caller permissions: `contents: write` on the calling job; only the publish job uses it. Concurrency is one group per tag, no cancel. See file header for the authoritative input list.

## `commit-lint.yaml`

Checks every non-merge PR commit subject and the PR title (the squash-merge subject) against Conventional Commits restricted to the autonewsmd types. It also checks that the head branch name is Conventional Branch `type/description`, where type is `feature`, `feat`, `bugfix`, `fix`, `hotfix`, `release`, `chore`, `ci`, `docs`, `refactor`, or `test`, with no agent or model tokens (codex, claude, ai/, copilot, gpt, and similar). Values are read through `env:`, and no Node is needed. Bot-authored commits are skipped; this is a lint, not a security control. Inputs: `types` (default `feat|fix|refactor|perf|build|test|ci|docs|style|chore`) and `scope-regex` (default `[A-Za-z0-9_]+`). Secrets: none. Caller permissions: `contents: read`. Trigger it from `pull_request` with no branch filter, so PRs to `integration` are covered too. Never write the literal `[skip ci]` (or `[ci skip]`, `[no ci]`, `[skip actions]`, `[actions skip]`) anywhere in a commit message, body included: when the PR's head commit carries it, GitHub skips every `push` and `pull_request` workflow, and no checks appear at all. Only the release workflow's own bot commit uses it. See file header for the authoritative input list.

## `gitleaks.yaml`

Scans full git history (`fetch-depth: 0`) with gitleaks-action and reads the caller's repo-root `.gitleaks.toml`. Bot commits are scanned too; there is no actor skip. Inputs: none. Secrets: `GITLEAKS_LICENSE` (optional; only for organization-owned repos). Caller permissions: `contents: read`. Keep the weekly `schedule` in the caller and change the cron minute per repo to stagger runs. See file header for the authoritative input list.

## `quarto-pages.yaml`

Renders a Quarto project and deploys it to GitHub Pages. The build runs on pull requests as a check, and deploy is skipped on `pull_request`. The deploy job holds `pages: write` and `id-token: write` and uses concurrency group `pages` without cancel. Inputs: `quarto-version` (required; pin a specific release), `output-dir` (default `_site`), and `needs-r` (bool; installs R and restores `renv.lock` if present). With `needs-r: false`, every `.qmd` with R chunks needs committed `_freeze/` output, and the build fails fast with a clear message when it is missing. Secrets: none. Caller permissions: `contents: read`, `pages: write`, `id-token: write`. See file header for the authoritative input list.

## `r-renv-tests.yaml`

Runs testthat for R projects that are not packages, against the environment in `renv.lock`. R is installed with `r-version: renv` and packages with `setup-renv`. Inputs: `os` (default `ubuntu-latest`), `test-dir` (default `tests/testthat`), `test-filter` (optional; concert's locked lane passes `review|modules-render`), `air-format-check` (bool; runs `air format --check .` once), `shiny-smoke` (bool; starts the app in the background, waits for `Listening on`, then stops it), and `shiny-run-command` (R expression that starts the app; default `shiny::runApp(port=3838, launch.browser=FALSE)`). Secrets: none. Caller permissions: `contents: read`. Timeout is 45 minutes, which guards against hung renv restores on Windows. See file header for the authoritative input list.

## `lint-workflows.yaml`

Runs actionlint and zizmor over the caller's `.github/workflows/`. zizmor flags `${{ inputs.* }}` or `${{ github.event.* }}` interpolated into `run:` scripts, missing permissions, and unpinned actions. Inputs: none. Secrets: none. Caller permissions: `contents: read`. Trigger it on changes to `.github/**`. See file header for the authoritative input list.

## `self-lint.yaml`

Not reusable. Runs `lint-workflows.yaml` against this repository on pushes to `main` and on pull requests that touch `.github/**`.

## Not here

- The shinylive Pages deploy is a copied example in `examples/shinylive-pages.yaml`, because it already wraps `posit-dev/r-shinylive`'s reusable workflow.
- Project-specific workflows (ComptoxR db builds, schema-check, cassette recording, epa-sswqs data release) stay in their own repos. They may use the composite actions in `.github/actions/r-setup` and `.github/actions/pkg-metadata`, pinned by SHA.

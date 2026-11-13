# Migration to baseline

Phased plan for moving each repository onto the baseline reusable workflows. It is derived from the 2026-09-24 audit ([`audit-2026-09-24.md`](audit-2026-09-24.md)). Phases run in order. Within a phase, repos are independent and can migrate in any order. Repos are named as they are today: the audit's `QRMA_VFAR` is now `singlehit`, and `amos-harmonizer` is now `envharmonizer-build`.

## Fix in place before migrating

These were live hazards. #3 is resolved; fix #1 and #2 in their own repos now, in small PRs, without waiting for baseline.

1. **ComptoxR `record-cassettes.yml` script injection (line 62).** Move `workers`, `batch_size`, and `mode` from `${{ inputs.* }}` interpolation into `env:`. Read them with `Sys.getenv()` and validate `workers` and `batch_size` as integers before use. Add `retention-days` to the fixtures artifact.
2. **ComptoxR `pipeline-tests.yml` and `rebase-WIP-branches.yml`.** Delete the `rerecord_cassettes` input and its fixture-deleting path, and delete the dead issue step that uses `dacbd/create-issue-action@main`. Delete `rebase-WIP-branches.yml` entirely.
3. **singlehit `release.yaml` (line 98).** It sourced `dev/normalize_news.R`, which was not committed. Resolved: singlehit's `release.yaml` now calls `release-r-package`.

## Conventions for every migration PR

- Branch: Conventional Branch name, for example `chore/adopt-baseline-ci`. No agent or model names.
- Commits: `ci:` type (a recognized autonewsmd type), for example `ci: adopt baseline gitleaks and commit-lint callers`.
- Workflow files use the `.yaml` extension and LF line endings.
- Callers pin baseline by full SHA with a `# vX.Y.Z` comment. Pass secrets by name, never `secrets: inherit`.

## Required status checks change name

Reusable-workflow jobs report as `caller-job / callee-job (matrix)`, for example `R CMD check / ubuntu-latest (release)` instead of `ubuntu-latest (release)`. In any repo with branch protection, update the required checks in Settings > Branches (or the ruleset) in the same PR that swaps the workflow. Otherwise PRs block on a check that never reports. After merging, confirm the new names appear under the protection rule and remove the old ones.

## Phase 0: create baseline

- [x] Create the public repo `seanthimons/baseline`.
- [x] Add `.github/workflows/*.yaml` (workflow_call), `.github/actions/r-setup` and `.github/actions/pkg-metadata`, `templates/` (caller stubs and shared config), `examples/`, and `.github/workflows/README.md`.
- [x] Add baseline's own `.github/dependabot.yml` and `self-lint.yaml` (actionlint and zizmor on itself). Confirm self-lint passes.
- [x] Tag `v1.0.0`. Record its full SHA for callers.
- [x] Confirm Settings > Actions > General allows other repos to use this repo's workflows (automatic for a public repo).

## Phase 1: hygiene everywhere (low risk)

Every repo gets the gitleaks, commit-lint, and lint-workflows callers, plus `.github/dependabot.yml`, `.gitattributes`, and `.gitleaks.toml`. Delete the local gitleaks and commit-lint copies. The gitleaks stub scans pushes to `main` and `master` and every pull request, so repos on either branch need no per-repo edits (`on:` filters cannot read `github.event.repository.default_branch`); add other long-lived branches to its `push.branches`. Keep a weekly gitleaks cron in each caller, with a different minute per repo.

Lint findings (#20): small repos (serapeum, envharmonizer-build, envharmonizer) fix them inside the adoption PR. boosterpak and chorus ignore the `release.yaml` findings in a repo-local zizmor config until Phase 3 replaces that file; first verify that zizmor-action discovers the config. ComptoxR is hardened in its own PR first and adopts lint-workflows last.

- [ ] **ComptoxR**: replace `gitleaks.yaml` and `commit-lint.yaml`. Keep the existing `.gitleaks.toml` and `.gitleaksignore`, and re-base `.gitleaks.toml` on the template's `[extend] useDefault = true` shape. commit-lint now also covers PRs to `integration`. Add `integration` to the gitleaks caller's `push.branches`; the current workflow scans `[main, integration]`.
- [x] **singlehit**: replace `gitleaks.yaml` and `commit-lint.yaml`. Add `dependabot.yml` (currently missing).
- [x] **boosterpak**: replace `gitleaks.yaml` (v2.3.9) and `commit-lint.yaml`.
- [ ] **chorus**: replace `gitleaks.yaml` and `commit-lint.yaml`. Replace the empty `air.toml` with the shared copy.
- [x] **concert**: replace `gitleaks.yaml` and `commit-lint.yaml`. Replace the tab-indented `air.toml` with the shared copy.
- [x] **specmill**: replace `gitleaks.yml` and `commit-lint.yml`. Add `dependabot.yml` (currently missing).
- [ ] **envharmonizer-build**: add the gitleaks, commit-lint, and lint-workflows callers and all config files (it has none of them today).
- [ ] **sk_app** (skipped by the owner for now, #21): add the gitleaks and commit-lint callers and config files. `.gitattributes` fixes the CRLF workflow file.
- [ ] **epa-sswqs** (skipped by the owner for now, #21): add the gitleaks and commit-lint callers and config files. `.gitattributes` fixes the mixed CRLF/LF in `build-toxval.yml`.
- [ ] **serapeum**: replace `gitleaks.yml`. Add the commit-lint caller and config files. Add allowlist entries to `.gitleaks.toml` only for confirmed false positives (for example `config.yml` or test fixtures). Add `integration` to the gitleaks caller's `push.branches`; the current workflow scans `[main, integration]`.
- [x] **seanthimons.github.io**: replace `gitleaks.yml`. Drop the stale `integration` branch from triggers. Add the commit-lint caller and config files. Consider allowlisting `docs/` and `_freeze/`.
- [ ] **envharmonizer** (public; new since the audit): add the gitleaks, commit-lint, and lint-workflows callers and config files. It already calls `r-cmd-check` and `release-r-package` pinned at v1.3.0, so bump those pins in the same PR. Its local `sync-tables.yaml` is checked by lint-workflows.
- [ ] **scifindeR** (new since the audit; already on the baseline callers and config except gitleaks): replace its `gitleaks.yaml`, which does not call baseline, with the baseline caller.

## Phase 2: R check and coverage

- [ ] **specmill**: replace `check.yml` (dispatch only) with an r-cmd-check caller on push and pull_request, with `setup-air: true`. specmill gets automatic CI for the first time.
- [ ] **ComptoxR**: replace `r-cmd-check.yaml` with a caller (`setup-air: true`, `testthat-parallel-windows: false`). Remove `DESCRIPTION`, `NAMESPACE`, and `.github/**` from every `paths-ignore` block. Replace `test-coverage.yml`, `coverage-check.yml`, and `test-quick.yml` with a single test-coverage caller (`codecov: true`) plus the shared `codecov.yml`. Stop passing `ctx_api_key` to routine test, check, and coverage jobs.
- [ ] **singlehit**: the `r-cmd-check` and `test-coverage` callers are already in place. DESCRIPTION declares R >= 4.1.0, so consider adding an `oldrel-1` leg through the `matrix` input (not re-checked).
- [ ] **boosterpak**: replace `r-cmd-check.yaml` with a caller (`quarto: true`). Drop the redundant `.planning/**` paths-ignore.
- [ ] **chorus**: replace `r-cmd-check.yaml` with a caller. The callee's profile isolation fixes the renv activation from `.Rprofile`. Drop the `.planning/**` paths-ignore.
- [ ] **concert**: replace the main r-cmd-check job with a caller. Move the `locked-review` job to an r-renv-tests caller (`os: windows-latest`, `test-filter: review|modules-render`); it now reads the R version from `renv.lock`.
- [ ] **envharmonizer-build**: replace `R-CMD-check.yaml` with an r-cmd-check caller and add `workflow_dispatch`. The stale `feature/initial-harmonization-pipeline` trigger is already gone. The local workflow pins CRAN to a dated Posit snapshot through `RSPM`; check how the callee handles that before swapping.
- [ ] **serapeum**: add an r-renv-tests caller (`air-format-check: true`, `shiny-smoke: true`). serapeum currently has no test CI.
- [ ] In every repo above with branch protection, update required checks to the new names in the same PR.

## Phase 3: docs and publishing

- [ ] **pkgdown repos (singlehit, boosterpak, specmill, ComptoxR)**: switch to the pkgdown caller (`quarto: true` for boosterpak; `pre-build-script` for ComptoxR's `check_public_api`). In Settings > Pages, change the source from "Deploy from a branch (gh-pages)" to "GitHub Actions". After the first successful deploy, delete the old `gh-pages` branch. singlehit already has the pkgdown caller.
- [ ] **seanthimons.github.io**: decide whether Pages deploys from Actions or from the committed `docs/` folder. If Actions, switch `publish.yml` to a quarto-pages caller with a pinned `quarto-version`, set Pages source to "GitHub Actions", gitignore `docs/`, and stop committing renders. If `docs/` is kept, delete `publish.yml`.
- [ ] **sk_app**: replace `deploy-app.yaml` with `examples/shinylive-pages.yaml` (top-level `permissions: {}`, concurrency group `pages` without cancel, `posit-dev/r-shinylive` pinned by SHA).
- [ ] **Releases (ComptoxR, singlehit, boosterpak, chorus, concert, specmill)**: move to a release-r-package caller. singlehit already calls `release-r-package`.
  - [ ] Confirm a `RELEASE_PAT` secret exists in each repo: fine-grained, Contents read and write on that repo, owned by an account allowed to push to protected `main`. Pass it explicitly.
  - [ ] Dry-run through the PR path (`dry-run: true`) before the first real release.
  - [ ] ComptoxR: pass `pre-release-check-script` for `check_public_api`.
  - [ ] singlehit: pass `news-postprocess-script` only if `dev/normalize_news.R` was committed (singlehit already migrated; check whether its caller passes it).
  - [ ] specmill: choose `notes-mode: autonewsmd` to match the other repos, or keep `generate-notes`. Retire `dev/build_release.R` once the callee covers it.
- [ ] **Rolling prereleases**: replace ComptoxR `publish-rolling-package.yaml` and `publish-integration-package.yaml` with rolling-prerelease callers. singlehit already calls rolling-prerelease. ComptoxR integration: `ref: integration`, `tag: integration-latest`, `build-binaries: true`, `require-dev-version: true`.

## Phase 4: project-specific cleanup (local only)

- [ ] **ComptoxR**: consolidate `db-dsstox.yml`, `db-toxval.yml`, and `db-ecotox-source-only.yml` into one repo-local reusable db-build workflow based on db-ecotox-source-only (`ref: main`), with 3 thin cron callers and a shared concurrency group or a pre-created `db-latest` release. Add permissions, concurrency, and timeouts to `cran-readiness.yml` and `schema-check.yml` (raise its timeout to 30-45, pass the PR body through env). Rewrite `.github/workflows/README.md` to match the remaining files.
- [ ] **concert**: in `track-comptoxr-release.yaml`, pin checkout by SHA, add concurrency, and fix the bot email to the `41898282+` form. Copy it to chorus to replace `ComptoxR@*release`.
- [ ] **epa-sswqs**: in `build-toxval.yml`, scope secrets to the steps that need them, create the new release before deleting the old one, check the parquet files exist before publishing, add timeout and concurrency, and use `r-version: renv`. Note that GitHub disables scheduled workflows after 60 days without repo activity, which affects the twice-yearly cron.
- [ ] **bsicons**: disable Actions on the fork, or delete the upstream `R-CMD-check.yaml`. Do not migrate it.

## Phase 5: release propagation

- [ ] Create `DISPATCH_PAT` (Contents read/write on the downstream repos only) on each upstream, and `BUMP_PAT` on each downstream repo. Set the `DOWNSTREAM_REPOS` variable on baseline.
- [ ] Pin the new templates to the release that ships `notify-downstream.yaml` and `track-release-pr.yaml` in a `ci: pin caller stubs` PR; the templates carry `REPLACE_WITH_RELEASE_SHA` until then.
- [ ] **baseline -> downstream**: add the `track-release-pr` caller (`workflow-sha`, event `baseline-release`) to each repo and uncomment the Dependabot `ignore` entry. Add the repo to `DOWNSTREAM_REPOS`.
- [ ] **ComptoxR -> concert, chorus**: add a `notify` job to ComptoxR's `release.yaml` (event `comptoxr-release`; concert already listens for it). Replace concert's `track-comptoxr-release.yaml` with the `description-remote` caller, and copy it to chorus.
- [ ] **specmill -> ComptoxR**: same pattern with its own event type, once its release caller carries the notify job.

## Ongoing

- Callers pin baseline by full SHA with a `# vX.Y.Z` comment. Dependabot proposes the bumps.
- Breaking callee changes (removed or renamed inputs, changed defaults, new required secrets or permissions) require a new major tag.
- Moving a gitleaks caller to v2.0.0: the shared workflow now needs `pull-requests: read` on the calling job (#24). First add `permissions: contents: read` and `pull-requests: read` to the calling job in the repo's gitleaks caller (valid against v1.5.0 too), then repin. Otherwise the workflow fails at startup, including push and scheduled scans, and a grouped Dependabot bump to v2 is red. Callers on a v1 stub today: concert, specmill, singlehit, seanthimons.github.io, and boosterpak. scifindeR returns from its local gitleaks to the shared caller once v2.0.0 exists.
- Every callee keeps the header rules: `permissions: contents: read`, per-job escalation, `timeout-minutes`, and SHA pins. lint-workflows (actionlint and zizmor) enforces them in caller repos.

## Open questions

- Should `oldrel-1` be in the default r-cmd-check matrix? It adds one ubuntu leg per push.
- Should Codecov be adopted beyond ComptoxR, or should repos keep step-summary-only coverage?

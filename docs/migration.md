# Migration to baseline

Phased plan for moving each repository onto the baseline reusable workflows. It is derived from the 2026-09-24 audit ([`audit-2026-09-24.md`](audit-2026-09-24.md)). Phases run in order. Within a phase, repos are independent and can migrate in any order.

## Fix in place before migrating

These three are live hazards. Fix them in their own repos now, in small PRs, without waiting for baseline.

1. **ComptoxR `record-cassettes.yml` script injection (line 62).** Move `workers`, `batch_size`, and `mode` from `${{ inputs.* }}` interpolation into `env:`. Read them with `Sys.getenv()` and validate `workers` and `batch_size` as integers before use. Add `retention-days` to the fixtures artifact.
2. **ComptoxR `pipeline-tests.yml` and `rebase-WIP-branches.yml`.** Delete the `rerecord_cassettes` input and its fixture-deleting path, and delete the dead issue step that uses `dacbd/create-issue-action@main`. Delete `rebase-WIP-branches.yml` entirely.
3. **QRMA_VFAR `release.yaml` (line 98).** It sources `dev/normalize_news.R`, which is not committed. Either commit the normalizer, or fall back to the plain autonewsmd step used in boosterpak.

## Conventions for every migration PR

- Branch: Conventional Branch name, for example `chore/adopt-baseline-ci`. No agent or model names.
- Commits: `ci:` type (a recognized autonewsmd type), for example `ci: adopt baseline gitleaks and commit-lint callers`.
- Workflow files use the `.yaml` extension and LF line endings.
- Callers pin baseline by full SHA with a `# v1.x.y` comment. Pass secrets by name, never `secrets: inherit`.

## Required status checks change name

Reusable-workflow jobs report as `caller-job / callee-job (matrix)`, for example `R CMD check / ubuntu-latest (release)` instead of `ubuntu-latest (release)`. In any repo with branch protection, update the required checks in Settings > Branches (or the ruleset) in the same PR that swaps the workflow. Otherwise PRs block on a check that never reports. After merging, confirm the new names appear under the protection rule and remove the old ones.

## Phase 0: create baseline

- [ ] Create the public repo `seanthimons/baseline`.
- [ ] Add `.github/workflows/*.yaml` (workflow_call), `.github/actions/r-setup` and `.github/actions/pkg-metadata`, `templates/` (caller stubs and shared config), `examples/`, and `.github/workflows/README.md`.
- [ ] Add baseline's own `.github/dependabot.yml` and `self-lint.yaml` (actionlint and zizmor on itself). Confirm self-lint passes.
- [ ] Tag `v1.0.0`. Record its full SHA for callers.
- [ ] Confirm Settings > Actions > General allows other repos to use this repo's workflows (automatic for a public repo).

## Phase 1: hygiene everywhere (low risk)

Every repo gets the gitleaks, commit-lint, and lint-workflows callers, plus `.github/dependabot.yml`, `.gitattributes`, and `.gitleaks.toml`. Delete the local gitleaks and commit-lint copies. Use unfiltered triggers or `github.event.repository.default_branch` so `main` and `master` repos need no per-repo edits. Keep a weekly gitleaks cron in each caller, with a different minute per repo.

- [ ] **ComptoxR**: replace `gitleaks.yaml` and `commit-lint.yaml`. Keep the existing `.gitleaks.toml` and `.gitleaksignore`, and re-base `.gitleaks.toml` on the template's `[extend] useDefault = true` shape. commit-lint now also covers PRs to `integration`.
- [ ] **QRMA_VFAR**: replace `gitleaks.yaml` and `commit-lint.yaml`. Add `dependabot.yml` (currently missing).
- [ ] **boosterpak**: replace `gitleaks.yaml` (v2.3.9) and `commit-lint.yaml`.
- [ ] **chorus**: replace `gitleaks.yaml` and `commit-lint.yaml`. Replace the empty `air.toml` with the shared copy.
- [ ] **concert**: replace `gitleaks.yaml` and `commit-lint.yaml`. Replace the tab-indented `air.toml` with the shared copy.
- [ ] **specmill**: replace `gitleaks.yml` and `commit-lint.yml`. Add `dependabot.yml` (currently missing).
- [ ] **amos-harmonizer**: add the gitleaks and commit-lint callers and all config files.
- [ ] **sk_app**: add the gitleaks and commit-lint callers and config files. `.gitattributes` fixes the CRLF workflow file.
- [ ] **epa-sswqs**: add the gitleaks and commit-lint callers and config files. `.gitattributes` fixes the mixed CRLF/LF in `build-toxval.yml`.
- [ ] **serapeum**: replace `gitleaks.yml`. Add the commit-lint caller and config files. Add allowlist entries to `.gitleaks.toml` only for confirmed false positives (for example `config.yml` or test fixtures).
- [ ] **seanthimons.github.io**: replace `gitleaks.yml`. Drop the stale `integration` branch from triggers. Add the commit-lint caller and config files. Consider allowlisting `docs/` and `_freeze/`.

## Phase 2: R check and coverage

- [ ] **specmill**: replace `check.yml` (dispatch only) with an r-cmd-check caller on push and pull_request, with `setup-air: true`. specmill gets automatic CI for the first time.
- [ ] **ComptoxR**: replace `r-cmd-check.yaml` with a caller (`setup-air: true`, `testthat-parallel-windows: false`). Remove `DESCRIPTION`, `NAMESPACE`, and `.github/**` from every `paths-ignore` block. Replace `test-coverage.yml`, `coverage-check.yml`, and `test-quick.yml` with a single test-coverage caller (`codecov: true`) plus the shared `codecov.yml`. Stop passing `ctx_api_key` to routine test, check, and coverage jobs.
- [ ] **QRMA_VFAR**: replace `r-cmd-check.yaml` and `test-coverage.yaml` with callers. DESCRIPTION declares R >= 4.1.0, so consider adding an `oldrel-1` leg through the `matrix` input.
- [ ] **boosterpak**: replace `r-cmd-check.yaml` with a caller (`quarto: true`). Drop the redundant `.planning/**` paths-ignore.
- [ ] **chorus**: replace `r-cmd-check.yaml` with a caller. The callee's profile isolation fixes the renv activation from `.Rprofile`. Drop the `.planning/**` paths-ignore.
- [ ] **concert**: replace the main r-cmd-check job with a caller. Move the `locked-review` job to an r-renv-tests caller (`os: windows-latest`, `test-filter: review|modules-render`); it now reads the R version from `renv.lock`.
- [ ] **amos-harmonizer**: replace `R-CMD-check.yaml` with an r-cmd-check caller. Drop the stale `feature/initial-harmonization-pipeline` push trigger and add `workflow_dispatch`.
- [ ] **serapeum**: add an r-renv-tests caller (`air-format-check: true`, `shiny-smoke: true`). serapeum currently has no test CI.
- [ ] In every repo above with branch protection, update required checks to the new names in the same PR.

## Phase 3: docs and publishing

- [ ] **pkgdown repos (QRMA_VFAR, boosterpak, specmill, ComptoxR)**: switch to the pkgdown caller (`quarto: true` for boosterpak; `pre-build-script` for ComptoxR's `check_public_api`). In Settings > Pages, change the source from "Deploy from a branch (gh-pages)" to "GitHub Actions". After the first successful deploy, delete the old `gh-pages` branch.
- [ ] **seanthimons.github.io**: decide whether Pages deploys from Actions or from the committed `docs/` folder. If Actions, switch `publish.yml` to a quarto-pages caller with a pinned `quarto-version`, set Pages source to "GitHub Actions", gitignore `docs/`, and stop committing renders. If `docs/` is kept, delete `publish.yml`.
- [ ] **sk_app**: replace `deploy-app.yaml` with `examples/shinylive-pages.yaml` (top-level `permissions: {}`, concurrency group `pages` without cancel, `posit-dev/r-shinylive` pinned by SHA).
- [ ] **Releases (ComptoxR, QRMA_VFAR, boosterpak, chorus, concert, specmill)**: move to a release-r-package caller.
  - [ ] Confirm a `RELEASE_PAT` secret exists in each repo: fine-grained, Contents read and write on that repo, owned by an account allowed to push to protected `main`. Pass it explicitly.
  - [ ] Dry-run through the PR path (`dry-run: true`) before the first real release.
  - [ ] ComptoxR: pass `pre-release-check-script` for `check_public_api`.
  - [ ] QRMA_VFAR: pass `news-postprocess-script` only if `dev/normalize_news.R` was committed.
  - [ ] specmill: choose `notes-mode: autonewsmd` to match the other repos, or keep `generate-notes`. Retire `dev/build_release.R` once the callee covers it.
- [ ] **Rolling prereleases**: replace QRMA_VFAR `publish-rolling-package.yaml` and ComptoxR `publish-rolling-package.yaml` and `publish-integration-package.yaml` with rolling-prerelease callers. ComptoxR integration: `ref: integration`, `tag: integration-latest`, `build-binaries: true`, `require-dev-version: true`.

## Phase 4: project-specific cleanup (local only)

- [ ] **ComptoxR**: consolidate `db-dsstox.yml`, `db-toxval.yml`, and `db-ecotox-source-only.yml` into one repo-local reusable db-build workflow based on db-ecotox-source-only (`ref: main`), with 3 thin cron callers and a shared concurrency group or a pre-created `db-latest` release. Add permissions, concurrency, and timeouts to `cran-readiness.yml` and `schema-check.yml` (raise its timeout to 30-45, pass the PR body through env). Rewrite `.github/workflows/README.md` to match the remaining files.
- [ ] **concert**: in `track-comptoxr-release.yaml`, pin checkout by SHA, add concurrency, and fix the bot email to the `41898282+` form. Copy it to chorus to replace `ComptoxR@*release`.
- [ ] **epa-sswqs**: in `build-toxval.yml`, scope secrets to the steps that need them, create the new release before deleting the old one, check the parquet files exist before publishing, add timeout and concurrency, and use `r-version: renv`. Note that GitHub disables scheduled workflows after 60 days without repo activity, which affects the twice-yearly cron.
- [ ] **bsicons**: disable Actions on the fork, or delete the upstream `R-CMD-check.yaml`. Do not migrate it.

## Ongoing

- Callers pin baseline by full SHA with a `# v1.x.y` comment. Dependabot proposes the bumps.
- Breaking callee input changes require a new major tag.
- Every callee keeps the header rules: `permissions: contents: read`, per-job escalation, `timeout-minutes`, and SHA pins. lint-workflows (actionlint and zizmor) enforces them in caller repos.

## Open questions

- Should `oldrel-1` be in the default r-cmd-check matrix? It adds one ubuntu leg per push.
- Should Codecov be adopted beyond ComptoxR, or should repos keep step-summary-only coverage?

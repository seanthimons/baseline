# baseline

Public source of truth for CI across seanthimons repositories.

baseline provides two things:

- **Reusable workflows** (`on: workflow_call`) in `.github/workflows/`. Each repo keeps a thin caller stub (about 10 to 20 lines) that owns triggers, path filters, cron stagger, and concurrency. The callee owns the jobs, timeouts, action pins, and setup steps.
- **Copied templates** in `templates/` for things GitHub cannot inherit: caller stubs, `dependabot.yml`, `.gitleaks.toml`, `air.toml`, `codecov.yml`, and `.gitattributes`.

The reasons for this layout and the findings behind it are in [`docs/audit-2026-09-24.md`](docs/audit-2026-09-24.md). The rollout order is in [`docs/migration.md`](docs/migration.md).

This repo must stay public. Public caller repos cannot call reusable workflows from a private repo.

## Scope and boundary with boosterpak

baseline and [boosterpak](https://github.com/seanthimons/boosterpak) are separate on purpose. The boundary is where the code runs, not the topic.

- **baseline's consumer is a repository**: a GitHub runner, or static files copied into a repo. baseline owns policy and wiring: workflows, action pins, and static config templates.
- **boosterpak's consumer is an R session inside a project.** boosterpak owns mechanism: anything that needs R logic, and R unit tests, to be correct. Its purpose is to smooth the rough edges of working in R: binaries versus compiling, OS and R version differences, portable restores. Packs are one feature of that.

Two rules keep the line sharp:

- **The laptop test.** If an R fix in baseline would also be needed on a laptop, it belongs in boosterpak. A CI runner is just another new machine.
- **Values, not branches.** baseline may copy a value from boosterpak (for example the P3M URL) but never a branch of logic (for example "if Linux, rewrite to manylinux").

boosterpak will generate the portable setup files, the way renv generates `renv/activate.R`, and baseline will stop authoring them. Two templates are exceptions to the rules above today, because baseline currently authors them: `templates/config/setup.R` (platform URL rewriting and a pinned boosterpak SHA) and the offline loader in `templates/config/.Rprofile`. They are described under [R repositories and cross-platform installs](#r-repositories-and-cross-platform-installs) and are not to be extended.

### The contract

This is everything baseline's CI needs from boosterpak, and everything baseline may know about it:

1. `setup.R` is committed at the project root, and running it restores the locked library on Windows, macOS and Linux.
2. After `source("setup.R")` in a vanilla session, `renv::paths$library(project = getwd())` works.
3. Opening the project before setup installs nothing.
4. baseline reads nothing else from boosterpak: no marker files, no internals, and no knowledge of packs or `boosters.toml`.

The `portable-setup: true` input of `r-renv-tests.yaml`, `quarto-pages.yaml` and the `r-setup` composite relies on points 1 and 2 only: it runs `source("setup.R")` and reads `renv::paths$library()`. Point 3 is a guarantee for people opening a clone; the CI setup step runs with `--vanilla`, so the project profile is never read before setup. Point 4 limits what baseline's workflows and templates may do.

### Adoption order for a new project

A new project adopts in three steps. This is a recommendation, not a dependency.

1. **baseline hygiene first, before the first commit.** `.gitignore`, `.gitattributes`, `.gitleaks.toml`, `dependabot.yml`, and the callers every repo takes: commit-lint, gitleaks and lint-workflows. These are worth most before any history exists. For example, [boosterpak's own adoption PR](https://github.com/seanthimons/boosterpak/pull/41) had to renormalize line endings in two files because `.gitattributes` arrived late.
2. **boosterpak second.** It sets up the R environment: packs, restores and portable lockfiles. For a portable renv project it also provides the portable setup files, `setup.R` and the offline loader. Today those come from this repo's `templates/config/setup.R` and `.Rprofile`; boosterpak's generator will replace them.
3. **baseline's R callers last.** Which ones apply depends on the project type that step 2 established (see [Which workflows apply to which project](#which-workflows-apply-to-which-project)), and `portable-setup: true` needs the `setup.R` from step 2.

Neither tool needs the other installed: boosterpak works in a project with no repo, and baseline works in a repo with no R. Only `portable-setup: true` depends on step 2's `setup.R`. What makes either order safe is that every file, or managed block within a file, has one owner:

- baseline owns the hygiene files and `.github/`.
- boosterpak owns its own project files and its managed block in `.Rprofile`. `setup.R` and the offline loader are on boosterpak's side too; until its generator replaces them, baseline's transitional templates supply them.
- `.Rprofile` otherwise belongs to the project: baseline's template is merged by hand and never replaces the file. `air.toml` is kept by whichever tool wrote it first, and neither tool overwrites an existing one automatically.

Neither tool overwrites a file or block the other owns.

## Layout

```
.github/
  workflows/          reusable workflows (workflow_call), plus the self-*.yaml workflows that run on this repo
  workflows/README.md one paragraph per reusable workflow: inputs, secrets, permissions
  actions/r-setup/    composite: pandoc, R, optional Quarto/Air, deps or renv, profile isolation
  actions/pkg-metadata/ composite: package, version, short SHA from DESCRIPTION
  dependabot.yml      bumps this repo's own action pins
templates/
  workflows/          caller stubs to copy into <repo>/.github/workflows/
  config/             dependabot.yml, .gitleaks.toml, air.toml, codecov.yml, .gitattributes, .gitignore, .gitignore.python
examples/             standalone workflows to copy and edit (shinylive Pages deploy)
docs/                 audit report, raw audit data, migration plan
```

The composite actions are for project-specific workflows in caller repos (for example ComptoxR's db builds). The reusable workflows in this repo inline their own setup steps and do not depend on the composites.

## How to adopt

1. Pick the workflows for your project type from the table below.
2. Copy each caller stub from `templates/workflows/` into `<repo>/.github/workflows/`. Keep the `.yaml` extension.
3. Pin the `uses:` ref to a full commit SHA of a baseline release tag, with the tag as a trailing comment:
   ```yaml
   uses: seanthimons/baseline/.github/workflows/r-cmd-check.yaml@<40-char-sha> # v2.0.0
   ```
   Get the SHA with `git ls-remote https://github.com/seanthimons/baseline refs/tags/v2.0.0`.
4. Edit the caller's triggers, branch filters, and inputs. Pass secrets explicitly by name. Do not use `secrets: inherit`.
5. Grant permissions on the calling job only. A callee cannot escalate beyond what the caller grants. Keep the caller's top-level `permissions: contents: read`.
6. Copy the config files you need from `templates/config/` (`.gitignore` there is the root-local pattern: ignores every root dot-file, dot-directory and `*.md` without naming agent files, with the usual tracked ones such as `.github/`, `README.md` and `NEWS.md` already opted in; opt anything else in with `!/<name>`; it also carries the GitHub R defaults, and Python repos append `.gitignore.python`) to the repo root (`dependabot.yml` and `pull_request_template.md` go in `.github/`).
7. Delete the repo's old local copy of each workflow you replaced.
8. Update branch protection. Required status check names change to `caller-job / callee-job (matrix)`, for example `R CMD check / ubuntu-latest (release)`. Change them in the same PR, or PRs block on a check that never reports. `docs-check.yaml` only blocks merge once `Docs Check / Docs confirmation` is a required check.

## Versioning

- Releases are tagged `vX.Y.Z`. Patch and minor releases never break callers.
- Removing or renaming an input, changing a default in a breaking way, adding a required secret, or requiring a permission that existing callers do not already grant requires a new major tag (for example `v2.0.0`).
- Callers pin a full SHA with a `# vX.Y.Z` comment, never a branch or bare tag.
- `self-release.yaml` tags and publishes a release on each merge to `main` that ships a change, after Self lint and the workflow regression checks pass, then sends `repository_dispatch` `baseline-release` to the repos in `DOWNSTREAM_REPOS` (see "Release propagation"). It reads the Conventional Commit subjects since the last tag: `feat` is a minor release; `fix`, `perf`, `refactor`, `build`, and `ci` commits that change a callee or composite action are patches. `docs`, `chore`, `test`, `style`, other `ci` commits (templates, Dependabot config, `self-*` workflows), and subjects that are not Conventional Commits do not release. Direct pushes to `main` by an admin release the same way.
- A breaking change (`!` in the subject or a `BREAKING CHANGE:` footer) does not release on its own, and neither do later merges until it ships. Run the **Release** workflow from `main` with `bump: major` and `dry-run` off. The same dispatch forces any other bump.
- Make `Commit Lint / Conventional Commits` a required check on `main`, because releases trust the PR title that squash-merge writes to `main`.
- Release callers pin by SHA, so the `# vX.Y.Z` comments in `templates/workflows/` are updated by hand in a `ci:` PR after a release.
- `templates/config/dependabot.yml` covers the `github-actions` ecosystem, which includes `uses: seanthimons/baseline/...@<sha>` refs. By default Dependabot opens grouped `ci:` PRs that bump both third-party pins and baseline pins, but only on its weekly schedule. Repos that adopt `track-release-pr.yaml` get a baseline bump PR as soon as a release is published, and uncomment the `ignore` entry in their Dependabot config so the two do not duplicate; third-party actions stay with Dependabot.
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
| `notify-downstream.yaml` | optional: repos other repos depend on | | | | |
| `track-release-pr.yaml` | optional: repos that pin another repo's releases | optional | optional | | |
| `docs-check.yaml` | optional | | | | |
| `r-renv-tests.yaml` | | yes | | | |
| `quarto-pages.yaml` | | | yes | | |
| `examples/shinylive-pages.yaml` | | | | copy and edit | |

Node and Rust builds stay project-specific. baseline ships no Node or Rust workflows or composites; those repos take only the hygiene callers.

Config files:

| File | Applies to |
|---|---|
| `.github/dependabot.yml` | every repo (add `npm` and `cargo` entries locally where needed) |
| `.gitattributes` | every repo |
| `.gitleaks.toml` | every repo; each repo keeps its own allowlist entries |
| `air.toml` | R repos. baseline's template is canonical, and `boosterpak::init()` writes an identical default (plus an ownership marker line) when its setting asks for one and no `air.toml` exists, so the two must stay the same: a PR that changes this template says that boosterpak's default needs the same change. Neither tool overwrites an existing file automatically. |
| `.Rprofile` | R repos: merge P3M and renv/pak defaults into the existing profile |
| `setup.R` | renv projects: one-command portable restore, with pinned boosterpak tooling |
| `codecov.yml` | repos that enable Codecov in `test-coverage.yaml` |

## Required secrets

| Secret | Used by | Required | Scope |
|---|---|---|---|
| `RELEASE_PAT` | `release-r-package.yaml` | yes | Fine-grained PAT limited to the one repository, with Repository permissions > Contents: Read and write. For `prepare-pr`, also grant Pull requests read/write. PR releases need no main bypass; only the legacy `direct` mode requires an owner allowed to push to protected main. Checkout uses a read-only token; the PAT is scoped to push and PR-creation steps. |
| `DISPATCH_PAT` | `notify-downstream.yaml` | when notifying | Fine-grained PAT with Repository permissions > Contents: Read and write on only the downstream repositories it notifies (the dispatches API requires it). Store it on the upstream repo, ideally as an environment secret restricted to `main`. |
| `BUMP_PAT` | `track-release-pr.yaml` | when tracking | Fine-grained PAT on the one downstream repository: Contents and Pull requests read/write, plus Workflows read/write for `workflow-sha` (it edits files under `.github/`). Add read access to the upstream if it is private. Map an existing secret in the caller if you prefer. |
| `GITLEAKS_LICENSE` | `gitleaks.yaml` | no | Only needed if the repo moves to an organization account. Personal-account repos do not need it. |

No other workflow takes secrets. Repository variable `DOWNSTREAM_REPOS` (whitespace-separated `owner/repo`) lists the repos baseline's own release notifies. API keys such as `CTX_API_KEY` stay in project-specific live-API workflows and must never be passed to baseline callees.

## Releases through a PR

Copy `templates/workflows/release-r-package-pr.yaml` and pin it to a baseline
release supporting `release-mode`. Run `prepare-pr` with `dry-run: false` from
main to open a checked version-and-NEWS PR. Review and merge it normally, then
run `publish` from main with `dry-run: false`. Publishing checks the merged
source without bumping again and creates only the version tag. Neither step
pushes main, so the PR-only branch rule needs no bypass. Dry-run defaults to
true in this template. The legacy caller and direct mode remain supported.

## Release propagation

When a repo publishes a release, repos that depend on it get a PR immediately instead of waiting for a poll or Dependabot.

1. The upstream's release workflow ends with a `notify` job calling `notify-downstream.yaml`, which sends a `repository_dispatch` event (for example `comptoxr-release`) to each listed repo. Copy `templates/workflows/release-r-package-pr-notify.yaml`, or add the same job to an existing release workflow, after the release is published. Set the repository variable `DOWNSTREAM_REPOS` and the secret `DISPATCH_PAT`.
2. Each downstream repo has a `track-release-pr.yaml` caller (template in `templates/workflows/`) listening for that event. It reads the upstream's latest release, rewrites the pin, and opens one PR on a fixed branch `chore/bump-<repo>` (lowercased repo name). A newer release updates that PR in place. It never moves a pin to a lower version. `pin-type: description-remote` rewrites `Remotes: owner/repo@tag` in `DESCRIPTION`; `pin-type: workflow-sha` rewrites `uses: owner/repo/...@<sha>` pins under `.github/` and sets the `# vX.Y.Z` comment. Set the secret `BUMP_PAT`.

The event carries no data the receiver trusts: the tag always comes from the upstream's API, so a stray or late dispatch only triggers a re-check. Keep a weekly schedule in the receiver caller as a backstop for a missed event. Repository names containing a word such as `ai` fail the commit-lint branch rule because the branch includes the name.

## GitHub Pages setting

`pkgdown.yaml` and `quarto-pages.yaml` deploy with the Pages artifact actions (`upload-pages-artifact` plus `deploy-pages`), not a `gh-pages` branch push. Before the first deploy, set each repo's **Settings > Pages > Build and deployment > Source** to **GitHub Actions**. The caller job needs `pages: write` and `id-token: write`. After a successful deploy, delete the old `gh-pages` branch.

Deploy jobs are skipped on `pull_request` events. The build still runs as a PR check.

## Rules every callee follows

- Top-level `permissions: contents: read`. Write scopes are granted per job only.
- `timeout-minutes` on every job.
- No concurrency in callees (callers own it), except release (group `release`, no cancel) and Pages deploys (group `pages`, no cancel).
- No `${{ inputs.* }}` or `${{ github.event.* }}` in `run:` scripts. Values pass through `env:`.
- R package and test jobs set `R_PROFILE_USER=/dev/null` and `RENV_CONFIG_AUTOLOADER_ENABLED=false`, so a repo's `.Rprofile` cannot activate renv over the installed library.
- `lint-workflows.yaml` (actionlint and zizmor) enforces these rules. `self-lint.yaml` runs it on this repo.

## R repositories and cross-platform installs

R workflows and the R setup composite explicitly use `https://p3m.dev/cran/latest`
as CRAN and keep `use-public-rspm: true` so setup-r can choose platform binaries.
Cloud CRAN is an additional binary fallback when P3M does not provide a package.
renv restores enable pak with `RENV_CONFIG_PAK_ENABLED=true`; package dependency
workflows already use pak through setup-r-dependencies.

For local development, merge `templates/config/.Rprofile` into the repo's existing
`.Rprofile`, preserving other project startup code. For renv projects, copy
`setup.R` too and replace the existing `source("renv/activate.R")` line with the
template's offline loader. Keep `renv/activate.R` for the explicit setup command.
The template sets CRAN while preserving other named repositories, enables pak,
and loads only a library prepared by setup for the current OS and R minor version.
Use the portable P3M URL in shared configuration, rather than copying a Linux
distribution-specific binary URL or a machine's library/cache paths. Existing
lockfile repositories and pinned versions still apply during renv restore. The CI
repository defaults do not rewrite lockfiles; the explicit setup command below
repairs platform metadata while preserving versions. See the
[renv configuration reference](https://rstudio.github.io/renv/reference/config.html)
for pak configuration and option precedence.

Downstream repos receive CI changes by bumping their baseline workflow/composite
SHA pins after merge. Local defaults require merging the copied template too;
CI deliberately skips project `.Rprofile` files. No downstream files are changed
by updating baseline alone.

For a renv project that needs portable setup without capability packs, copy
`templates/config/setup.R` to the project root. Run `Rscript --vanilla setup.R`
on each new machine (Windows, macOS, or Linux). It installs a pinned boosterpak
commit into the project library and calls `boosterpak::restore_project()`;
this repairs existing Linux PPM lockfile metadata before restoring exact
versions. For compiled pins absent from the latest binary index, restore adds a
dated P3M snapshot for that operation. To prohibit a source build for a heavy
package, customize the call as
`boosterpak::restore_project(require_binaries = "duckdb")`.
No `boosters.toml`, packs, or startup attachments are created. Keep
`renv/activate.R` and `renv.lock` committed. The script pins the setup tool
independently from the application's lockfile; update that SHA deliberately.
Setup writes machine-local activation data under `renv/local/`; keep that
directory gitignored. Before setup, opening a clone only prints the setup command.
After setup, opening it loads the prepared library without bootstrapping renv or
restoring packages. A different OS or R minor version requires setup again.

After deliberate dependency changes, use `boosterpak::snapshot_project()` to
save a portable lockfile. A plain `renv::snapshot()` bypasses cleanup.

For reusable `r-renv-tests` and `quarto-pages` jobs, opt into this same restore
path with `portable-setup: true` after copying the paired templates and pinning a
baseline version that supports the input. The R setup composite supports the
same input with `use-renv: true`; set `r-version: renv` there for locked R.
Following CI steps receive the prepared library automatically. Existing callers
keep `setup-renv` unless they opt in.

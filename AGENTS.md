# AGENTS.md

Repo rules for coding agents. This file stands alone: it restates the global
rules so a clone works without the global agent files in your home directory.
To adopt it: fill every `FILL` comment, delete sections marked for other
project types (`IF SHINY`, `IF PACKAGE`, `IF PIPELINE`), and replace the
`example from <repo>` comments with this repo's real rules or delete them.

- Decide once whether `AGENTS.md` and `CLAUDE.md` are tracked. Shared repo:
  track them (`!/AGENTS.md`, `!/CLAUDE.md` in `.gitignore`). Sensitive repo:
  `templates/config/.gitignore` blocks all root dot-directories and root
  markdown without naming them, so the files stay local and unlisted.
- Save both as UTF-8 without BOM, LF line endings. No `@` imports here (not every agent
  expands them).
- Where source rules conflicted, this file picks one and records the loser in
  a `Rejected:` line. Keep those lines or delete them.

## Project

<!-- FILL: 2-4 lines: what the repo does, core value, hard constraints. -->

Read before non-trivial changes: README.md <!-- FILL: CONTRIBUTING.md, CONTEXT.md, docs/ -->

<!-- example from serapeum: local-first research assistant. R + Shiny + bslib
UI, DuckDB storage, OpenRouter for chat and embeddings, OpenAlex for search. -->
<!-- example from THREAT: constraints: stay in the R ecosystem; isolate the
ComptoxR API surface behind modules; light, clean theme (a scientific tool,
not a dashboard product). -->

### Known gotchas

<!-- FILL: concrete traps, each with its fix. -->
<!-- example from THREAT: API calls have no tryCatch() and failures show no
notification; one bad query ends the session. -->

## Layout

<!-- FILL: 5-10 key paths and their roles (entry point, R/, shared utils,
data dirs, outputs). No line numbers. -->

<!-- example from serapeum:
- `app.R`: Shiny entry point
- `R/mod_*.R`: Shiny modules
- `R/api_*.R`: API clients
- `R/db.R`: database operations
- `tests/testthat/`: unit tests -->
<!-- example from concert: the app lives in inst/app/app.R and starts via
run_app() in R/run_app.R. There is no top-level app.R. -->
<!-- example from curation: functions.R at the root holds shared helpers
(srs_search(), %ni%, similar_hash()); dict/ holds unit dictionaries. Reuse
them before writing new ones. -->

## Commands

- Shell: <!-- FILL: PowerShell | Git Bash --> Use that shell's syntax.
- R: <!-- FILL: "C:\Program Files\R\R-4.5.1\bin\Rscript.exe" | Rscript on PATH -->
- Setup: <!-- FILL: renv::restore() | pak::local_install_deps() | source("load_packages.R") -->
- Run: <!-- FILL: devtools::load_all(); pkg::run_app(port = 3838, launch.browser = FALSE) | targets::tar_make() -->
- Test one: <!-- FILL: testthat::test_file("tests/testthat/test-<name>.R") -->
- Test by name: <!-- FILL: devtools::test(filter = "<name>") -->
- Test all: <!-- FILL: devtools::test() | testthat::test_dir("tests/testthat") -->
- Docs (IF PACKAGE): `devtools::document()` after roxygen changes.
- Check (IF PACKAGE): `devtools::check()` when risk justifies it.
- Format and lint: `air format .`, then `jarl check .` (repo `air.toml` applies).

## Workflow

- Research before editing. Read the relevant files, tests, docs, and current
  implementation. For externally defined behavior, check authoritative
  upstream docs first.
- Start file-changing work with `git status --short`. Never revert, overwrite,
  or clean up unrelated local work.
- State assumptions, uncertainty, and tradeoffs. If several readings are
  plausible and the wrong one is risky, ask before changing files.
- Push back when an approach is more complex than the problem needs.
- Keep changes scoped to the request. No broad refactors, generated churn,
  speculative features, or unrelated formatting. Ask before expanding scope.
- Search for existing helpers (`R/`, `dev/`, `scripts/`, shared utility
  files) before writing new ones. Prefer existing patterns over new
  abstractions.
- Write the minimum code that solves the request. No flexibility,
  configurability, or error handling for out-of-scope cases.
- Match existing style, even where you would choose differently.
- Remove imports, variables, functions, or files your change made unused.
  Leave pre-existing dead code; mention it instead.
- Code should be simple, durable, defensible, deterministic, and easy to
  verify.
- Before using a name, read the source: field names, function signatures,
  API response fields, framework identifiers (Bootstrap classes, icon names).
- For generated code, trace the whole generator and edit the source or
  template, not the output. Test generated output with real values.
- Multi-step work: write brief success criteria, pair each step with a check,
  and loop until the checks pass.
- Bugs: reproduce first, state a root-cause hypothesis, fix, verify. If the
  fix fails, restart from fresh assumptions.
- Refactors: confirm behavior is unchanged with the same tests before and
  after.

<!-- example from serapeum: new features get a design doc in docs/plans/
before implementation. -->
<!-- example from concert: a new detection method returns list(header_row,
data_start_row, method, confidence), is registered in detect_data_start(),
and gets tests. -->

### Definition of done

- Every referenced name resolves, targeted tests pass, format and lint pass.
- IF SHINY: the app cold-boots (see Shiny).
- IF PACKAGE: `devtools::document()` diff reviewed; `NAMESPACE` and `.Rd`
  match roxygen.
- IF PIPELINE: `targets::tar_validate()` passes and the affected targets
  build.
- If a check cannot run (credentials, services, packages), say so and report
  the closest validation performed.

## Git

### Branches

- Use a feature branch for non-trivial work. Use a worktree in a sibling
  directory (for example `../<repo>-sprint/`) for sprints or several related
  fixes. Never commit to a protected trunk.
- Rejected: branching before every change, including typo fixes (serapeum).
- Branch names follow Conventional Branch: `type/description`, lowercase,
  hyphen-separated. Prefixes: `feat/`, `feature/`, `fix/`, `bugfix/`,
  `hotfix/`, `release/`, `chore/`, `ci/`, `docs/`, `refactor/`, `test/`.
- Trunks are `main`, `master`, and `develop`; do not prefix them.
- Put issue ids in the description: `fix/issue-123-api-timeout`.
- Hard block: no agent, assistant, model, or AI source names in branch
  names (`codex/`, `claude/`, `ai/`, `copilot/`, `cursor/`, `chatgpt`, `gpt`,
  `openai`, `anthropic`, `gemini`, `llama`, `mistral`, `grok`, `qwen`,
  `deepseek`, `llm`, or similar).
- Verify the current directory and local state before deleting a worktree or
  branch.

<!-- FILL: branch model if not plain feature -> trunk. -->
<!-- example from ComptoxR: feature -> integration -> main -> Release. Cut
feature branches from integration; open PRs against main. -->

### Commits

- Conventional Commits: `type: description`, `type(scope): description`,
  `type!: description`, or `type(scope)!: description`.
- `feat:` for user-facing features, `fix:` for bug fixes.
- With `autonewsmd`, use only `feat`, `fix`, `refactor`, `perf`, `build`,
  `test`, `ci`, `docs`, `style`, `chore` for commits that belong in
  `NEWS.md`. Scopes use ASCII letters, digits, and underscores only
  (`docs(phase36_1): ...`, not `fix(37-01): ...` or `test(api/client): ...`).
- Write the first line as the release note. Put issue or PR refs at the end:
  `fix(resolver): use bulk POST endpoint (#219)`.
- Mark breaking changes with `!` before the colon or a `BREAKING CHANGE:`
  footer.
- No final subjects like `Merge ...`, `Checkpoint ...`, `WIP`, or bare
  summaries without a type.
- Rejected: free-form 50-character summaries without a type (concert).
- Small commits, one reason each. Commit after each logical unit: a function
  done and tested, a bug fix verified, a refactor green, or before switching
  tasks.
- Hard block: no agent, assistant, model, or AI source names anywhere in a
  commit message. No `Co-authored-by` or attribution trailers. If a branch
  name or message references one, rename it to describe the work.

### Releases

- If a release workflow owns versioning, do not edit `Version:` in
  `DESCRIPTION` and do not create tags by hand.

<!-- example from ComptoxR: the manual Release workflow bumps the version,
tags, regenerates NEWS.md, and cuts the GitHub release. -->

## R style

- Format with `air format <file>` and lint with `jarl check <file>`; apply
  `jarl check --fix`, then fix the rest by hand. Both must pass.
- `air.toml` defaults: line width 120, 2-space indent. Match existing
  indentation where no `air.toml` exists.
- Use `TRUE`/`FALSE`, never `T`/`F`.
- Use `snake_case` for objects and functions. Keep names inherited from
  external APIs as they are (for example camelCase endpoint names).
- Use `here::here()` for project-relative paths.
- Use `cli::cli_alert_*()` for status messages and `cli::cli_abort()` for
  fatal errors.
- Namespace non-base calls outside the core dplyr/tidyr verbs
  (`rio::import()`, `janitor::clean_names()`); always prefix ggplot2
  (`ggplot2::ggplot()`, `ggplot2::aes()`).
- Confirm column and object names with `names()` or `dplyr::glimpse()` before
  building a pipeline.
- Ad hoc analysis, debugging, and validation scripts must run with
  `source("path/to/script.R")` from an interactive session. CLI scripts keep
  core logic in functions; a thin `Rscript` entry point may stay.
- Run multi-statement R from a temporary `.R` file, not `Rscript -e`.
- From PowerShell, use single-quoted R string literals so quotes reach
  Rscript intact.

<!-- example from THREAT: section headers `# Name ----`, `## N. Tab ----`,
`### Sub ----`; single quotes for column names, double quotes for UI text. -->

## R package (IF PACKAGE)

- Prefer `testthat`, `devtools`, and package-native validation.
- Prefer R over text search when the question depends on package semantics:
  metadata, roxygen, namespace, exports, or load behavior.
- Keep roxygen, exported behavior, tests, `.Rd` files, and `NAMESPACE`
  consistent. Run `devtools::document()` after roxygen changes and review the
  generated diff.
- Do not change data files, schema snapshots, generated tests, or generated
  docs unless the task requires it.
- Regenerate generated code from its source and run the generator's check
  mode; never hand-edit generated files.

<!-- example from ComptoxR: install the pinned toolkit with
source("dev/install_toolkit.R"); install_toolkit(). Regenerate a promoted
operation only from its approved production schema. -->

## Testing

- Prefer targeted tests; run the full suite only for broad-impact changes
  (shared helpers, package setup, test infrastructure, generated code,
  cross-module contracts).
- Packages: `testthat::test_file("tests/testthat/test-<name>.R")` or
  `devtools::test(filter = "<name>")`; full `devtools::test()` or
  `devtools::check()` when risk justifies it.
- Non-package apps and scripts: tests live in `tests/testthat/`; run
  `testthat::test_dir("tests/testthat")`.
- Rejected: flat `tests/` run with `testthat::test_dir("tests")` (concert).
- Cover adversarial and edge conditions relevant to the change: size,
  duplication, invalid input, empty input.
- New tests follow existing `test-*.R` patterns and use fixtures, mocks, or
  deterministic local data for external calls.
- Derive assertions from the real implementation, not from assumptions.

## Shiny (IF SHINY)

- Cold-boot after any UI, server, module, or reactive change: start the Run
  command in the background from a fresh R session, wait for `Listening on`
  or an error, then stop it. Fix startup failures (missing imports, icons,
  load order, module wiring) before handoff.
- Use `ns()` for every module input and output ID. IDs are `snake_case`.
- Guard reactives with `req()`.
- An `observe()` that reads and writes the same `reactiveVal` loops forever.
  Keep the trigger outside and wrap the rest in `isolate({ ... })`. This
  applies to ExtendedTask result handlers and pollers; `observeEvent()` is
  safe.
- Wrap API calls and file reads in `tryCatch()`; show every error state with
  `showNotification()` or `validate()`.
- Set the upload limit in the app entry point:
  `options(shiny.maxRequestSize = <FILL> * 1024^2)`.
- Test theme, dark-mode, and CSS specificity changes against the full page,
  including htmlwidget canvases (vis.js, plotly).

<!-- example from concert: state lives in one reactiveValues() store with
raw, clean, detection, and file_info slots. -->

## Pipelines (IF PIPELINE)

- targets: run `targets::tar_validate()`, check `targets::tar_outdated()`,
  then `targets::tar_make(names = ...)` for the affected targets.
- renv: `renv::restore()` to set up. Run `renv::snapshot()` only for an
  intentional dependency change; never hand-edit `renv.lock`.
- Skip expensive acquisition when outputs are fresh. Freshness threshold:
  <!-- FILL: e.g. 180 days via file.info()$mtime -->. If a step fails on
  missing data, run its acquisition step first.
- Use DuckDB for large data; build lazy `dplyr`/`dbplyr` queries and
  `collect()` last. Validate SQL against the DuckDB dialect.
- Remove large intermediates with `rm()` after heavy steps.
- Parallel maps: <!-- FILL: mirai::daemons(parallel::detectCores() - 1) | none -->

<!-- example from curation: acquisition uses httr2 request pipelines, rvest
scraping, or V8 for JavaScript data files; exports use saveRDS() and
nanoparquet::write_parquet(). -->

## Data handling

- Import with `rio::import()` and apply `janitor::clean_names()` right after,
  unless the repo names another reader.
- Validate before processing: file type, size, and data frame structure.
  Use `tryCatch()` fallbacks for file reading.
- Raw data and outputs are gitignored; commit code only. Data dirs:
  <!-- FILL: data/, final/ -->
- Do not modify committed data, fixtures, or snapshots unless the task
  requires it.
- State the return shape of cleaning functions here and keep it:
  <!-- FILL -->

<!-- example from concert: every cleaning function returns
list(cleaned_data, audit_trail); the audit trail is one tibble with row_id,
field, step, original_value, new_value, reason. -->

## Shell

- Use the shell named in Commands. Prefer `rg` for search; use structured
  parsers or language tooling when they fit.
- Use non-interactive flags so nothing waits on a prompt: `apt-get -y`,
  `ssh`/`scp -o BatchMode=yes`, `HOMEBREW_NO_AUTO_UPDATE=1`, no `git -i`
  commands.
- `cp`, `mv`, and `rm` may be aliased to `-i`. Use `-f` only on paths you
  created in this session. Never force-delete or overwrite paths you did not
  create.
- Rejected: `rm -rf` and `cp -rf` as default forms (THREAT, serapeum).
- Windows: when deleting directories, check for file locks, close handles,
  and retry. If R network calls fail, download with `curl` first and load
  the local file.

## Issue tracking

<!-- PICK ONE tracker and list 3-5 commands. -->
<!-- example from serapeum (beans, .beans/): beans list --ready;
beans show <id>; beans update <id> --status in-progress;
beans update <id> --status completed. -->
<!-- example from THREAT (bd, .beads/): bd ready; bd show <id>;
bd update <id> --claim; bd close <id>; bd dolt push. -->

- Use one tracker. No separate `TODO.md`.
- In-session todo tools are fine; persistent tasks go in the tracker.
- Rejected: banning TodoWrite, TaskCreate, and MEMORY.md (THREAT).
- Planning dirs such as `.planning/` are local-only: gitignored, never
  committed.
- Close an issue only after its programmatic verification passes, or after
  user acceptance when none is specified. Record the evidence first.
- Confirm which issue is meant when a number is ambiguous.

## Session end

Work is done when it is committed and pushed:

1. File tracker issues for follow-up work.
2. Run quality gates if code changed: tests, format, lint, build.
3. Update issue status.
4. Commit, `git pull --rebase` on your branch, `git push`, then
   `git status` must show up to date with origin. If the push fails,
   resolve and retry.
5. Clean up only what you created: your stashes, your merged branches;
   `git fetch --prune`.
6. Hand off: what changed, what is left, how to verify.

- Push your feature branch before reporting done. Do not push to trunk or
  force-push unless asked.
- Rejected: pushing any branch, including trunk, without review at every
  session end (THREAT, serapeum).
- If features changed, check README.md and ask whether to update it.

<!-- example from THREAT: run bd dolt push before git push. -->

## Communication

- When asked to review or scan, report findings first; act after.
- When asked for a plan or options, wait for approval before changing code.
- Summarize what you researched when it shaped the change.
- Final message: changed files and targeted validation. If no tests ran, say
  why.
- No agent, assistant, or model names in code, docs, branches, or commits.

<!-- example from ComptoxR: use ASD-STE100 Simplified Technical English. -->

## Performance

- Watch runtime shape on large or user-provided data: nested loops,
  repeated regex compilation, growing objects in loops, per-row data frame
  mutation, accidental quadratic behavior.
- Do not grow a list in a loop and `bind_rows()` it. Pre-allocate vectors and
  build one tibble at the end.
- Compile regex once outside loops; use vectorized `stringr::str_detect()`
  over whole columns.
- Vectorize instead of row loops:
  `idx <- which(!is.na(x) & x != ""); out[idx] <- "flagged"`.
- Do not assign `df$col[i]` in a loop (copy on modify). Extract the vector,
  update it, assign it back once.
- Add a targeted test or benchmark for adversarial size when performance
  matters.

## Security

- Never write real API keys, tokens, credentials, or private URLs into
  tracked files, fixtures, logs, examples, or generated docs.
- `.Renviron` and `.env` are gitignored; never commit them.
- Routine tests run without secrets. Live recording against real APIs is
  opt-in only.
- Use existing HTTP fixtures or cassettes. Re-record only when the task
  requires it; it can hit production APIs and need real credentials.
- Before committing a new or updated cassette, run the repo's cassette
  safety helper and confirm keys, tokens, and private URLs are redacted.
- Add `.gitleaks.toml` allowlist entries only for confirmed false positives.

<!-- example from ComptoxR: source("tests/testthat/helper-vcr.R");
check_cassette_safety(). Live recording needs ctx_api_key and runs via the
Record VCR Cassettes workflow. -->

## CI

Workflows are reusable callees in `seanthimons/baseline`; copy caller stubs
from `templates/workflows/` and pin by SHA. Details:
`.github/workflows/README.md`.

| Project type | Adopt callers |
|---|---|
| Every repo | `gitleaks`, `commit-lint`, `lint-workflows` |
| R package | + `r-cmd-check`; opt in: `test-coverage`, `pkgdown`, `build-package`, `release-r-package`, `rolling-prerelease` |
| R app with renv | + `r-renv-tests` (shinylive apps: copy `examples/shinylive-pages.yaml`) |
| Quarto site | + `quarto-pages` |
| Other | hygiene set only |

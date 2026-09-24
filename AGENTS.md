# AGENTS.md

Repo rules for coding agents. Global rules in `~/.codex/AGENTS.md` and
`~/.claude/CLAUDE.md` still apply; this file adds only what is specific to
this repo. Do not copy global rules here.

- `AGENTS.md` and `CLAUDE.md` are tracked in git. Never gitignore or
  `.git/info/exclude` them; if a pattern like `/*.md` exists, add
  `!/AGENTS.md` and `!/CLAUDE.md`.
- Save both as UTF-8 without BOM. No `@` imports here (Codex does not expand
  them).

## Project

<!-- FILL: 2-4 lines: what the repo does, core value, hard constraints. -->

Read before non-trivial changes: README.md <!-- FILL: CONTEXT.md, CONTRIBUTING.md, docs/ -->

## Layout

<!-- FILL: 5-10 key paths and their roles (entry point, R/, shared utils,
data dirs, outputs). No line numbers. -->

## Commands

- Setup: <!-- FILL: renv::restore() | pak::local_install_deps() -->
- Run: <!-- FILL: devtools::load_all(); pkg::run_app(port = 3838, launch.browser = FALSE) | targets::tar_make() -->
- Test one: <!-- FILL: testthat::test_file("tests/testthat/test-<name>.R") -->
- Test all: <!-- FILL: devtools::test() -->
- Format and lint: `air format .`, then `jarl check .` (repo `air.toml` applies)

## Definition of done

- Targeted tests pass, then format and lint pass.
<!-- IF SHINY: cold-boot the app with the Run command from a fresh R session and wait for "Listening on". -->
<!-- IF PIPELINE: targets::tar_validate(), then tar_make() on the affected targets. -->

## Project conventions

<!-- FILL: only rules that differ from global rules or cannot be inferred
from the code (e.g. here::here() paths, janitor::clean_names() after import,
cli messages, a return-shape contract). -->

## Known gotchas

<!-- FILL: concrete traps, e.g. observe() that reads and writes the same
reactiveVal loops forever; wrap the read in isolate(). -->

## Issue tracking

<!-- PICK ONE: GitHub Issues | beans (.beans/) | bd (beads). List 3-5
commands. Do not ban harness tools (TodoWrite etc.). -->

## Session end

- Commit logical units with Conventional Commits; push the branch when the
  work is complete.

## Shell

- Use non-interactive flags (`-y`, `BatchMode=yes`) so commands never wait
  on a prompt.
- Do not force-delete or overwrite (`rm -rf`, `cp -f`) paths you did not
  create in this session.

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

# Run from the repo root: source("tests/check-news-headings.R"); check_news_headings()
check_news_headings <- function(
  workflow = ".github/workflows/release-r-package.yaml"
) {
  lines <- readLines(workflow, warn = FALSE)
  start <- grep("# pkgdown requires package-prefixed", lines, fixed = TRUE)
  stopifnot(length(start) == 1L)
  code <- paste(trimws(lines[start + seq_len(5L)]), collapse = "\n")
  parse(text = code)

  path <- tempfile("news-headings-")
  dir.create(path)
  old <- setwd(path)
  on.exit(
    {
      setwd(old)
      unlink(path, recursive = TRUE)
    },
    add = TRUE
  )
  writeLines(
    c(
      "Package: example.pkg",
      "Version: 1.2.3",
      "Title: Example Package",
      "Description: A minimal package for testing news pages.",
      "Authors@R: person('Test', 'Author', role = c('aut', 'cre'), email = 'test@example.org')",
      "License: MIT"
    ),
    "DESCRIPTION"
  )
  input <- c(
    "# example.pkg NEWS",
    "",
    "## v1.2.3 (2026-09-25)",
    "",
    "#### Bug fixes",
    "",
    "- Fixed a bug.",
    "",
    "## v1.2.2.9000 (2026-09-24)",
    "",
    "#### Features",
    "",
    "- Older change."
  )
  writeLines(input, "NEWS.md")
  pkg <- pkgdown::as_pkgdown(
    path,
    override = list(news = list(cran_dates = FALSE))
  )
  # Reproduce the malformed generated page before applying the workflow fix.
  suppressWarnings(pkgdown::build_news(pkg))
  html <- readLines(file.path(path, "docs/news/index.html"), warn = FALSE)
  stopifnot(!any(grepl("Fixed a bug", html, fixed = TRUE)))
  eval(parse(text = code))
  expected <- input[-1L]
  expected[c(2L, 8L)] <- c(
    "## example.pkg v1.2.3 (2026-09-25)",
    "## example.pkg v1.2.2.9000 (2026-09-24)"
  )
  stopifnot(identical(readLines("NEWS.md"), expected))
  pkgdown::build_news(pkg)
  html <- readLines(file.path(path, "docs/news/index.html"), warn = FALSE)
  stopifnot(any(grepl("Fixed a bug", html, fixed = TRUE)))
  stopifnot(any(grepl("Older change", html, fixed = TRUE)))
  eval(parse(text = code))
  stopifnot(identical(readLines("NEWS.md"), expected))
  # Handwritten NEWS and body text remain unchanged.
  handwritten <- c("# example.pkg 1.2.3", "", "- Mention ## v1.0.0 in text.")
  writeLines(handwritten, "NEWS.md")
  eval(parse(text = code))
  stopifnot(identical(readLines("NEWS.md"), handwritten))
  invisible(TRUE)
}

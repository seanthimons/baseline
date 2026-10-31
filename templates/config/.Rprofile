# Local defaults; setup.R is the only entry point that installs packages.
local({
  repos <- getOption("repos")
  repos["CRAN"] <- "https://p3m.dev/cran/latest"
  if (!any(names(repos) == "CRAN_fallback")) {
    repos["CRAN_fallback"] <- "https://cloud.r-project.org"
  }
  options(repos = repos, renv.config.pak.enabled = TRUE)

  if (file.exists("renv.lock")) {
    marker <- "renv/local/startup"
    startup <- if (file.exists(marker)) readLines(marker, warn = FALSE) else character()
    r_minor <- paste(R.version$major, strsplit(R.version$minor, ".", fixed = TRUE)[[1L]][1L], sep = ".")
    ready <- length(startup) == 3L &&
      identical(startup[2:3], c(R.version$platform, r_minor)) &&
      file.exists(file.path(startup[[1L]], "renv", "DESCRIPTION"))
    if (ready) {
      loadNamespace("renv", lib.loc = startup[[1L]])
      renv::load(project = getwd())
    } else {
      message("Run Rscript --vanilla setup.R to prepare this project's environment.")
    }
  }
})

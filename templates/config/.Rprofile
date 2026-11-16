# Local defaults. For renv projects, boosterpak::write_portable_setup() manages the startup block.
local({
  repos <- getOption("repos")
  repos["CRAN"] <- "https://p3m.dev/cran/latest"
  if (!any(names(repos) == "CRAN_fallback")) {
    repos["CRAN_fallback"] <- "https://cloud.r-project.org"
  }
  options(repos = repos, renv.config.pak.enabled = TRUE)
})

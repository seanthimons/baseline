# Run from the project root: Rscript --vanilla setup.R (or source("setup.R")).
# Setup tool pinned independently of the application's locked package versions.
local({
  if (!file.exists("renv.lock") || !file.exists("renv/activate.R")) {
    stop("Run setup.R from a project root containing renv.lock and renv/activate.R.")
  }
  options(
    repos = c(getOption("repos")[names(getOption("repos")) != "CRAN"], CRAN = "https://p3m.dev/cran/latest"),
    renv.config.pak.enabled = TRUE,
    renv.config.autoloader.enabled = TRUE
  )
  Sys.setenv(RENV_PROJECT = getwd())
  source("renv/activate.R")
  # Keep shared URLs portable; select Linux binaries only for this process.
  repos <- getOption("repos")
  ppm <- "^(https?://(?:p3m\\.dev|packagemanager\\.(?:posit\\.co|rstudio\\.com))/[^/]+)"
  repos <- sub(paste0(ppm, "/__linux__/[^/]+/"), "\\1/", repos, perl = TRUE)
  if (!any(names(repos) == "CRAN_fallback")) {
    repos["CRAN_fallback"] <- "https://cloud.r-project.org"
  }
  if (identical(R.version$os, "linux-gnu")) {
    repos <- sub(paste0(ppm, "/([^/]+)$"), "\\1/__linux__/manylinux_2_28/\\2", repos, perl = TRUE)
    options(
      HTTPUserAgent = sprintf(
        "R/%s R (%s)",
        getRversion(),
        paste(getRversion(), R.version$platform, R.version$arch, R.version$os)
      )
    )
  }
  options(repos = repos, renv.config.repos.override = repos)

  if (!requireNamespace("pak", quietly = TRUE)) {
    renv::install("pak", prompt = FALSE)
  }
  if (
    identical(R.version$os, "linux-gnu") && is.null(getOption("pkg.platforms")) && !nzchar(Sys.getenv("PKG_PLATFORMS"))
  ) {
    platform <- pak::system_r_platform()
    options(pkg.platforms = unique(c(platform, sub("^([^-]+)-[^-]+-", "\\1-pc-", platform), "source")))
  }

  ref <- "85ea5abc0d2d16c0d9601f640c4f3510b784a388"
  path <- find.package("boosterpak", quiet = TRUE)
  installed_ref <- if (length(path)) {
    read.dcf(file.path(path, "DESCRIPTION"), fields = "RemoteSha")[[1L]]
  } else {
    NA_character_
  }
  if (!identical(installed_ref, ref)) {
    if (isNamespaceLoaded("boosterpak")) {
      unloadNamespace("boosterpak")
    }
    renv::install(paste0("seanthimons/boosterpak@", ref), prompt = FALSE)
  }
  boosterpak::restore_project()
  # Machine-local activation data: opening a fresh clone never bootstraps renv.
  dir.create("renv/local", showWarnings = FALSE, recursive = TRUE)
  if (!file.exists("renv/local/.gitignore")) {
    writeLines("*", "renv/local/.gitignore")
  }
  r_minor <- paste(R.version$major, strsplit(R.version$minor, ".", fixed = TRUE)[[1L]][1L], sep = ".")
  writeLines(c(dirname(find.package("renv")), R.version$platform, r_minor), "renv/local/startup")
})

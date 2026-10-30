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
  # Runtime-only URL: shared configuration and lockfiles stay portable.
  if (identical(R.version$os, "linux-gnu")) {
    repos <- getOption("repos")
    repos["CRAN"] <- "https://p3m.dev/cran/__linux__/manylinux_2_28/latest"
    options(
      repos = repos,
      HTTPUserAgent = sprintf(
        "R/%s R (%s)",
        getRversion(),
        paste(getRversion(), R.version$platform, R.version$arch, R.version$os)
      )
    )
  }

  if (!requireNamespace("pak", quietly = TRUE)) {
    renv::install("pak", prompt = FALSE)
  }
  if (
    identical(R.version$os, "linux-gnu") && is.null(getOption("pkg.platforms")) && !nzchar(Sys.getenv("PKG_PLATFORMS"))
  ) {
    platform <- pak::system_r_platform()
    options(pkg.platforms = unique(c(platform, sub("^([^-]+)-[^-]+-", "\\1-pc-", platform), "source")))
  }

  ref <- "14346ade36ab381c3d0388821b3b573474997852"
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

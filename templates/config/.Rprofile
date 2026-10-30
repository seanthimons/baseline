# Merge into the project .Rprofile before any renv activation line.
# Keep the portable URL; let pak / renv select binaries for the current OS.
options(
  repos = c(getOption("repos")[names(getOption("repos")) != "CRAN"], CRAN = "https://p3m.dev/cran/latest"),
  renv.config.pak.enabled = TRUE
)

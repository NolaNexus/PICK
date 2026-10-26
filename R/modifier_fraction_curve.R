#' Fit the % ores modified curve from observed drop data
#'
#' Fits a saturating (asymptotic exponential) model to observed modifier
#' fraction data:
#'     pct_modified ~ Asym * (1 - exp(-k * eff_mb))
#' where Asym is the ceiling (~99.4% per Stat Systems Guide) and k controls
#' the steepness of the rise. Fitted via stats::nls() (base R, always
#' available). Degrades to NULL on non-convergence so the caller can fall
#' back to the hardcoded approximation.
#'
#' @param query_eff_mb Numeric vector of effective MB values at which to
#'   predict pct_modified.
#' @param obs_eff_mb Numeric vector of observed effective MB values.
#' @param obs_modified Integer/numeric vector of observed modified-ore counts.
#' @param obs_total Integer/numeric vector of observed total ore counts.
#' @return Data frame with columns eff_mb and pct_modified (0-100 scale), or
#'   NULL if the fit failed (too few points / non-convergence).
fit_modifier_fraction <- function(
  query_eff_mb,
  obs_eff_mb,
  obs_modified,
  obs_total
) {
  n <- length(obs_eff_mb)
  if (n < 3) {
    return(NULL)
  }

  # Observed fraction modified per point, clipped to [0, 1].
  frac <- pmin(pmax(obs_modified / pmax(obs_total, 1), 0), 1)

  # Need some variation in eff_mb and at least some non-zero fractions.
  if (length(unique(obs_eff_mb)) < 2 || sum(frac) <= 0) {
    return(NULL)
  }

  dat <- data.frame(eff_mb = obs_eff_mb, frac = frac)

  fit <- tryCatch(
    nls(
      frac ~ Asym * (1 - exp(-k * eff_mb)),
      data = dat,
      start = list(Asym = 0.994, k = 0.001),
      algorithm = "port",
      lower = c(Asym = 0, k = 0),
      upper = c(Asym = 1, k = 1),
      control = nls.control(maxiter = 200, tol = 1e-6, minFactor = 1e-8)
    ),
    error = function(e) NULL
  )

  if (is.null(fit)) {
    return(NULL)
  }

  qdat <- data.frame(eff_mb = query_eff_mb)
  pred <- tryCatch(
    predict(fit, newdata = qdat),
    error = function(e) NULL
  )

  if (is.null(pred)) {
    return(NULL)
  }

  # Convert fraction (0-1) to percentage (0-100), clip to [0, 99.4].
  pct <- pmin(pmax(as.numeric(pred) * 100, 0), 99.4)

  data.frame(
    eff_mb = as.numeric(query_eff_mb),
    pct_modified = round(pct, 4),
    stringsAsFactors = FALSE
  )
}

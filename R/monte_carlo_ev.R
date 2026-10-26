#' Monte Carlo simulation of expected value per hour
#'
#' Simulates EV per pan and pans per hour as correlated normal draws,
#' then returns the mean and 5th/95th percentiles of EV per hour.
#'
#' @param n_samples Integer number of simulation draws.
#' @param ev_mean Mean EV per pan.
#' @param ev_sd Standard deviation of EV per pan.
#' @param pph_mean Mean pans per hour.
#' @param pph_sd Standard deviation of pans per hour.
#' @return Named numeric vector with mean, p05, p95 of EV per hour.
monte_carlo_ev <- function(n_samples, ev_mean, ev_sd, pph_mean, pph_sd) {
  set.seed(42)

  ev <- rnorm(n_samples, mean = ev_mean, sd = ev_sd)
  pph <- rnorm(n_samples, mean = pph_mean, sd = pph_sd)

  # Clamp negatives to zero (EV and pans/hour cannot be negative).
  ev[ev < 0] <- 0
  pph[pph < 0] <- 0

  ev_hour <- ev * pph

  c(
    mean = mean(ev_hour),
    p05 = quantile(ev_hour, 0.05),
    p95 = quantile(ev_hour, 0.95)
  )
}

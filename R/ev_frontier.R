#' EV / risk Pareto frontier for candidate builds
#'
#' Computes the expected-value-per-hour distribution for each candidate build
#' via Monte Carlo (correlated draws of EV per pan and pans per hour), then
#' returns the Pareto frontier: builds not dominated on both mean EV/hour and
#' p05 EV/hour (risk-adjusted downside). Useful for comparing gear/location
#' choices where higher mean comes with higher variance.
#'
#' @param candidates Data frame with columns: name, ev_per_pan_mean,
#'   ev_per_pan_sd, pph_mean, pph_sd.
#' @param n_samples Integer Monte Carlo draws per candidate.
#' @return Data frame with columns: name, mean_ev_hour, p05_ev_hour,
#'   p95_ev_hour, ev_per_pan_mean, pph_mean, on_frontier, dominated_by.
#'   Sorted by mean_ev_hour descending.
ev_pareto_frontier <- function(
  candidates,
  n_samples = 10000
) {
  set.seed(42)

  if (nrow(candidates) == 0) {
    return(data.frame(
      name = character(0), mean_ev_hour = numeric(0), p05_ev_hour = numeric(0),
      p95_ev_hour = numeric(0), ev_per_pan_mean = numeric(0), pph_mean = numeric(0),
      on_frontier = logical(0), dominated_by = character(0),
      stringsAsFactors = FALSE
    ))
  }

  n <- nrow(candidates)
  mean_ev_hour <- numeric(n)
  p05_ev_hour <- numeric(n)
  p95_ev_hour <- numeric(n)

  for (i in seq_len(n)) {
    ev <- rnorm(n_samples, mean = candidates$ev_per_pan_mean[i],
                sd = candidates$ev_per_pan_sd[i])
    ev[ev < 0] <- 0
    pph <- rnorm(n_samples, mean = candidates$pph_mean[i],
                 sd = candidates$pph_sd[i])
    pph[pph < 0] <- 0
    ev_hour <- ev * pph

    mean_ev_hour[i] <- mean(ev_hour)
    p05_ev_hour[i] <- quantile(ev_hour, 0.05)
    p95_ev_hour[i] <- quantile(ev_hour, 0.95)
  }

  # Pareto dominance: A dominates B if A.mean >= B.mean AND A.p05 >= B.p05
  # with at least one strict. Higher is better for both.
  on_frontier <- logical(n)
  dominated_by <- character(n)
  for (i in seq_len(n)) {
    dominated <- FALSE
    dominator <- NA_character_
    for (j in seq_len(n)) {
      if (i == j) next
      a_mean <- mean_ev_hour[j]; a_p05 <- p05_ev_hour[j]
      b_mean <- mean_ev_hour[i]; b_p05 <- p05_ev_hour[i]
      if (a_mean >= b_mean && a_p05 >= b_p05 &&
          (a_mean > b_mean || a_p05 > b_p05)) {
        dominated <- TRUE
        dominator <- candidates$name[j]
        break
      }
    }
    on_frontier[i] <- !dominated
    dominated_by[i] <- if (dominated) dominator else ""
  }

  data.frame(
    name = candidates$name,
    mean_ev_hour = round(mean_ev_hour, 2),
    p05_ev_hour = round(p05_ev_hour, 2),
    p95_ev_hour = round(p95_ev_hour, 2),
    ev_per_pan_mean = candidates$ev_per_pan_mean,
    pph_mean = candidates$pph_mean,
    on_frontier = on_frontier,
    dominated_by = dominated_by,
    stringsAsFactors = FALSE
  )[order(-mean_ev_hour), ]
}

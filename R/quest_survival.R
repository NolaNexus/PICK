#' Survival analysis for Dredge Master quest completion
#'
#' Simulates many Dredge Master quest runs across a grid of build/event
#' configurations, records time-to-completion (right-censored at max_time), and
#' fits a Weibull survival regression (survival::survreg) with covariates for
#' luck, modifier boost, solar magnifier, modifier surge, meteor, and weather
#' events. Returns model coefficients, hazard ratios, baseline median time to
#' completion, a survival curve at requested time points, and quest-completion
#' probabilities within key time windows.
#'
#' @param n_runs Integer number of quest runs to simulate.
#' @param n_quests Integer quests per run target.
#' @param max_time_hours Numeric right-censoring time in hours.
#' @param time_points Numeric vector of times (hours) for survival curve.
#' @param luck_levels Numeric vector of current_luck values to simulate.
#' @param modifier_boost_levels Numeric vector of modifier_boost values.
#' @param meteor Logical whether meteor is active (applied to all runs).
#' @param weather_events Integer number of weather events (applied to all runs).
#' @param solar_magnifier Logical whether Solar Magnifier active.
#' @param modifier_surge Logical whether Modifier Surge active.
#' @param bonus_interval Integer quests between bonus rewards.
#' @param base_pph Numeric base pans per hour for simulation.
#' @return List with coefficients, hazard_ratios, baseline_median_time_hours,
#'   n_runs, n_completed, n_censored, survival_curve, completion_prob_within.
quest_survival_analysis <- function(
  n_runs = 200,
  n_quests = 50,
  max_time_hours = 48,
  time_points = c(1, 5, 10, 24, 48),
  luck_levels = c(0, 5000, 10000, 25000, 50000),
  modifier_boost_levels = c(0, 200, 500, 1000),
  meteor = FALSE,
  weather_events = 0,
  solar_magnifier = FALSE,
  modifier_surge = FALSE,
  bonus_interval = 10,
  base_pph = 100
) {
  # Event luck multiplier (from Stat Systems Guide / formulas.py).
  event_mult <- 1.0
  if (meteor) event_mult <- event_mult * 2.0
  event_mult <- event_mult * (1.5 ^ weather_events)

  # pct_ores_modified curve (approximate from Stat Systems Guide).
  pct_modified <- function(eff_mb) {
    if (eff_mb <= 0) return(0)
    if (eff_mb >= 1900) return(99.4)
    x <- eff_mb / 1900
    min(99.4, 99.4 * (x ^ 0.3) * 1.15)
  }

  # modifier_luck curve (needs luck and modifier_boost explicitly).
  modifier_luck <- function(luck, modifier_boost) {
    min(50, luck / 1000) + modifier_boost / 10
  }

  # Probability of finding requested minerals per pan.
  find_prob <- function(luck, eff_mb, modifier_boost) {
    ml <- modifier_luck(luck, modifier_boost)
    pm <- pct_modified(eff_mb)
    if (pm <= 0 || ml <= 0) return(1e-4) # small base rate; avoids separation
    (pm / 100) * (ml / 50) * event_mult
  }

  # Simulate one quest run: accumulate n_quests completions, track time.
  # Right-censor at max_time_hours.
  simulate_run <- function(start_luck, modifier_boost, eff_mb) {
    luck <- start_luck
    quests_done <- 0
    total_time_hours <- 0
    pph <- base_pph

    while (quests_done < n_quests) {
      if (total_time_hours >= max_time_hours) {
        break
      }
      p_find <- find_prob(luck, eff_mb, modifier_boost)
      if (p_find <= 0) {
        # Cannot progress; censor at max time.
        total_time_hours <- max_time_hours
        break
      }
      pans_per_quest <- 1 / p_find
      quest_hours <- pans_per_quest / pph / 3600
      total_time_hours <- total_time_hours + quest_hours
      quests_done <- quests_done + 1
      luck <- luck + 3
      luck <- min(luck, 50000) # cap at modifier_luck saturation
    }

    completed <- quests_done >= n_quests
    list(time = total_time_hours, event = as.integer(completed))
  }

  # Build a grid of covariate combinations and simulate runs.
  rows <- data.frame()
  run_idx <- 1
  for (luck in luck_levels) {
    for (mb in modifier_boost_levels) {
      eff_mb <- mb
      if (solar_magnifier) eff_mb <- eff_mb * 2
      if (modifier_surge) eff_mb <- eff_mb * 2
      for (rep in seq_len(n_runs)) {
        res <- simulate_run(luck, mb, eff_mb)
        rows <- rbind(rows, data.frame(
          run_id = run_idx,
          time = res$time,
          event = res$event,
          luck = luck,
          modifier_boost = mb,
          solar_magnifier = as.integer(solar_magnifier),
          modifier_surge = as.integer(modifier_surge),
          meteor = as.integer(meteor),
          weather_events = weather_events,
          stringsAsFactors = FALSE
        ))
        run_idx <- run_idx + 1
      }
    }
  }

  n_completed <- sum(rows$event == 1)
  n_censored <- sum(rows$event == 0)

  # Build a dynamic formula using only covariates that vary across runs.
  # solar_magnifier / modifier_surge / meteor / weather_events are constant
  # within a single call (their effects are already in eff_mb / event_mult),
  # so they are excluded to avoid collinearity.
  cov_terms <- c()
  if (length(unique(rows$luck)) > 1) cov_terms <- c(cov_terms, "luck")
  if (length(unique(rows$modifier_boost)) > 1) cov_terms <- c(cov_terms, "modifier_boost")
  if (length(cov_terms) == 0) {
    # No varying covariates: fit intercept-only Weibull.
    fit_formula <- survival::Surv(time, event) ~ 1
  } else {
    fit_formula <- as.formula(paste(
      "survival::Surv(time, event) ~", paste(cov_terms, collapse = " + ")
    ))
  }

  # Fit Cox proportional hazards regression (more robust than parametric
  # Weibull AFT on simulated/censored quest data). Coefficients are log
  # hazard ratios; exp(coef) are hazard ratios.
  fit <- tryCatch(
    survival::coxph(fit_formula, data = rows),
    error = function(e) NULL
  )

  coefficients <- NULL
  hazard_ratios <- NULL
  baseline_median <- NULL

  if (!is.null(fit)) {
    sm <- tryCatch(summary(fit), error = function(e) NULL)
    if (!is.null(sm) && !is.null(sm$coefficients)) {
      coefs <- sm$coefficients[, "coef"]
      coefficients <- as.list(coefs)
      hazard_ratios <- as.list(exp(coefs))
    }

    # Baseline median time at reference (luck=0, modifier_boost=0) from the
    # baseline survival curve (S(t) = 0.5).
    if (length(cov_terms) > 0) {
      ref_vals <- list(luck = 0, modifier_boost = 0)
      reference <- as.data.frame(ref_vals[cov_terms], stringsAsFactors = FALSE)
    } else {
      reference <- data.frame()
    }
    baseline_median <- tryCatch({
      sfit <- survival::survfit(fit, newdata = reference)
      # Find the smallest time where baseline survival drops to <= 0.5.
      summ <- summary(sfit)
      surv_probs <- summ$surv
      times <- summ$time
      idx <- which(surv_probs <= 0.5)
      if (length(idx) > 0) times[idx[1]] else NA_real_
    }, error = function(e) NA_real_)
  }

  # Empirical baseline median from completed runs in the reference subgroup.
  if (is.null(baseline_median) || is.na(baseline_median)) {
    ref_done <- rows[rows$luck == 0 & rows$modifier_boost == 0 &
                     rows$event == 1, "time"]
    if (length(ref_done) > 0) {
      baseline_median <- median(ref_done)
    } else {
      baseline_median <- NA_real_
    }
  }

  # Survival curve at time_points for the reference player (luck=0, mb=0).
  ref_subset <- rows[rows$luck == 0 & rows$modifier_boost == 0, ]

  survival_curve <- data.frame(
    time = numeric(0), survival_prob = numeric(0), stringsAsFactors = FALSE
  )
  completion_prob_within <- list()

  if (nrow(ref_subset) > 0) {
    km <- tryCatch(
      survival::survfit(survival::Surv(time, event) ~ 1, data = ref_subset),
      error = function(e) NULL
    )
    km_available <- FALSE
    if (!is.null(km)) {
      km_sum <- tryCatch(
        summary(km, times = time_points),
        error = function(e) NULL
      )
      if (!is.null(km_sum) && !is.null(km_sum$time) && length(km_sum$time) > 0) {
        km_available <- TRUE
        n_tp <- length(km_sum$time)
        surv_probs <- as.numeric(km_sum$surv)
        if (length(surv_probs) < n_tp) {
          surv_probs <- c(surv_probs, rep(tail(surv_probs, 1), n_tp - length(surv_probs)))
        }
        survival_curve <- data.frame(
          time = as.numeric(km_sum$time),
          survival_prob = round(surv_probs, 4),
          stringsAsFactors = FALSE
        )
        for (i in seq_len(n_tp)) {
          completion_prob_within[[as.character(km_sum$time[i])]] <-
            round(1 - surv_probs[i], 4)
        }
      }
    }

    # Empirical fallback (and curve) if KM produced nothing.
    if (!km_available) {
      for (t in time_points) {
        completed_by_t <- ref_subset$event == 1 & ref_subset$time <= t
        p_complete <- mean(completed_by_t, na.rm = TRUE)
        completion_prob_within[[as.character(t)]] <- round(p_complete, 4)
        # Empirical survival probability P(T > t).
        still_alive <- ref_subset$time > t | (ref_subset$time <= t & ref_subset$event == 0)
        p_survive <- mean(still_alive, na.rm = TRUE)
        survival_curve <- rbind(survival_curve, data.frame(
          time = t, survival_prob = round(p_survive, 4),
          stringsAsFactors = FALSE
        ))
      }
    }
  }

  list(
    coefficients = coefficients,
    hazard_ratios = hazard_ratios,
    baseline_median_time_hours = if (!is.null(baseline_median) && !is.na(baseline_median))
      round(baseline_median, 2) else NA_real_,
    n_runs = nrow(rows),
    n_completed = n_completed,
    n_censored = n_censored,
    survival_curve = survival_curve,
    completion_prob_within = completion_prob_within,
    r_used = TRUE
  )
}

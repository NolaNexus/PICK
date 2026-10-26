#' Optimize luck cap for Dredge Master quest completion
#'
#' Models quest completion rate as a function of luck cap, accounting for:
#' - modifier_luck curve: min(50, luck / 1000) + modifier_boost / 10
#' - +3 luck permanent boost per completed quest (up to cap)
#' - Bonus rewards every X quests
#' - Diminishing returns on luck beyond 50000 (luck/1000 capped at 50)
#'
#' @param current_luck Numeric player's current luck.
#' @param modifier_boost Numeric player's panel modifier boost.
#' @param solar_magnifier Logical whether Solar Magnifier is active.
#' @param modifier_surge Logical whether Modifier Surge is active.
#' @param bonus_interval Integer quests between bonus rewards.
#' @param n_quests Integer number of quests to simulate.
#' @param luck_caps Numeric vector of luck cap values to evaluate.
#' @return Data frame with optimal luck cap and expected outcomes per cap.
optimize_luck_cap <- function(
  current_luck,
  modifier_boost = 0,
  solar_magnifier = FALSE,
  modifier_surge = FALSE,
  bonus_interval = 10,
  n_quests = 100,
  luck_caps = c(0, 1000, 2500, 5000, 10000, 15000, 20000, 30000, 50000)
) {
  # Effective modifier boost (Job 1: % ores modified)
  eff_mb <- modifier_boost
  if (solar_magnifier) eff_mb <- eff_mb * 2
  if (modifier_surge) eff_mb <- eff_mb * 2

  # modifier_luck: min(50, luck / 1000) + modifier_boost / 10
  modifier_luck <- function(luck) {
    min(50, luck / 1000) + modifier_boost / 10
  }

  # pct_ores_modified curve (approximate from Stat Systems Guide)
  pct_modified <- function(eff_mb) {
    if (eff_mb <= 0) return(0)
    if (eff_mb >= 1900) return(99.4)
    x <- eff_mb / 1900
    min(99.4, 99.4 * (x ^ 0.3) * 1.15)
  }

  # Mineral find probability per pan: combines pct_modified and modifier_luck
  # Higher luck = better modifier odds = better chance of requested modifiers
  find_prob <- function(luck) {
    ml <- modifier_luck(luck)
    pm <- pct_modified(eff_mb)
    # Probability scales with both modifier coverage and luck
    (pm / 100) * (ml / 50)
  }

  # Simulate quest completion for a given luck cap
  simulate_cap <- function(luck_cap) {
    luck <- current_luck
    quests_done <- 0
    total_time_hours <- 0
    bonuses_earned <- 0

    # Base pans per hour (reasonable default for a mid-game build)
    pph <- 100

    while (quests_done < n_quests) {
      # Cap luck at the cap
      luck <- min(luck, luck_cap)

      # Probability of finding requested minerals per pan
      p_find <- find_prob(luck)

      # Expected pans to complete one quest (assume 1 mineral needed per quest)
      # With diminishing returns, very low luck makes quests very slow
      if (p_find <= 0) {
        pans_per_quest <- Inf
      } else {
        pans_per_quest <- 1 / p_find
      }

      # Time for this quest (hours)
      quest_hours <- pans_per_quest / pph / 3600

      total_time_hours <- total_time_hours + quest_hours
      quests_done <- quests_done + 1

      # +3 luck per quest (up to cap)
      luck <- luck + 3

      # Bonus every bonus_interval quests
      if (quests_done %% bonus_interval == 0) {
        bonuses_earned <- bonuses_earned + 1
      }
    }

    list(
      luck_cap = luck_cap,
      quests_done = quests_done,
      total_time_hours = total_time_hours,
      bonuses_earned = bonuses_earned,
      bonuses_per_hour = if (total_time_hours > 0) bonuses_earned / total_time_hours else 0,
      final_luck = min(luck, luck_cap),
      avg_luck = min((current_luck + luck) / 2, luck_cap)
    )
  }

  results <- lapply(luck_caps, simulate_cap)
  df <- do.call(rbind, lapply(results, as.data.frame))

  # Find optimal cap: highest bonuses per hour
  optimal_idx <- which.max(df$bonuses_per_hour)
  df$optimal <- FALSE
  df$optimal[optimal_idx] <- TRUE

  df[order(-df$bonuses_per_hour), ]
}

#' Continuous luck-cap optimization for Dredge Master quest completion
#'
#' Finds the luck cap that maximizes expected bonuses per hour using bounded
#' 1D optimization (Brent's method, derivative-free). The objective
#' (bonuses_per_hour vs luck_cap) is monotonic increasing then flat once luck
#' saturates modifier_luck at 50, so gradient-based methods fail; Brent's
#' method handles this step-like function without derivatives.
#'
#' Also reports the saturation cap: the smallest cap within tolerance of the
#' maximum, which is the actionable recommendation (anything beyond adds no
#' benefit).
#'
#' @param current_luck Numeric player's current luck.
#' @param modifier_boost Numeric player's panel modifier boost.
#' @param solar_magnifier Logical whether Solar Magnifier is active.
#' @param modifier_surge Logical whether Modifier Surge is active.
#' @param bonus_interval Integer quests between bonus rewards.
#' @param n_quests Integer number of quests to simulate.
#' @param lower Numeric lower bound for luck cap search.
#' @param upper Numeric upper bound for luck cap search.
#' @return List with optimal_cap, optimal_bonuses_per_hour, saturation_cap,
#'   lower, upper.
optimize_luck_cap_continuous <- function(
  current_luck,
  modifier_boost = 0,
  solar_magnifier = FALSE,
  modifier_surge = FALSE,
  bonus_interval = 10,
  n_quests = 100,
  lower = 0,
  upper = 100000
) {
  # Effective modifier boost.
  eff_mb <- modifier_boost
  if (solar_magnifier) eff_mb <- eff_mb * 2
  if (modifier_surge) eff_mb <- eff_mb * 2

  # pct_ores_modified curve (approximate from Stat Systems Guide).
  pct_modified <- function(eff_mb) {
    if (eff_mb <= 0) return(0)
    if (eff_mb >= 1900) return(99.4)
    x <- eff_mb / 1900
    min(99.4, 99.4 * (x ^ 0.3) * 1.15)
  }

  # Probability of finding requested minerals per pan at a given luck.
  find_prob <- function(luck) {
    ml <- min(50, luck / 1000) + modifier_boost / 10
    pm <- pct_modified(eff_mb)
    if (pm <= 0 || ml <= 0) return(0)
    (pm / 100) * (ml / 50)
  }

  # Expected bonuses per hour for a single luck cap.
  bonuses_per_hour <- function(luck_cap) {
    luck <- current_luck
    quests_done <- 0
    total_time_hours <- 0
    bonuses_earned <- 0
    pph <- 100

    while (quests_done < n_quests) {
      luck <- min(luck, luck_cap)
      p_find <- find_prob(luck)
      if (p_find <= 0) return(0)
      pans_per_quest <- 1 / p_find
      total_time_hours <- total_time_hours + pans_per_quest / pph / 3600
      quests_done <- quests_done + 1
      luck <- luck + 3
      if (quests_done %% bonus_interval == 0) bonuses_earned <- bonuses_earned + 1
    }

    if (total_time_hours <= 0) return(0)
    bonuses_earned / total_time_hours
  }

  # Brent bounded 1D optimization (minimize negative = maximize).
  obj <- function(cap) -bonuses_per_hour(cap)
  fit <- tryCatch(
    optimize(obj, interval = c(lower, upper), maximum = FALSE),
    error = function(e) list(minimum = lower, objective = obj(lower))
  )
  optimal_cap <- fit$minimum
  optimal_bph <- -fit$objective
  if (!is.finite(optimal_bph)) {
    optimal_cap <- lower
    optimal_bph <- bonuses_per_hour(lower)
  }

  # Saturation point: smallest cap within tolerance of the maximum.
  tol <- 0.01 * max(abs(optimal_bph), 1)
  saturation_cap <- upper
  test_caps <- seq(lower, upper, length.out = 201)
  for (c in test_caps) {
    v <- bonuses_per_hour(c)
    if (v >= optimal_bph - tol) {
      saturation_cap <- c
      break
    }
  }

  list(
    optimal_cap = optimal_cap,
    optimal_bonuses_per_hour = optimal_bph,
    saturation_cap = saturation_cap,
    lower = lower,
    upper = upper
  )
}

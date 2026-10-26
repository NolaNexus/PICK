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

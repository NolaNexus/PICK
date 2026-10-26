#' Score locations for a mineral hunt list
#'
#' Ranks locations by how well they match a player's hunt list of minerals.
#' Scores combine tier-weighted hunt matches, Exotic mineral presence, and
#' raw hunt mineral count.
#'
#' @param loc_names Character vector of location names.
#' @param loc_hunt_counts Integer vector: number of hunt-list minerals at each location.
#' @param loc_hunt_weights Numeric vector: sum of tier weights for hunt minerals at each location.
#' @param loc_exotic_counts Integer vector: number of Exotic-tier minerals at each location.
#' @return Data frame of locations ranked by score descending.
score_hunt_locations <- function(
  loc_names,
  loc_hunt_counts,
  loc_hunt_weights,
  loc_exotic_counts
) {
  n <- length(loc_names)

  # Base score from tier-weighted hunt matches
  base_score <- loc_hunt_weights

  # Exotic bonus: locations with Exotic minerals are valuable for Exotic hunting
  exotic_bonus <- loc_exotic_counts * 5

  # Hunt count bonus: more hunt minerals = more opportunities per pan
  count_bonus <- loc_hunt_counts * 1

  score <- base_score + exotic_bonus + count_bonus

  data.frame(
    name = loc_names,
    score = round(score, 2),
    hunt_count = loc_hunt_counts,
    hunt_weight = round(loc_hunt_weights, 2),
    exotic_count = loc_exotic_counts,
    stringsAsFactors = FALSE
  )[order(-score), ]
}

#' Score locations for Exotic modifier hunting with a player build
#'
#' Ranks locations by probability of yielding Exotic modifier ores, combining
#' location Exotic mineral density with the player's modifier distribution.
#'
#' @param loc_names Character vector of location names.
#' @param loc_exotic_mineral_counts Integer vector: Exotic minerals at each location.
#' @param loc_total_minerals Integer vector: total minerals at each location.
#' @param modifier_names Character vector of modifier names from the fitted distribution.
#' @param modifier_pcts Numeric vector of modifier percentages (0-100 scale).
#' @param player_modifier_boost Numeric: player's effective modifier boost.
#' @return Data frame of locations ranked by Exotic hunting score descending.
score_exotic_locations <- function(
  loc_names,
  loc_exotic_mineral_counts,
  loc_total_minerals,
  modifier_names,
  modifier_pcts,
  player_modifier_boost
) {
  n <- length(loc_names)

  # Look up Exotic modifier probability from the fitted distribution.
  # Default to the base Exotic rarity weight if not found.
  exotic_mod_prob <- 0.08
  exotic_idx <- which(modifier_names == "Exotic")
  if (length(exotic_idx) > 0) {
    exotic_mod_prob <- modifier_pcts[exotic_idx] / 100.0
  }

  # Probability of an Exotic mineral appearing at a location
  location_exotic_rate <- loc_exotic_mineral_counts / pmax(loc_total_minerals, 1)

  # Combined score: location Exotic density × modifier probability
  # Higher modifier boost shifts distribution toward rarer modifiers,
  # which is already reflected in the fitted distribution.
  score <- location_exotic_rate * exotic_mod_prob * 100

  data.frame(
    name = loc_names,
    score = round(score, 4),
    exotic_rate = round(location_exotic_rate, 4),
    exotic_mod_prob = round(exotic_mod_prob, 4),
    stringsAsFactors = FALSE
  )[order(-score), ]
}

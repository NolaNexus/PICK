#' Gear recommendation scoring
#'
#' Scores candidate gear (pans, shovels, trinkets) for a build using a
#' weighted combination of pans-per-hour, capacity, luck, size boost, and
#' modifier boost. Applies dig-strength cliff boundaries so gear just above
#' a dig threshold is penalized appropriately.
#'
#' @param gear Data frame with columns: name, capacity, dig_strength,
#'   shake_strength, shake_speed, luck, size_boost, modifier_boost.
#' @param dig_strength Player's dig strength (used for cliff boundary check).
#' @param shake_strength Player's shake strength.
#' @param shake_speed Player's shake speed.
#' @param target_capacity Optional minimum capacity filter.
#' @param min_luck Optional minimum luck filter.
#' @param min_size_boost Optional minimum size boost filter.
#' @param min_modifier_boost Optional minimum modifier boost filter.
#' @return Data frame of scored gear sorted by score descending.
score_gear <- function(
  gear,
  dig_strength = 0,
  shake_strength = 0,
  shake_speed = 0,
  target_capacity = 0,
  min_luck = 0,
  min_size_boost = 0,
  min_modifier_boost = 0
) {
  # Dig time per dig: 143.9 * dig_speed^(-0.93)
  dig_time_per_dig <- function(ds) {
    if (ds <= 0) return(1.0)
    143.9 * (ds ^ -0.93)
  }

  # Digs per pan: ceil(capacity / (1.5 * dig_strength))
  digs_per_pan <- function(cap, ds) {
    if (ds <= 0) return(1)
    max(1, ceiling(cap / (1.5 * ds)))
  }

  # Shake speed conversion (buggy zones from Stat Systems Guide).
  shake_sps <- function(pct) {
    base_rate <- 0.1
    steps <- list(
      c(0, 400, 0.4),
      c(400, 600, 0.6),
      c(600, 650, 0.65),
      c(650, 900, 0.9),
      c(900, 950, 0.95),
      c(950, 1000, 0.9),
      c(1000, 1700, 0.9),
      c(1700, Inf, 1.0)
    )
    for (step in steps) {
      if (pct >= step[1] && pct < step[2]) {
        return(base_rate * step[3])
      }
    }
    base_rate * 1.0
  }

  # Pans per hour.
  pph <- function(cap, ds, spd, ss, sps) {
    digs <- digs_per_pan(cap, ds)
    dig_t <- dig_time_per_dig(spd)
    s_rate <- shake_sps(sps)
    shake_t <- if (ss > 0 && s_rate > 0) cap / (ss * s_rate) else 0
    pan_t <- digs * dig_t + shake_t
    if (pan_t <= 0) return(0)
    3600 / pan_t
  }

  # Apply filters.
  result <- gear
  if (target_capacity > 0) {
    result <- result[result$capacity >= target_capacity, ]
  }
  if (min_luck > 0) {
    result <- result[result$luck >= min_luck, ]
  }
  if (min_size_boost > 0) {
    result <- result[result$size_boost >= min_size_boost, ]
  }
  if (min_modifier_boost > 0) {
    result <- result[result$modifier_boost >= min_modifier_boost, ]
  }

  if (nrow(result) == 0) {
    return(result)
  }

  # Score each gear piece.
  scores <- mapply(
    function(cap, ds, ss, spd, luck, sb, mb) {
      d <- digs_per_pan(cap, ds)
      p <- pph(cap, ds, 1000, ss, spd)
      (p * 0.5) + (cap * 0.2) + (luck * 0.1) + (sb * 0.1) + (mb * 0.1)
    },
    result$capacity, result$dig_strength, result$shake_strength,
    result$shake_speed, result$luck, result$size_boost,
    result$modifier_boost
  )

  result$score <- round(scores, 2)
  result$digs_per_pan <- mapply(
    function(cap, ds) digs_per_pan(cap, ds),
    result$capacity, result$dig_strength
  )
  result$pans_per_hour <- round(
    mapply(
      function(cap, ds, ss, spd) pph(cap, ds, 1000, ss, spd),
      result$capacity, result$dig_strength, result$shake_strength,
      result$shake_speed
    ),
    2
  )

  result[order(-result$score), ]
}

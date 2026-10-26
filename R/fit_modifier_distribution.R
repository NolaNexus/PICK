#' Fit modifier drop distribution from observed counts
#'
#' Uses a shrinkage prior so rare modifiers observed zero times still get
#' nonzero mass. Applies an effective-MB boost that shifts mass toward rarer
#' modifiers as the player's modifier boost increases.
#'
#' @param counts Named numeric vector of observed drop counts per modifier.
#' @param effective_mb Numeric effective modifier boost.
#' @return Named numeric vector of fitted percentages (0-100 scale).
fit_modifier_distribution <- function(counts, effective_mb) {
  modifier_names <- c(
    "Perfect", "Treasured", "Lunar", "Voidtorn", "Mutated", "Cosmic",
    "Iridescent", "Irradiated", "Crystalline", "Scorching", "Glowing",
    "Pure", "Shiny"
  )

  # Align counts to the canonical modifier order, filling missing with 0.
  counts <- counts[modifier_names]
  counts[is.na(counts)] <- 0

  total <- sum(counts)
  if (total == 0 || length(counts) == 0) {
    return(setNames(rep(0, length(modifier_names)), modifier_names))
  }

  # Shrinkage prior: rare modifiers observed zero times still get mass.
  prior <- 0.5
  smoothed <- (counts + prior) / (total + prior * length(counts))

  # Effective-MB boost: higher MB shifts mass toward rarer modifiers.
  # Rarity weight is inverse of smoothed frequency (rarer = higher weight).
  rarity_weight <- 1 / (smoothed + 0.001)

  boost_factor <- switch(
    as.character(cut(
      effective_mb,
      c(-Inf, 500, 1000, 1900, Inf)
    )),
    "(-Inf,500]" = 1.0,
    "(500,1000]" = 1.5,
    "(1000,1900]" = 2.0,
    "(1900, Inf]" = 3.0,
    1.0
  )

  boosted <- smoothed * (boost_factor ^ pmin(rarity_weight, 5))

  pct <- boosted / sum(boosted) * 100
  setNames(round(pct, 6), modifier_names)
}

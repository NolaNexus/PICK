"""Calculator API endpoints - using service layer implementations."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Item
from app.schemas import (
    BestPanResponse,
    CalculatorBPGRequest,
    CalculatorEVRequest,
    CalculatorMORRequest,
    CalculatorTTGRequest,
    EVResponse,
    ExoticHuntRequest,
    ExoticHuntResponse,
    GearRecommendationRequest,
    GearRecommendationResponse,
    HuntListRequest,
    HuntRecommendationResponse,
    LuckCapOptimizationRequest,
    LuckCapOptimizationResponse,
    ModifierDistributionFitRequest,
    ModifierDistributionFitResponse,
    ModifierOddsResponse,
    MonteCarloEVRequest,
    MonteCarloEVResponse,
    MuseumCalculatorRequest,
    MuseumCalculatorResponse,
    TTGResponse,
)
from app.services.calculators import (
    calculate_best_pan,
    calculate_ev,
    calculate_modifier_odds,
    calculate_museum_optimizer,
    calculate_museum_projection,
    calculate_ttg,
    calculate_unlock_costs,
    calculate_weight_gate,
    effective_modifier_boost,
    modifier_distribution,
)
from app.services.r_stats import (
    fit_modifier_distribution,
    is_available,
    monte_carlo_ev,
    optimize_luck_cap_r,
    score_exotic_locations_r,
    score_gear_r,
    score_hunt_locations_r,
)

router = APIRouter()


@router.post("/ev", response_model=EVResponse, tags=["calculators"])
async def calculate_ev_endpoint(request: CalculatorEVRequest):
    """Expected value per pan for a location."""
    return calculate_ev(
        location_drop_table=request.location_drop_table,
        luck=request.luck,
        modifier_boost=request.modifier_boost,
        quality=request.quality,
        autopan=request.autopan,
        mastered_shovel=request.mastered_shovel,
        solar_magnifier=request.solar_magnifier,
        modifier_surge=request.modifier_surge,
        capacity=request.capacity,
    )


@router.post("/ttg", response_model=TTGResponse, tags=["calculators"])
async def calculate_ttg_endpoint(request: CalculatorTTGRequest):
    """Time to goal calculator."""
    return calculate_ttg(
        goal_value=request.goal_value,
        location_ev_per_pan=request.location_ev_per_pan,
        capacity=request.capacity,
        dig_strength=request.dig_strength,
        dig_speed=request.dig_speed,
        shake_strength=request.shake_strength,
        shake_speed=request.shake_speed,
    )


@router.post("/modifier-odds", response_model=ModifierOddsResponse, tags=["calculators"])
async def calculate_modifier_odds_endpoint(request: CalculatorMORRequest):
    """Calculate modifier odds and distribution."""
    return calculate_modifier_odds(
        panel_modifier_boost=request.panel_modifier_boost,
        solar_magnifier=request.solar_magnifier,
        modifier_surge=request.modifier_surge,
    )


@router.post("/best-pan", response_model=BestPanResponse, tags=["calculators"])
async def calculate_best_pan_endpoint(request: CalculatorBPGRequest):
    """Recommend best pan for given build parameters."""
    return calculate_best_pan(
        pans=request.pans,
        dig_strength=request.dig_strength,
        shake_strength=request.shake_strength,
        shake_speed=request.shake_speed,
        target_capacity=request.target_capacity,
        min_luck=request.min_luck,
        min_size_boost=request.min_size_boost,
        min_modifier_boost=request.min_modifier_boost,
    )


@router.post("/museum", response_model=MuseumCalculatorResponse, tags=["calculators"])
async def calculate_museum_endpoint(request: MuseumCalculatorRequest):
    """Museum display optimizer and stat calculator.

    Modes:
    - optimize: Find best ore assignment for target stats
    - project: Calculate stats from current slot assignments
    - weight_gate: Check which ores meet min_kg requirements
    - unlock_cost: Calculate money/shards to unlock all displays
    """
    if request.mode == "optimize":
        result = calculate_museum_optimizer(
            available_ores=[ore.model_dump() for ore in request.available_ores],
            unlocked_displays=request.unlocked_displays,
            target_stats=request.target_stats,
            size_boost=request.size_boost,
        )
    elif request.mode == "project":
        # For projection, we need slot assignments from available_ores
        slot_assignments = [
            {
                "rarity": ore.rarity,
                "slot_index": i + 1,
                "ore_name": ore.name,
                "kg": ore.kg,
                "modifier": ore.modifier
            }
            for i, ore in enumerate(request.available_ores)
        ]
        total_stats = calculate_museum_projection(
            slot_assignments=slot_assignments,
            size_boost=request.size_boost,
        )
        result = {
            "slot_recommendations": [],
            "total_stats": total_stats,
            "by_rarity": {},
            "unlock_costs": None,
            "weight_gate_info": None
        }
    elif request.mode == "weight_gate":
        weight_info = calculate_weight_gate(
            available_ores=[ore.model_dump() for ore in request.available_ores],
            size_boost=request.size_boost,
        )
        result = {
            "slot_recommendations": [],
            "total_stats": {},
            "by_rarity": {},
            "unlock_costs": None,
            "weight_gate_info": weight_info
        }
    elif request.mode == "unlock_cost":
        unlock_info = calculate_unlock_costs(request.unlocked_displays)
        result = {
            "slot_recommendations": [],
            "total_stats": {},
            "by_rarity": {},
            "unlock_costs": unlock_info,
            "weight_gate_info": None
        }
    else:
        result = {
            "slot_recommendations": [],
            "total_stats": {},
            "by_rarity": {},
            "unlock_costs": None,
            "weight_gate_info": None
        }

    return result


@router.post(
    "/stats/modifier-distribution",
    response_model=ModifierDistributionFitResponse,
    tags=["calculators"],
)
async def fit_modifier_distribution_endpoint(
    request: ModifierDistributionFitRequest,
):
    """Fit a modifier drop distribution from observed counts using R.

    Falls back to the pure-Python approximation when R/rpy2 is not
    available.
    """
    fitted = fit_modifier_distribution(
        request.observed_counts,
        request.effective_mb,
    )
    return {
        "modifier_distribution": fitted,
        "r_used": is_available(),
        "effective_mb": request.effective_mb,
    }


@router.post(
    "/stats/monte-carlo-ev",
    response_model=MonteCarloEVResponse,
    tags=["calculators"],
)
async def monte_carlo_ev_endpoint(request: MonteCarloEVRequest):
    """Monte Carlo simulation of EV per hour using R.

    Returns the mean and 5th/95th percentile EV per hour. Falls back to
    a deterministic point estimate when R/rpy2 is not available.
    """
    result = monte_carlo_ev(
        samples=request.samples,
        ev_per_pan_mean=request.ev_per_pan_mean,
        ev_per_pan_sd=request.ev_per_pan_sd,
        pph_mean=request.pph_mean,
        pph_sd=request.pph_sd,
    )
    return {
        "mean": result["mean"],
        "p05": result["p05"],
        "p95": result["p95"],
        "r_used": is_available(),
    }


@router.post(
    "/stats/gear-recommendations",
    response_model=GearRecommendationResponse,
    tags=["calculators"],
)
async def gear_recommendations_endpoint(request: GearRecommendationRequest):
    """Score and rank gear using R's recommendation model.

    Falls back to an empty list when R/rpy2 is not available.
    """
    gear = [item.model_dump() for item in request.gear]
    recommendations = score_gear_r(
        gear=gear,
        dig_strength=request.dig_strength,
        shake_strength=request.shake_strength,
        shake_speed=request.shake_speed,
        target_capacity=request.target_capacity,
        min_luck=request.min_luck,
        min_size_boost=request.min_size_boost,
        min_modifier_boost=request.min_modifier_boost,
    )
    return {
        "recommendations": recommendations,
        "r_used": is_available(),
    }


@router.post(
    "/stats/hunt-locations",
    response_model=HuntRecommendationResponse,
    tags=["calculators"],
)
async def hunt_locations_endpoint(
    request: HuntListRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Recommend locations for a mineral hunt list.

    Scores each location by how many hunt-list minerals it has, weighted by
    mineral tier (Exotic > Mythic > ... > Common). Locations with Exotic-tier
    minerals get a bonus for Exotic hunting potential.
    """
    # Fetch all locations and minerals from the database
    loc_result = await db.execute(select(Item).where(Item.type == "location"))
    locations = loc_result.scalars().all()

    min_result = await db.execute(select(Item).where(Item.type == "mineral"))
    minerals = min_result.scalars().all()

    # Build mineral lookup: name -> {tier, value}
    mineral_lookup = {}
    for m in minerals:
        mineral_lookup[m.name] = {
            "tier": m.data.get("tier", "Common") if m.data else "Common",
            "value": m.data.get("value", 0) if m.data else 0,
        }

    # Tier weights for scoring (Exotic is most valuable)
    tier_weights_map = {
        "Common": 1,
        "Uncommon": 2,
        "Rare": 4,
        "Epic": 8,
        "Legendary": 16,
        "Mythic": 32,
        "Exotic": 64,
    }

    hunt_set = set(request.minerals)

    loc_names = []
    loc_hunt_counts = []
    loc_hunt_weights = []
    loc_exotic_counts = []

    for loc in locations:
        loc_data = loc.data or {}
        loc_minerals = loc_data.get("minerals", [])

        hunt_count = 0
        hunt_weight = 0.0
        exotic_count = 0

        for mineral_name in loc_minerals:
            if mineral_name in hunt_set:
                hunt_count += 1
                m_info = mineral_lookup.get(mineral_name, {})
                tier = m_info.get("tier", "Common")
                hunt_weight += tier_weights_map.get(tier, 1)

            m_info = mineral_lookup.get(mineral_name, {})
            if m_info.get("tier") == "Exotic":
                exotic_count += 1

        loc_names.append(loc.name)
        loc_hunt_counts.append(hunt_count)
        loc_hunt_weights.append(hunt_weight)
        loc_exotic_counts.append(exotic_count)

    recommendations = score_hunt_locations_r(
        loc_names=loc_names,
        loc_hunt_counts=loc_hunt_counts,
        loc_hunt_weights=loc_hunt_weights,
        loc_exotic_counts=loc_exotic_counts,
    )

    return {
        "recommendations": recommendations,
        "r_used": is_available(),
    }


@router.post(
    "/stats/exotic-locations",
    response_model=ExoticHuntResponse,
    tags=["calculators"],
)
async def exotic_locations_endpoint(
    request: ExoticHuntRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Recommend locations for Exotic modifier hunting.

    Scores each location by its Exotic mineral density combined with the
    player's modifier distribution (fitted via R when available). Higher
    modifier boost shifts the distribution toward rarer modifiers, improving
    Exotic modifier odds.
    """
    # Fetch all locations and minerals from the database
    loc_result = await db.execute(select(Item).where(Item.type == "location"))
    locations = loc_result.scalars().all()

    min_result = await db.execute(select(Item).where(Item.type == "mineral"))
    minerals = min_result.scalars().all()

    # Build mineral lookup: name -> tier
    mineral_lookup = {}
    for m in minerals:
        mineral_lookup[m.name] = m.data.get("tier", "Common") if m.data else "Common"

    # Calculate player's effective modifier boost (Job 1: % ores modified)
    eff_mb = effective_modifier_boost(
        request.modifier_boost,
        solar_magnifier=request.solar_magnifier,
        modifier_surge=request.modifier_surge,
        for_which_modifier=False,
    )

    # Get fitted modifier distribution (R when available, Python fallback)
    mod_dist = modifier_distribution(
        effective_mb=eff_mb,
        observed_counts=None,  # No observed counts, use the model approximation
    )

    loc_names = []
    loc_exotic_counts = []
    loc_total_counts = []

    for loc in locations:
        loc_data = loc.data or {}
        loc_minerals = loc_data.get("minerals", [])

        exotic_count = 0
        for mineral_name in loc_minerals:
            if mineral_lookup.get(mineral_name) == "Exotic":
                exotic_count += 1

        loc_names.append(loc.name)
        loc_exotic_counts.append(exotic_count)
        loc_total_counts.append(len(loc_minerals))

    recommendations = score_exotic_locations_r(
        loc_names=loc_names,
        loc_exotic_mineral_counts=loc_exotic_counts,
        loc_total_minerals=loc_total_counts,
        modifier_distribution=mod_dist,
        player_modifier_boost=eff_mb,
    )

    return {
        "recommendations": recommendations,
        "r_used": is_available(),
    }


@router.post(
    "/stats/optimize-luck-cap",
    response_model=LuckCapOptimizationResponse,
    tags=["calculators"],
)
async def optimize_luck_cap_endpoint(request: LuckCapOptimizationRequest):
    """Optimize the luck cap for Dredge Master quest completion.

    Models quest completion rate as a function of luck cap, accounting for
    the modifier_luck curve, +3 luck per completed quest, and bonus rewards
    every X quests. Returns results for each evaluated cap with an optimal
    flag on the best-performing cap.
    """
    results = optimize_luck_cap_r(
        current_luck=request.current_luck,
        modifier_boost=request.modifier_boost,
        solar_magnifier=request.solar_magnifier,
        modifier_surge=request.modifier_surge,
        bonus_interval=request.bonus_interval,
        n_quests=request.n_quests,
        luck_caps=request.luck_caps,
    )

    if not results:
        # Fallback without R: return a simple deterministic result
        return {
            "recommendations": [
                {
                    "luck_cap": request.current_luck,
                    "quests_done": request.n_quests,
                    "total_time_hours": 0.0,
                    "bonuses_earned": request.n_quests // request.bonus_interval,
                    "bonuses_per_hour": 0.0,
                    "final_luck": request.current_luck + request.n_quests * 3,
                    "avg_luck": request.current_luck + (request.n_quests * 3) / 2,
                    "optimal": True,
                }
            ],
            "optimal_cap": request.current_luck,
            "r_used": False,
        }

    optimal = max(results, key=lambda r: r.get("bonuses_per_hour", 0))
    return {
        "recommendations": results,
        "optimal_cap": optimal.get("luck_cap", request.current_luck),
        "r_used": is_available(),
    }

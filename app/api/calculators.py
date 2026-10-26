"""Calculator API endpoints - using service layer implementations."""

from fastapi import APIRouter

from app.schemas import (
    BestPanResponse,
    CalculatorBPGRequest,
    CalculatorEVRequest,
    CalculatorMORRequest,
    CalculatorTTGRequest,
    EVResponse,
    ModifierOddsResponse,
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

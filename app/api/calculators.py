"""Calculator API endpoints - using service layer implementations."""

from fastapi import APIRouter

from app.schemas import (
    CalculatorBPGRequest,
    CalculatorEVRequest,
    CalculatorMORRequest,
    CalculatorTTGRequest,
)
from app.services.calculators import (
    calculate_best_pan,
    calculate_ev,
    calculate_modifier_odds,
    calculate_ttg,
)

router = APIRouter()


@router.post("/ev", tags=["calculators"])
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
    )


@router.post("/ttg", tags=["calculators"])
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


@router.post("/modifier-odds", tags=["calculators"])
async def calculate_modifier_odds_endpoint(request: CalculatorMORRequest):
    """Calculate modifier odds and distribution."""
    return calculate_modifier_odds(
        panel_modifier_boost=request.panel_modifier_boost,
        solar_magnifier=request.solar_magnifier,
        modifier_surge=request.modifier_surge,
    )


@router.post("/best-pan", tags=["calculators"])
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

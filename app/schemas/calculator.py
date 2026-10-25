"""Pydantic schemas for calculator API requests."""

from pydantic import BaseModel


class ItemFilter(BaseModel):
    type: str | None = None
    search: str | None = None
    page: int = 1
    size: int = 20


class CalculatorEVRequest(BaseModel):
    # Location-specific drop table (required for accurate EV)
    # List of: {"name": str, "base_price": float, "base_weight": float, "rarity": str}
    location_drop_table: list[dict] = []

    # Panel stats
    luck: float = 0.0
    modifier_boost: float = 0.0
    capacity: float = 0.0  # Used for items_per_pan calculation

    # Quality settings
    quality: float = 1.0
    autopan: bool = False
    mastered_shovel: bool = False

    # Event boosts
    solar_magnifier: bool = False
    modifier_surge: bool = False


class CalculatorTTGRequest(BaseModel):
    goal_value: float
    location_ev_per_pan: float
    capacity: float
    dig_strength: float
    dig_speed: float
    shake_strength: float
    shake_speed: float


class CalculatorMORRequest(BaseModel):
    panel_modifier_boost: float
    solar_magnifier: bool = False
    modifier_surge: bool = False


class CalculatorBPGRequest(BaseModel):
    # Available pans to evaluate (list of pan objects with data fields)
    pans: list[dict]

    # Build parameters
    dig_strength: float
    shake_strength: float
    shake_speed: float

    # Filters
    target_capacity: float = 0
    min_luck: float = 0
    min_size_boost: float = 0
    min_modifier_boost: float = 0

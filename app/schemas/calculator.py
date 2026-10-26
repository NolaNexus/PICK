"""Pydantic schemas for calculator API requests and responses."""

from typing import Any

from pydantic import BaseModel, Field


class ItemFilter(BaseModel):
    type: str | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class CalculatorEVRequest(BaseModel):
    # Location-specific drop table (required for accurate EV)
    # List of: {"name": str, "base_price": float, "base_weight": float, "rarity": str}
    location_drop_table: list[dict] = Field(default_factory=list)

    # Panel stats
    luck: float = Field(default=0.0, ge=0)
    modifier_boost: float = Field(default=0.0, ge=0)
    capacity: float = Field(default=0.0, ge=0)

    # Quality settings
    quality: float = Field(default=1.0, ge=0, le=1)
    autopan: bool = False
    mastered_shovel: bool = False

    # Event boosts
    solar_magnifier: bool = False
    modifier_surge: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "location_drop_table": [
                    {"name": "Gold Ore", "base_price": 100, "base_weight": 1.0, "rarity": "common"},
                    {"name": "Diamond", "base_price": 5000, "base_weight": 0.01, "rarity": "legendary"}
                ],
                "luck": 5000,
                "modifier_boost": 200,
                "capacity": 100,
                "quality": 1.0,
                "autopan": False,
                "mastered_shovel": True,
                "solar_magnifier": False,
                "modifier_surge": False
            }
        }
    }


class CalculatorTTGRequest(BaseModel):
    goal_value: float = Field(gt=0)
    location_ev_per_pan: float = Field(ge=0)
    capacity: float = Field(gt=0)
    dig_strength: float = Field(gt=0)
    dig_speed: float = Field(gt=0)
    shake_strength: float = Field(gt=0)
    shake_speed: float = Field(ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "goal_value": 1000000,
                "location_ev_per_pan": 5000,
                "capacity": 100,
                "dig_strength": 50,
                "dig_speed": 100,
                "shake_strength": 50,
                "shake_speed": 500
            }
        }
    }


class CalculatorMORRequest(BaseModel):
    panel_modifier_boost: float = Field(ge=0)
    solar_magnifier: bool = False
    modifier_surge: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "panel_modifier_boost": 500,
                "solar_magnifier": True,
                "modifier_surge": False
            }
        }
    }


class CalculatorBPGRequest(BaseModel):
    # Available pans to evaluate (list of pan objects with data fields)
    pans: list[dict] = Field(min_length=1)

    # Build parameters
    dig_strength: float = Field(gt=0)
    shake_strength: float = Field(gt=0)
    shake_speed: float = Field(ge=0)

    # Filters
    target_capacity: float = Field(default=0, ge=0)
    min_luck: float = Field(default=0, ge=0)
    min_size_boost: float = Field(default=0, ge=0)
    min_modifier_boost: float = Field(default=0, ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "pans": [
                    {"id": 1, "name": "Steel Pan", "slug": "steel-pan", "type": "pan", "data": {"capacity": 50, "dig_strength": 10, "shake_strength": 10, "shake_speed": 100, "luck": 0, "size_boost": 0, "modifier_boost": 0}, "image_url": ""}
                ],
                "dig_strength": 50,
                "shake_strength": 50,
                "shake_speed": 500,
                "target_capacity": 80,
                "min_luck": 100,
                "min_size_boost": 0,
                "min_modifier_boost": 0
            }
        }
    }


# --- Response Models ---

class ModifierDistributionItem(BaseModel):
    modifier: str
    percentage: float = Field(ge=0, le=100)


class EVResponse(BaseModel):
    ev_per_pan: float = Field(ge=0)
    items_per_pan: float = Field(ge=0)
    quality_multiplier: float = Field(ge=0, le=1)
    effective_modifier_boost: float = Field(ge=0)
    pct_modified: float = Field(ge=0, le=100)
    modifier_distribution: dict[str, float]

    model_config = {
        "json_schema_extra": {
            "example": {
                "ev_per_pan": 5432.10,
                "items_per_pan": 10.8,
                "quality_multiplier": 1.0,
                "effective_modifier_boost": 400.0,
                "pct_modified": 45.2,
                "modifier_distribution": {
                    "Perfect": 0.02,
                    "Treasured": 0.1,
                    "Lunar": 0.5,
                    "Voidtorn": 1.0,
                    "Mutated": 3.0,
                    "Cosmic": 10.0,
                    "Iridescent": 30.0,
                    "Irradiated": 80.0,
                    "Crystalline": 150.0,
                    "Scorching": 250.0,
                    "Glowing": 400.0,
                    "Pure": 550.0,
                    "Shiny": 700.0
                }
            }
        }
    }


class TTGResponse(BaseModel):
    hours_to_goal: float = Field(ge=0)
    pans_per_hour: float = Field(ge=0)
    ev_per_hour: float = Field(ge=0)
    ev_per_pan: float = Field(ge=0)
    digs_per_pan: int = Field(ge=1)
    dig_time_per_dig: float = Field(ge=0)
    shake_time: float = Field(ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "hours_to_goal": 45.5,
                "pans_per_hour": 120.5,
                "ev_per_hour": 602500.0,
                "ev_per_pan": 5000.0,
                "digs_per_pan": 3,
                "dig_time_per_dig": 1.25,
                "shake_time": 2.5
            }
        }
    }


class ModifierOddsResponse(BaseModel):
    effective_modifier_boost_job1: float = Field(ge=0)
    effective_modifier_boost_job2: float = Field(ge=0)
    pct_ores_modified: float = Field(ge=0, le=100)
    modifier_distribution: dict[str, float]
    note: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "effective_modifier_boost_job1": 2000.0,
                "effective_modifier_boost_job2": 1000.0,
                "pct_ores_modified": 99.4,
                "modifier_distribution": {
                    "Perfect": 0.5,
                    "Treasured": 2.0,
                    "Lunar": 5.0,
                    "Voidtorn": 10.0,
                    "Mutated": 30.0,
                    "Cosmic": 100.0,
                    "Iridescent": 300.0,
                    "Irradiated": 800.0,
                    "Crystalline": 1500.0,
                    "Scorching": 2500.0,
                    "Glowing": 4000.0,
                    "Pure": 5500.0,
                    "Shiny": 7000.0
                },
                "note": "Solar Magnifier doubles for Job 1 only. Modifier Surge doubles for both jobs."
            }
        }
    }


class PanRecommendation(BaseModel):
    pan: dict[str, Any]
    score: float
    capacity: float
    digs_per_pan: int
    pans_per_hour: float
    luck: float
    size_boost: float
    modifier_boost: float


class BestPanResponse(BaseModel):
    recommendations: list[PanRecommendation]
    criteria: dict[str, float]

    model_config = {
        "json_schema_extra": {
            "example": {
                "recommendations": [
                    {
                        "pan": {"id": 1, "name": "Golden Pan", "slug": "golden-pan", "type": "pan", "data": {"capacity": 100, "dig_strength": 20, "shake_strength": 20, "shake_speed": 600, "luck": 500, "size_boost": 50, "modifier_boost": 100}, "image_url": ""},
                        "score": 85.5,
                        "capacity": 100,
                        "digs_per_pan": 3,
                        "pans_per_hour": 150.0,
                        "luck": 500,
                        "size_boost": 50,
                        "modifier_boost": 100
                    }
                ],
                "criteria": {
                    "target_capacity": 80,
                    "dig_strength": 50,
                    "shake_strength": 50,
                    "shake_speed": 500
                }
            }
        }
    }


# =============================================================================
# MUSEUM CALCULATOR SCHEMAS
# =============================================================================

class AvailableOre(BaseModel):
    """An ore the player has available for museum displays."""
    name: str
    rarity: str
    kg: float = Field(ge=0)
    modifier: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Gold",
                "rarity": "Common",
                "kg": 50.0,
                "modifier": "Shiny"
            }
        }
    }


class MuseumCalculatorRequest(BaseModel):
    """Request for museum calculator."""
    # Available ores the player has
    available_ores: list[AvailableOre] = Field(default_factory=list)

    # Currently unlocked displays per rarity
    unlocked_displays: dict[str, int] = Field(default_factory=dict)

    # Target stats to optimize for (weights)
    target_stats: dict[str, float] = Field(default_factory=dict)

    # Player's Size Boost (for weight gate calculation)
    size_boost: float = Field(default=0.0, ge=0)

    # Mode: "optimize" | "project" | "weight_gate" | "unlock_cost"
    mode: str = Field(default="optimize", pattern="^(optimize|project|weight_gate|unlock_cost)$")

    model_config = {
        "json_schema_extra": {
            "example": {
                "available_ores": [
                    {"name": "Gold", "rarity": "Common", "kg": 50.0, "modifier": "Shiny"},
                    {"name": "Diamond", "rarity": "Legendary", "kg": 25.0, "modifier": "Perfect"},
                    {"name": "Aetherite", "rarity": "Legendary", "kg": 30.0, "modifier": None}
                ],
                "unlocked_displays": {
                    "Common": 3,
                    "Uncommon": 2,
                    "Rare": 1,
                    "Epic": 1,
                    "Legendary": 2,
                    "Mythic": 1,
                    "Exotic": 0
                },
                "target_stats": {
                    "Luck": 1.0,
                    "Sell Boost": 0.5,
                    "Dig Speed": 0.3
                },
                "size_boost": 1000.0,
                "mode": "optimize"
            }
        }
    }


class SlotRecommendation(BaseModel):
    """Recommendation for a single museum display slot."""
    slot_id: str
    rarity: str
    slot_index: int
    recommended_ore: str
    ore_kg: float
    modifier: str | None = None
    effective_boost: dict[str, float]
    score: float


class RarityBreakdown(BaseModel):
    """Breakdown of stats per rarity."""
    slots_filled: int
    total_slots: int
    total_boost: dict[str, float]
    ores_used: list[str]


class UnlockCostInfo(BaseModel):
    """Museum unlock cost information."""
    next_unlock: dict[str, Any] | None = None
    total_remaining_money: int
    total_remaining_shards: int


class WeightGateInfo(BaseModel):
    """Weight gate check result for an ore."""
    ore_name: str
    rarity: str
    min_kg: int
    current_kg: float
    effective_kg: float
    meets_requirement: bool


class MuseumCalculatorResponse(BaseModel):
    """Response from museum calculator."""
    # Per-slot recommendations
    slot_recommendations: list[SlotRecommendation]

    # Total projected stats
    total_stats: dict[str, float]

    # Per-rarity breakdown
    by_rarity: dict[str, RarityBreakdown]

    # Unlock costs if applicable
    unlock_costs: UnlockCostInfo | None = None

    # Weight gate info
    weight_gate_info: list[WeightGateInfo] | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "slot_recommendations": [
                    {
                        "slot_id": "common-1",
                        "rarity": "Common",
                        "slot_index": 1,
                        "recommended_ore": "Gold",
                        "ore_kg": 50.0,
                        "modifier": "Shiny",
                        "effective_boost": {"Sell Boost": 0.05, "Shake Strength": 0.0037},
                        "score": 0.0287
                    }
                ],
                "total_stats": {
                    "Luck": 0.85,
                    "Sell Boost": 0.42,
                    "Dig Speed": 0.31,
                    "Shake Strength": 0.12
                },
                "by_rarity": {
                    "Common": {
                        "slots_filled": 3,
                        "total_slots": 3,
                        "total_boost": {"Sell Boost": 0.15, "Shake Strength": 0.011},
                        "ores_used": ["Gold", "Copper", "Silver"]
                    }
                },
                "unlock_costs": {
                    "next_unlock": {"rarity": "Mythic", "money": 10000000000, "shards": 5000},
                    "total_remaining_money": 11111000000,
                    "total_remaining_shards": 23050
                },
                "weight_gate_info": [
                    {"ore_name": "Gold", "rarity": "Common", "min_kg": 40, "current_kg": 50.0, "effective_kg": 550.0, "meets_requirement": True}
                ]
            }
        }
    }


# =============================================================================
# R-POWERED STATISTICAL SCHEMAS
# =============================================================================

class ModifierDistributionFitRequest(BaseModel):
    """Request to fit a modifier drop distribution from observed data.

    observed_counts: Mapping of modifier name -> observed drop count from
    scraped wiki data or player tracking.
    effective_mb: Player's effective modifier boost.
    """
    observed_counts: dict[str, int] = Field(default_factory=dict)
    effective_mb: float = Field(default=0.0, ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "observed_counts": {
                    "Shiny": 100,
                    "Pure": 50,
                    "Glowing": 20,
                    "Iridescent": 5,
                    "Perfect": 1,
                },
                "effective_mb": 500,
            }
        }
    }


class ModifierDistributionFitResponse(BaseModel):
    """Fitted modifier distribution percentages (0-100 scale)."""
    modifier_distribution: dict[str, float]
    r_used: bool
    effective_mb: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "modifier_distribution": {
                    "Perfect": 0.02,
                    "Treasured": 0.1,
                    "Lunar": 0.5,
                    "Voidtorn": 1.0,
                    "Mutated": 3.0,
                    "Cosmic": 10.0,
                    "Iridescent": 30.0,
                    "Irradiated": 80.0,
                    "Crystalline": 150.0,
                    "Scorching": 250.0,
                    "Glowing": 400.0,
                    "Pure": 550.0,
                    "Shiny": 700.0,
                },
                "r_used": False,
                "effective_mb": 500,
            }
        }
    }


class MonteCarloEVRequest(BaseModel):
    """Request for Monte Carlo EV per hour simulation.

    samples: Number of simulation draws.
    ev_per_pan_mean: Mean expected value per pan.
    ev_per_pan_sd: Standard deviation of EV per pan.
    pph_mean: Mean pans per hour.
    pph_sd: Standard deviation of pans per hour.
    """
    samples: int = Field(default=10000, ge=1, le=1000000)
    ev_per_pan_mean: float = Field(default=0.0, ge=0)
    ev_per_pan_sd: float = Field(default=0.0, ge=0)
    pph_mean: float = Field(default=0.0, ge=0)
    pph_sd: float = Field(default=0.0, ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "samples": 10000,
                "ev_per_pan_mean": 5000.0,
                "ev_per_pan_sd": 500.0,
                "pph_mean": 120.0,
                "pph_sd": 10.0,
            }
        }
    }


class MonteCarloEVResponse(BaseModel):
    """Monte Carlo EV per hour simulation results."""
    mean: float
    p05: float
    p95: float
    r_used: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "mean": 600000.0,
                "p05": 540000.0,
                "p95": 660000.0,
                "r_used": False,
            }
        }
    }


class GearItemInput(BaseModel):
    """A single piece of gear for recommendation scoring."""
    name: str
    capacity: float = Field(default=0, ge=0)
    dig_strength: float = Field(default=0, ge=0)
    shake_strength: float = Field(default=0, ge=0)
    shake_speed: float = Field(default=0, ge=0)
    luck: float = Field(default=0, ge=0)
    size_boost: float = Field(default=0, ge=0)
    modifier_boost: float = Field(default=0, ge=0)


class GearRecommendationRequest(BaseModel):
    """Request to score and rank gear using R's recommendation model.

    gear: List of gear items to evaluate.
    dig_strength/shake_strength/shake_speed: Player's build stats.
    target_capacity/min_luck/min_size_boost/min_modifier_boost: Filters.
    """
    gear: list[GearItemInput] = Field(default_factory=list)
    dig_strength: float = Field(default=0, ge=0)
    shake_strength: float = Field(default=0, ge=0)
    shake_speed: float = Field(default=0, ge=0)
    target_capacity: float = Field(default=0, ge=0)
    min_luck: float = Field(default=0, ge=0)
    min_size_boost: float = Field(default=0, ge=0)
    min_modifier_boost: float = Field(default=0, ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "gear": [
                    {
                        "name": "Golden Pan",
                        "capacity": 100,
                        "dig_strength": 20,
                        "shake_strength": 20,
                        "shake_speed": 600,
                        "luck": 500,
                        "size_boost": 50,
                        "modifier_boost": 100,
                    }
                ],
                "dig_strength": 50,
                "shake_strength": 50,
                "shake_speed": 500,
                "target_capacity": 80,
                "min_luck": 100,
                "min_size_boost": 0,
                "min_modifier_boost": 0,
            }
        }
    }


class GearRecommendationResponse(BaseModel):
    """Scored and ranked gear recommendations."""
    recommendations: list[dict]
    r_used: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "recommendations": [
                    {
                        "name": "Golden Pan",
                        "score": 85.5,
                        "capacity": 100,
                        "digs_per_pan": 3,
                        "pans_per_hour": 150.0,
                    }
                ],
                "r_used": False,
            }
        }
    }


# =============================================================================
# LOCATION RECOMMENDATION SCHEMAS
# =============================================================================

class HuntListRequest(BaseModel):
    """Request for location recommendations based on a mineral hunt list.

    minerals: List of mineral names the player is hunting for.
    The endpoint scores each location by how many hunt-list minerals it has,
    weighted by mineral tier (Exotic > Mythic > ... > Common).
    """
    minerals: list[str] = Field(default_factory=list, min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "minerals": ["Diamond", "Gold", "Aetherite", "Void Crystal"]
            }
        }
    }


class HuntLocationResult(BaseModel):
    """Score and hunt details for a single location."""
    name: str
    score: float
    hunt_count: int
    hunt_weight: float
    exotic_count: int


class HuntRecommendationResponse(BaseModel):
    """Location recommendations for a mineral hunt list."""
    recommendations: list[HuntLocationResult]
    r_used: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "recommendations": [
                    {
                        "name": "Crystal Caves",
                        "score": 75.0,
                        "hunt_count": 4,
                        "hunt_weight": 64.0,
                        "exotic_count": 2,
                    }
                ],
                "r_used": False,
            }
        }
    }


class ExoticHuntRequest(BaseModel):
    """Request for Exotic hunting location recommendations.

    modifier_boost: Player's panel modifier boost.
    luck: Player's panel luck.
    solar_magnifier: Whether Solar Magnifier is active.
    modifier_surge: Whether Modifier Surge is active.
    """
    modifier_boost: float = Field(default=0.0, ge=0)
    luck: float = Field(default=0.0, ge=0)
    solar_magnifier: bool = False
    modifier_surge: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "modifier_boost": 500,
                "luck": 10000,
                "solar_magnifier": True,
                "modifier_surge": False,
            }
        }
    }


class ExoticLocationResult(BaseModel):
    """Score and Exotic hunting details for a single location."""
    name: str
    score: float
    exotic_rate: float
    exotic_mod_prob: float


class ExoticHuntResponse(BaseModel):
    """Location recommendations for Exotic modifier hunting."""
    recommendations: list[ExoticLocationResult]
    r_used: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "recommendations": [
                    {
                        "name": "Void Depths",
                        "score": 12.5,
                        "exotic_rate": 0.15,
                        "exotic_mod_prob": 0.083,
                    }
                ],
                "r_used": False,
            }
        }
    }


# =============================================================================
# LUCK CAP OPTIMIZATION SCHEMAS
# =============================================================================

class LuckCapOptimizationRequest(BaseModel):
    """Request to optimize the luck cap for Dredge Master quest completion.

    current_luck: Player's current luck.
    modifier_boost: Player's panel modifier boost.
    solar_magnifier: Whether Solar Magnifier is active.
    modifier_surge: Whether Modifier Surge is active.
    bonus_interval: Quests between bonus rewards (default 10).
    n_quests: Number of quests to simulate (default 100).
    luck_caps: List of luck cap values to evaluate. Defaults to a standard
        range if not provided.
    """
    current_luck: float = Field(default=0.0, ge=0)
    modifier_boost: float = Field(default=0.0, ge=0)
    solar_magnifier: bool = False
    modifier_surge: bool = False
    bonus_interval: int = Field(default=10, ge=1)
    n_quests: int = Field(default=100, ge=1, le=10000)
    luck_caps: list[float] | None = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_luck": 5000,
                "modifier_boost": 200,
                "solar_magnifier": False,
                "modifier_surge": False,
                "bonus_interval": 10,
                "n_quests": 100,
                "luck_caps": [0, 5000, 10000, 20000, 50000],
            }
        }
    }


class LuckCapResult(BaseModel):
    """Result for a single luck cap evaluation."""
    luck_cap: float
    quests_done: int
    total_time_hours: float
    bonuses_earned: int
    bonuses_per_hour: float
    final_luck: float
    avg_luck: float
    optimal: bool


class LuckCapOptimizationResponse(BaseModel):
    """Luck cap optimization results."""
    recommendations: list[LuckCapResult]
    optimal_cap: float
    r_used: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "recommendations": [
                    {
                        "luck_cap": 10000,
                        "quests_done": 100,
                        "total_time_hours": 45.5,
                        "bonuses_earned": 10,
                        "bonuses_per_hour": 0.22,
                        "final_luck": 8300,
                        "avg_luck": 6650,
                        "optimal": True,
                    }
                ],
                "optimal_cap": 10000,
                "r_used": False,
            }
        }
    }




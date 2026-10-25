# Museum Calculator Implementation Plan

## Overview
Add a Museum Calculator endpoint that helps players compare their available ores against their current museum display setup. The museum has 18 display slots across 7 rarities, each accepting ores of matching rarity with weight gates and modifier riders. The cap (max_boost) is already in the parsed data.

## Data Structures (from scraper)

### Displays (7 rarities, 18 total slots)
| Rarity | Free | Locked (Money) | Locked (Shards) | Total |
|--------|------|----------------|-----------------|-------|
| Common | 1 | $1M | 400 | 3 |
| Uncommon | 1 | $5M | 800 | 3 |
| Rare | 1 | $10M | 1,500 | 3 |
| Epic | 1 | $100M | 2,250 | 3 |
| Legendary | 1 | $1B | 3,000 | 3 |
| Mythic | 0 | $10B | 5,000 | 2 |
| Exotic | 0 | N/A | 10,000 | 1 |

### Ore Bonuses (per rarity, ~80+ ores)
Each ore: `name, min_kg, bonus_stat(s), max_boost`
- Bonus can be single stat or multiple (e.g., "Luck, Capacity" or "Dig Strength, Size Boost")
- Some have negative stats (e.g., Flarebloom: +Luck, -Size Boost)
- **Max boost is the cap** (e.g., 0.05×, 0.3×, 0.8×) - already in data, no calculation needed

### Modifier Riders (from Stat Systems Guide)
| Modifier | Base Bonus | Chance |
|----------|------------|--------|
| Perfect | Luck + Capacity + Size Boost | 0.0037% |
| Treasured | 2× Luck | Treasure chests only |
| Lunar | Dig Speed + Shake Speed + WalkSpeed | 0.009% |
| Voidtorn | Luck + Capacity | Void only |
| Mutated | Luck + Dig Strength + Modifier Boost | 0.037% |
| Cosmic | Capacity + Shake Strength | 0.187% |
| Electrified | Dig Speed + Shake Speed | Thunderstorm only |
| Iridescent | Luck | 0.747% |
| Crystalline | Size Boost | Geodes only |
| Irradiated | Modifier Boost | 3.736% |
| Scorching | Dig Strength | 9.341% |
| Glowing | Shake Speed | 18.68% |
| Pure | Dig Speed | 29.89% |
| Shiny | Shake Strength | 37.36% |

### Rarity Multipliers for Modifiers
- Common: 0.005×
- Uncommon: 0.0075×
- Rare: 0.0125×
- Epic: 0.02×
- Legendary: 0.03×
- Mythic: 0.05×
- Exotic: 0.08×
- Treasured: 2× above

## Calculator Features

### 1. Mineral Comparison (Primary)
**Input:** 
- Currently displayed ores (list of `{slot_id, rarity, slot_index, ore_name, kg, modifier}`)
- Available ores on hand (list of `{name, rarity, kg, modifier?}`)
- Target stats with weights (e.g., `{"Luck": 1.0, "Sell Boost": 0.5}`)
- Player's Size Boost (for weight gate)

**Output:** 
- Per-slot comparison: current ore vs best available alternative
- Stat delta if swapped
- Recommendation: keep current or swap to available ore
- Total projected stats for current vs optimized setup

**Algorithm:**
- For each slot, calculate current ore's effective boost (using max_boost cap, weight_factor, modifier_rider)
- For each available ore of same rarity, calculate its effective boost
- Find best available ore per slot
- Show comparison: current vs best alternative with stat deltas
- Weight factor: 1.0 if kg >= min_kg, else kg / min_kg (linear scaling)
- Modifier rider: modifier's base stats * rarity_multiplier (Treasured = 2×)

### 2. Total Stat Projection
**Input:** Current museum setup (ore per slot + modifier per slot + kg)
**Output:** Total stat boosts across all stats (using max_boost caps)

### 3. Weight Gate Checker
**Input:** Player's Size Boost, list of available ores
**Output:** Which ores meet min_kg for each rarity at current Size Boost (effective_kg = kg * (1 + size_boost/100))

## API Design

### Endpoint: `POST /api/v1/calculators/museum`

#### Request: `MuseumCalculatorRequest`
```python
class MuseumCalculatorRequest(BaseModel):
    # Currently displayed ores in museum
    current_displays: list[CurrentDisplay]  # slot_id, rarity, slot_index, ore_name, kg, modifier
    
    # Available ores the player has on hand
    available_ores: list[AvailableOre]  # name, rarity, kg, modifier (optional)
    
    # Target stats to optimize for (weights)
    target_stats: dict[str, float] = Field(default_factory=dict)
    # e.g., {"Luck": 1.0, "Sell Boost": 0.5, "Dig Speed": 0.3}
    
    # Player's Size Boost (for weight gate calculation)
    size_boost: float = Field(default=0.0, ge=0)
    
    # Mode: "compare" | "project" | "weight_gate"
    mode: str = Field(default="compare", pattern="^(compare|project|weight_gate)$")
```

#### Response: `MuseumCalculatorResponse`
```python
class MuseumCalculatorResponse(BaseModel):
    # Per-slot comparison: current vs best available
    slot_comparisons: list[SlotComparison]
    
    # Total projected stats for current setup
    current_total_stats: dict[str, float]
    
    # Total projected stats if all recommended swaps made
    optimized_total_stats: dict[str, float]
    
    # Per-rarity breakdown
    by_rarity: dict[str, RarityBreakdown]
    
    # Weight gate info for available ores
    weight_gate_info: list[WeightGateInfo] | None = None
```

## Implementation Tasks

### Phase 1: Service Layer (`app/services/calculators.py`)
- [ ] Add `calculate_museum_comparison()` - compare current vs available ores per slot
- [ ] Add `calculate_museum_projection()` - stat projection from current setup
- [ ] Add `calculate_weight_gate()` - check which ores meet min_kg
- [ ] Add helper: `get_ore_data(ore_name, rarity)` - fetch ore bonuses from database (min_kg, bonus_stat, max_boost)
- [ ] Add helper: `get_modifier_rider(modifier, rarity)` - compute modifier bonus
- [ ] Add helper: `weight_factor(kg, min_kg)` - linear scaling below min_kg
- [ ] Add helper: `calculate_effective_boost(ore_data, kg, modifier, rarity)` - compute boost using max_boost cap

### Phase 2: Schemas (`app/schemas/calculator.py`)
- [ ] `CurrentDisplay` - slot_id, rarity, slot_index, ore_name, kg, modifier
- [ ] `AvailableOre` - name, rarity, kg, modifier
- [ ] `MuseumCalculatorRequest` - as above
- [ ] `SlotComparison` - slot_id, rarity, current_ore, current_boost, best_available_ore, best_boost, stat_deltas, recommendation
- [ ] `RarityBreakdown` - rarity, slots_filled, total_boost, current_ores, recommended_swaps
- [ ] `WeightGateInfo` - ore_name, rarity, min_kg, current_kg, effective_kg, meets_requirement
- [ ] `MuseumCalculatorResponse` - as above
- [ ] Add OpenAPI examples for all

### Phase 3: API Endpoint (`app/api/calculators.py`)
- [ ] Add `POST /museum` endpoint with `response_model=MuseumCalculatorResponse`
- [ ] Import new schemas and service functions
- [ ] Add proper docstring and tags

### Phase 4: Tests
- [ ] Unit tests for each service function
- [ ] Integration test for full endpoint
- [ ] Test with fixture data (Museum.wiki)
- [ ] Edge cases: no ores, partial displays, negative stats, multi-stat ores, no available alternatives

## Dependencies
- Requires parsed museum data in database (items of type `museum_display` and `museum_ore`)
- Uses existing `Item` model - query by `type` and `data.rarity`
- No new database models needed

## Validation Plan
1. Run existing tests: `pytest tests/ -v`
2. Run new museum calculator tests
3. Verify OpenAPI schema at `/openapi.json`
4. Manual test via API docs at `/docs`

## Out of Scope (Future)
- Equipment Calculator (separate plan)
- Auto-fetch player's museum from game (would need auth)
- Museum setup save/load (Manage Museums Board)
- Rune/Enchant interactions with museum stats
- Unlock cost calculator (displayed on wiki page)
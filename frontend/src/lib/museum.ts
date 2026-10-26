/**
 * Museum calculator math ported from app/services/calculators.py
 * Pure TypeScript — no external dependencies.
 */

// Display configuration: rarity -> {free, locked_money, locked_shards, total}
export const MUSEUM_DISPLAYS: Record<string, { free: number; locked_money: number; locked_shards: number; total: number }> = {
	Common: { free: 1, locked_money: 1, locked_shards: 1, total: 3 },
	Uncommon: { free: 1, locked_money: 1, locked_shards: 1, total: 3 },
	Rare: { free: 1, locked_money: 1, locked_shards: 1, total: 3 },
	Epic: { free: 1, locked_money: 1, locked_shards: 1, total: 3 },
	Legendary: { free: 1, locked_money: 1, locked_shards: 1, total: 3 },
	Mythic: { free: 0, locked_money: 1, locked_shards: 1, total: 2 },
	Exotic: { free: 0, locked_money: 0, locked_shards: 1, total: 1 },
};

// Rarity display order
export const RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic", "Exotic"];

// Modifier base bonuses (from Stat Systems Guide)
export const MODIFIER_BASE_BONUSES: Record<string, Record<string, number>> = {
	Perfect: { Luck: 1, Capacity: 1, "Size Boost": 1 },
	Treasured: { Luck: 2 },
	Lunar: { "Dig Speed": 1, "Shake Speed": 1, "Walk Speed": 1 },
	Voidtorn: { Luck: 1, Capacity: 1 },
	Mutated: { Luck: 1, "Dig Strength": 1, "Modifier Boost": 1 },
	Cosmic: { Capacity: 1, "Shake Strength": 1 },
	Electrified: { "Dig Speed": 1, "Shake Speed": 1 },
	Iridescent: { Luck: 1 },
	Crystalline: { "Size Boost": 1 },
	Irradiated: { "Modifier Boost": 1 },
	Scorching: { "Dig Strength": 1 },
	Glowing: { "Shake Speed": 1 },
	Pure: { "Dig Speed": 1 },
	Shiny: { "Shake Strength": 1 },
};

// Rarity multipliers for modifier riders
export const MODIFIER_RARITY_MULTIPLIERS: Record<string, number> = {
	Common: 0.005,
	Uncommon: 0.0075,
	Rare: 0.0125,
	Epic: 0.02,
	Legendary: 0.03,
	Mythic: 0.05,
	Exotic: 0.08,
};

export function getModifierRider(modifier: string | null | undefined, rarity: string): Record<string, number> {
	if (!modifier) {
		return {};
	}

	const base = MODIFIER_BASE_BONUSES[modifier];
	if (!base) {
		return {};
	}

	const multiplier = MODIFIER_RARITY_MULTIPLIERS[rarity] ?? 0;

	// Treasured gives 2x the amounts
	const effectiveMultiplier = modifier === "Treasured" ? multiplier * 2 : multiplier;

	const result: Record<string, number> = {};
	for (const [stat, value] of Object.entries(base)) {
		result[stat] = value * effectiveMultiplier;
	}

	return result;
}

export function weightFactor(kg: number, minKg: number): number {
	if (minKg <= 0) {
		return 1.0;
	}
	if (kg >= minKg) {
		return 1.0;
	}
	return kg / minKg;
}

export function parseBonusStat(bonusStr: string | null | undefined): [string, number][] {
	if (!bonusStr) {
		return [];
	}

	const stats: [string, number][] = [];
	const parts = bonusStr.replace("{{Stat|", "").replace("}}", "").split(",");
	for (const part of parts) {
		const trimmed = part.trim();
		if (!trimmed) {
			continue;
		}

		let multiplier = 1.0;
		let stat = trimmed;

		if (trimmed.startsWith("+")) {
			stat = trimmed.slice(1).trim();
		} else if (trimmed.startsWith("-")) {
			stat = trimmed.slice(1).trim();
			multiplier = -1.0;
		}

		// Handle "0.25×" format
		if (stat.includes("×")) {
			const [statPart, multPart] = stat.split("×");
			stat = statPart.trim();
			try {
				multiplier = parseFloat(multPart.replace("×", "").trim());
			} catch {
				multiplier = 1.0;
			}
		}

		stats.push([stat, multiplier]);
	}

	return stats;
}

export interface OreData {
	min_kg?: number;
	bonus_stat?: string;
	max_boost?: string | number;
	[key: string]: unknown;
}

export function calculateEffectiveBoost(
	oreData: OreData,
	kg: number,
	modifier: string | null | undefined,
	rarity: string
): Record<string, number> {
	const minKg = (oreData.min_kg as number) ?? 0;
	const bonusStr = (oreData.bonus_stat as string) ?? "";
	const maxBoostRaw = oreData.max_boost ?? 0;

	// Parse max_boost - could be "0.05×" or "0.3×" or "0.75×, -0.5×"
	let boostValues: number[] = [];
	if (typeof maxBoostRaw === "string") {
		for (const part of maxBoostRaw.split(",")) {
			const trimmed = part.trim().replace("×", "");
			const val = parseFloat(trimmed);
			boostValues.push(Number.isNaN(val) ? 0.0 : val);
		}
	} else {
		boostValues = [Number(maxBoostRaw)];
	}

	// Parse bonus stats
	const bonusStats = parseBonusStat(bonusStr);

	// Calculate weight factor
	const wf = weightFactor(kg, minKg);

	// Calculate base ore boost (capped at max_boost via weight_factor)
	const result: Record<string, number> = {};
	for (let i = 0; i < bonusStats.length; i++) {
		const [stat, sign] = bonusStats[i];
		const boost = i < boostValues.length ? boostValues[i] : boostValues[0];
		result[stat] = (result[stat] ?? 0) + sign * boost * wf;
	}

	// Add modifier rider if applicable
	if (modifier) {
		const rider = getModifierRider(modifier, rarity);
		for (const [stat, value] of Object.entries(rider)) {
			result[stat] = (result[stat] ?? 0) + value;
		}
	}

	return result;
}

export interface CurrentDisplay {
	slot_id: string;
	rarity: string;
	slot_index: number;
	ore_name: string;
	kg: number;
	modifier?: string | null;
}

export interface AvailableOreInput {
	name: string;
	rarity: string;
	kg: number;
	modifier?: string | null;
}

export interface MuseumComparatorInputs {
	currentDisplays: CurrentDisplay[];
	availableOres: AvailableOreInput[];
	targetStats: Record<string, number>;
	sizeBoost: number;
	oreDatabase: Record<string, OreData>;
}

export interface SlotComparison {
	slot_id: string;
	rarity: string;
	slot_index: number;
	current_ore: string | null;
	current_kg: number;
	current_modifier: string | null | undefined;
	current_boost: Record<string, number>;
	best_available_ore: string | null;
	best_available_kg: number | null;
	best_available_modifier: string | null | undefined;
	best_boost: Record<string, number>;
	stat_deltas: Record<string, number>;
	recommendation: string;
}

export interface RarityBreakdown {
	ores_used: string[];
	slots_filled: number;
	total_boost: Record<string, number>;
	total_slots: number;
}

export interface MuseumComparatorOutput {
	slot_comparisons: SlotComparison[];
	current_total_stats: Record<string, number>;
	optimized_total_stats: Record<string, number>;
	by_rarity: Record<string, RarityBreakdown>;
}

export function calculateMuseumComparison(inputs: MuseumComparatorInputs): MuseumComparatorOutput {
	const { currentDisplays, availableOres, targetStats, oreDatabase } = inputs;

	// Group available ores by rarity
	const availableByRarity: Record<string, AvailableOreInput[]> = {};
	for (const ore of availableOres) {
		if (!availableByRarity[ore.rarity]) {
			availableByRarity[ore.rarity] = [];
		}
		availableByRarity[ore.rarity].push(ore);
	}

	// Group current displays by rarity
	const currentByRarity: Record<string, CurrentDisplay[]> = {};
	for (const display of currentDisplays) {
		if (!currentByRarity[display.rarity]) {
			currentByRarity[display.rarity] = [];
		}
		currentByRarity[display.rarity].push(display);
	}

	const slotComparisons: SlotComparison[] = [];
	const currentTotalStats: Record<string, number> = {};
	const optimizedTotalStats: Record<string, number> = {};
	const byRarity: Record<string, RarityBreakdown> = {};

	for (const rarity of RARITY_ORDER) {
		const displayInfo = MUSEUM_DISPLAYS[rarity];
		if (!displayInfo) {
			continue;
		}

		const totalSlots = displayInfo.total;
		const currentSlots = currentByRarity[rarity] ?? [];
		const availableRarityOres = availableByRarity[rarity] ?? [];

		const rarityCurrentTotal: Record<string, number> = {};
		const rarityOptimizedTotal: Record<string, number> = {};
		const currentOres: string[] = [];
		const recommendedSwaps: { slot: string; from: string; to: string }[] = [];

		// Process each current display slot
		for (const slot of currentSlots) {
			const slotId = slot.slot_id ?? `${rarity.toLowerCase()}-${slot.slot_index}`;
			const oreName = slot.ore_name;
			const kg = slot.kg;
			const modifier = slot.modifier;

			// Get ore data from database
			const oreDataKey = `${oreName}|${rarity}`;
			const oreData = oreDatabase[oreDataKey] ?? {};

			// Calculate current ore's effective boost
			const currentBoost = calculateEffectiveBoost(oreData, kg, modifier, rarity);

			// Find best available ore of same rarity
			let bestAvailable: AvailableOreInput | null = null;
			let bestBoost: Record<string, number> = {};
			let bestScore = -1.0;

			for (const availOre of availableRarityOres) {
				const availOreDataKey = `${availOre.name}|${rarity}`;
				const availOreData = oreDatabase[availOreDataKey] ?? {};

				const availBoost = calculateEffectiveBoost(
					availOreData,
					availOre.kg,
					availOre.modifier,
					rarity
				);

				// Score based on target stats
				let score = 0.0;
				for (const [stat, weight] of Object.entries(targetStats)) {
					score += (availBoost[stat] ?? 0) * weight;
				}

				if (score > bestScore) {
					bestScore = score;
					bestAvailable = availOre;
					bestBoost = availBoost;
				}
			}

			// Calculate stat deltas
			const statDeltas: Record<string, number> = {};
			const allStats = new Set([...Object.keys(currentBoost), ...Object.keys(bestBoost)]);
			for (const stat of allStats) {
				const currentVal = currentBoost[stat] ?? 0;
				const bestVal = bestBoost[stat] ?? 0;
				statDeltas[stat] = Math.round((bestVal - currentVal) * 10000) / 10000;
			}

			// Determine recommendation
			const totalDelta = Object.values(statDeltas).reduce((a, b) => a + b, 0);
			const recommendation =
				bestAvailable && totalDelta > 0.001 ? `Swap to ${bestAvailable.name}` : "Keep current";

			slotComparisons.push({
				slot_id: slotId,
				rarity,
				slot_index: slot.slot_index,
				current_ore: oreName,
				current_kg: kg,
				current_modifier: modifier,
				current_boost: Object.fromEntries(
					Object.entries(currentBoost).map(([k, v]) => [k, Math.round(v * 10000) / 10000])
				),
				best_available_ore: bestAvailable ? bestAvailable.name : null,
				best_available_kg: bestAvailable ? bestAvailable.kg : null,
				best_available_modifier: bestAvailable ? bestAvailable.modifier : null,
				best_boost: Object.fromEntries(
					Object.entries(bestBoost).map(([k, v]) => [k, Math.round(v * 10000) / 10000])
				),
				stat_deltas: statDeltas,
				recommendation,
			});

			// Add to current totals
			for (const [stat, value] of Object.entries(currentBoost)) {
				currentTotalStats[stat] = (currentTotalStats[stat] ?? 0) + value;
				rarityCurrentTotal[stat] = (rarityCurrentTotal[stat] ?? 0) + value;
			}

			// Add to optimized totals (use best available if better, else current)
			if (bestAvailable && totalDelta > 0.001) {
				for (const [stat, value] of Object.entries(bestBoost)) {
					optimizedTotalStats[stat] = (optimizedTotalStats[stat] ?? 0) + value;
					rarityOptimizedTotal[stat] = (rarityOptimizedTotal[stat] ?? 0) + value;
				}
				recommendedSwaps.push({
					slot: slotId,
					from: oreName,
					to: bestAvailable.name,
				});
			} else {
				for (const [stat, value] of Object.entries(currentBoost)) {
					optimizedTotalStats[stat] = (optimizedTotalStats[stat] ?? 0) + value;
					rarityOptimizedTotal[stat] = (rarityOptimizedTotal[stat] ?? 0) + value;
				}
			}

			currentOres.push(oreName);
		}

		// Handle empty slots (if fewer current displays than total slots)
		const filledSlots = currentSlots.length;
		for (let slotIdx = filledSlots; slotIdx < totalSlots; slotIdx++) {
			const slotId = `${rarity.toLowerCase()}-${slotIdx + 1}`;
			if (availableRarityOres.length === 0) {
				continue;
			}

			// Find best available ore for empty slot
			let bestAvailable: AvailableOreInput | null = null;
			let bestBoost: Record<string, number> = {};
			let bestScore = -1.0;

			for (const availOre of availableRarityOres) {
				const availOreDataKey = `${availOre.name}|${rarity}`;
				const availOreData = oreDatabase[availOreDataKey] ?? {};

				const availBoost = calculateEffectiveBoost(
					availOreData,
					availOre.kg,
					availOre.modifier,
					rarity
				);

				let score = 0.0;
				for (const [stat, weight] of Object.entries(targetStats)) {
					score += (availBoost[stat] ?? 0) * weight;
				}

				if (score > bestScore) {
					bestScore = score;
					bestAvailable = availOre;
					bestBoost = availBoost;
				}
			}

			if (bestAvailable) {
				slotComparisons.push({
					slot_id: slotId,
					rarity,
					slot_index: slotIdx + 1,
					current_ore: null,
					current_kg: 0,
					current_modifier: null,
					current_boost: {},
					best_available_ore: bestAvailable.name,
					best_available_kg: bestAvailable.kg,
					best_available_modifier: bestAvailable.modifier,
					best_boost: Object.fromEntries(
						Object.entries(bestBoost).map(([k, v]) => [k, Math.round(v * 10000) / 10000])
					),
					stat_deltas: Object.fromEntries(
						Object.entries(bestBoost).map(([k, v]) => [k, Math.round(v * 10000) / 10000])
					),
					recommendation: `Fill with ${bestAvailable.name}`,
				});

				for (const [stat, value] of Object.entries(bestBoost)) {
					optimizedTotalStats[stat] = (optimizedTotalStats[stat] ?? 0) + value;
					rarityOptimizedTotal[stat] = (rarityOptimizedTotal[stat] ?? 0) + value;
				}
				recommendedSwaps.push({
					slot: slotId,
					from: "Empty",
					to: bestAvailable.name,
				});
			}
		}

		const rarityCurrentTotalRounded: Record<string, number> = {};
		const rarityOptimizedTotalRounded: Record<string, number> = {};
		for (const [k, v] of Object.entries(rarityCurrentTotal)) {
			rarityCurrentTotalRounded[k] = Math.round(v * 10000) / 10000;
		}
		for (const [k, v] of Object.entries(rarityOptimizedTotal)) {
			rarityOptimizedTotalRounded[k] = Math.round(v * 10000) / 10000;
		}

		byRarity[rarity] = {
			ores_used: currentOres,
			slots_filled: filledSlots,
			total_boost: rarityOptimizedTotalRounded,
			total_slots: totalSlots,
		};
	}

	// Round totals
	const currentTotalStatsRounded: Record<string, number> = {};
	const optimizedTotalStatsRounded: Record<string, number> = {};
	for (const [k, v] of Object.entries(currentTotalStats)) {
		currentTotalStatsRounded[k] = Math.round(v * 10000) / 10000;
	}
	for (const [k, v] of Object.entries(optimizedTotalStats)) {
		optimizedTotalStatsRounded[k] = Math.round(v * 10000) / 10000;
	}

	return {
		slot_comparisons: slotComparisons,
		current_total_stats: currentTotalStatsRounded,
		optimized_total_stats: optimizedTotalStatsRounded,
		by_rarity: byRarity,
	};
}

export interface WeightGateOre {
	ore_name: string;
	rarity: string;
	min_kg: number;
	current_kg: number;
	effective_kg: number;
	meets_requirement: boolean;
}

export interface WeightGateInputs {
	availableOres: AvailableOreInput[];
	sizeBoost: number;
	oreDatabase: Record<string, OreData>;
}

export function calculateWeightGate(inputs: WeightGateInputs): WeightGateOre[] {
	const { availableOres, sizeBoost, oreDatabase } = inputs;

	// Weight multiplier from size boost
	const weightMult = 1 + sizeBoost / 100;

	const results: WeightGateOre[] = [];
	for (const ore of availableOres) {
		const oreDataKey = `${ore.name}|${ore.rarity}`;
		const oreData = oreDatabase[oreDataKey] ?? {};

		const minKg = (oreData.min_kg as number) ?? 0;
		const currentKg = ore.kg;
		const effectiveKg = currentKg * weightMult;

		results.push({
			ore_name: ore.name,
			rarity: ore.rarity,
			min_kg: minKg,
			current_kg: currentKg,
			effective_kg: Math.round(effectiveKg * 10) / 10,
			meets_requirement: effectiveKg >= minKg,
		});
	}

	return results;
}

export interface UnlockCostsOutput {
	money_cost: number;
	shards_cost: number;
	total_cost: { money: number; shards: number };
}

export function calculateUnlockCosts(unlockedDisplays: CurrentDisplay[]): UnlockCostsOutput {
	const unlocked = new Set<string>();
	for (const d of unlockedDisplays) {
		unlocked.add(`${d.rarity}|${d.slot_index}`);
	}

	let totalMoney = 0;
	let totalShards = 0;

	for (const [rarity, info] of Object.entries(MUSEUM_DISPLAYS)) {
		const totalSlots = info.total;
		const freeSlots = info.free;
		const lockedMoney = info.locked_money;
		const lockedShards = info.locked_shards;

		// Slots that need unlocking beyond free ones
		const lockedSlots = Math.max(0, totalSlots - freeSlots);
		// Subtract any already-unlocked slots for this rarity
		let unlockedCount = 0;
		for (const d of unlockedDisplays) {
			if (d.rarity === rarity) {
				unlockedCount += 1;
			}
		}
		const remainingLocked = Math.max(0, lockedSlots - unlockedCount);

		totalMoney += remainingLocked * lockedMoney;
		totalShards += remainingLocked * lockedShards;
	}

	return {
		money_cost: totalMoney,
		shards_cost: totalShards,
		total_cost: { money: totalMoney, shards: totalShards },
	};
}

export interface MuseumOptimizerInputs {
	availableOres: AvailableOreInput[];
	unlockedDisplays?: CurrentDisplay[];
	targetStats?: Record<string, number>;
	sizeBoost?: number;
}

export interface MuseumOptimizerOutput {
	slot_recommendations: SlotComparison[];
	total_stats: Record<string, number>;
	by_rarity: Record<string, RarityBreakdown>;
	unlock_costs: UnlockCostsOutput;
	weight_gate_info: WeightGateOre[];
}

export function calculateMuseumOptimizer(inputs: MuseumOptimizerInputs): MuseumOptimizerOutput {
	const targetStats = inputs.targetStats ?? {};
	const unlocked = inputs.unlockedDisplays ?? [];
	const sizeBoost = inputs.sizeBoost ?? 0;

	// Build current_displays from unlocked_displays for comparison
	const currentDisplays: CurrentDisplay[] = [];
	for (let i = 0; i < unlocked.length; i++) {
		const ud = unlocked[i];
		currentDisplays.push({
			slot_id: ud.slot_id ?? `slot-${i}`,
			rarity: ud.rarity,
			slot_index: ud.slot_index ?? i,
			ore_name: ud.ore_name,
			kg: ud.kg,
			modifier: ud.modifier,
		});
	}

	// Build ore database from snapshot items
	const oreDatabase: Record<string, OreData> = {};
	for (const ore of inputs.availableOres) {
		oreDatabase[`${ore.name}|${ore.rarity}`] = {} as OreData;
	}

	// Use the existing comparison engine
	const comparison = calculateMuseumComparison({
		currentDisplays,
		availableOres: inputs.availableOres,
		targetStats,
		sizeBoost,
		oreDatabase,
	});

	const unlockInfo = calculateUnlockCosts(unlocked);
	const weightInfo = calculateWeightGate({
		availableOres: inputs.availableOres,
		sizeBoost,
		oreDatabase,
	});

	return {
		slot_recommendations: comparison.slot_comparisons,
		total_stats: comparison.optimized_total_stats,
		by_rarity: comparison.by_rarity,
		unlock_costs: unlockInfo,
		weight_gate_info: weightInfo,
	};
}

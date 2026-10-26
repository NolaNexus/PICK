/**
 * Calculator math ported from app/services/calculators.py
 * Pure TypeScript — no external dependencies.
 */

// Shake speed conversion (buggy - from Stat Systems Guide)
const SHAKE_SPEED_STEPS: [number, number, number][] = [
	[0, 400, 0.4], // 0-400%: linear
	[400, 600, 0.6], // 400-600%: buggy
	[600, 650, 0.65], // 600-650%: sweet spot
	[650, 900, 0.9], // 650-900%: linear
	[900, 950, 0.95], // 900-950%: sweet spot
	[950, 1000, 0.9], // 950-1000%: buggy zone
	[1000, 1700, 0.9], // 1000-1700%: BUGGED - same as 900%
	[1700, Infinity, 1.0], // 1700%+: linear
];

export function shakesPerSecond(shakeSpeedPct: number): number {
	const baseRate = 0.1;
	for (const [minPct, maxPct, multiplier] of SHAKE_SPEED_STEPS) {
		if (minPct <= shakeSpeedPct && shakeSpeedPct < maxPct) {
			return baseRate * multiplier;
		}
	}
	return baseRate * 1.0;
}

export function digsPerPan(capacity: number, digStrength: number): number {
	if (digStrength <= 0) {
		return 1;
	}
	return Math.max(1, Math.ceil(capacity / (1.5 * digStrength)));
}

export function digTimePerDig(digSpeed: number): number {
	if (digSpeed <= 0) {
		return 1.0;
	}
	return 143.9 * digSpeed ** -0.93;
}

export function itemsPerPan(capacity: number): number {
	if (capacity <= 0) {
		return 0;
	}
	return Math.sqrt(capacity) * 1.08;
}

export function weightMultiplier(sizeBoost: number): number {
	return 1 + sizeBoost / 100;
}

export function sellMultiplier(sellBoost: number): number {
	return 1 + sellBoost / 100;
}

export function modifierLuck(luck: number, modifierBoost: number): number {
	return Math.min(50, luck / 1000) + modifierBoost / 10;
}

export function effectiveModifierBoost(
	panelModifierBoost: number,
	solarMagnifier = false,
	modifierSurge = false,
	forWhichModifier = false
): number {
	let effective = panelModifierBoost;

	if (forWhichModifier) {
		// Job 2: which modifier you get
		if (modifierSurge) {
			effective *= 2;
		}
		// Solar Magnifier does NOT affect Job 2
	} else {
		// Job 1: % of ores that get a modifier
		if (solarMagnifier) {
			effective *= 2;
		}
		if (modifierSurge) {
			effective *= 2;
		}
	}

	return effective;
}

export function pctOresModified(effectiveMB: number): number {
	if (effectiveMB <= 0) {
		return 0.0;
	}
	if (effectiveMB >= 1900) {
		return 99.4;
	}

	// Approximate the steep curve: rapid rise then plateau
	const x = effectiveMB / 1900;
	// Steep rise: use x^0.3 for initial steepness, then level off
	return Math.min(99.4, 99.4 * x ** 0.3 * 1.15);
}

// Modifier base distribution (from Stat Systems Guide table)
export const MODIFIER_BASE_DISTRIBUTION: Record<string, number> = {
	Perfect: 0.002, // 0.002%
	Treasured: 0.01, // treasure chests only
	Lunar: 0.05, // night only
	Voidtorn: 0.1, // Void tools only
	Mutated: 0.3,
	Cosmic: 1.0,
	Iridescent: 3.0,
	Irradiated: 8.0,
	Crystalline: 15.0, // geodes / Crystal Touch
	Scorching: 25.0,
	Glowing: 40.0,
	Pure: 55.0,
	Shiny: 70.0,
};

export function modifierDistribution(effectiveMB: number): Record<string, number> {
	if (effectiveMB <= 0) {
		const result: Record<string, number> = {};
		for (const mod of Object.keys(MODIFIER_BASE_DISTRIBUTION)) {
			result[mod] = 0.0;
		}
		return result;
	}

	// Boost factor for rare modifiers based on effective MB
	let rareBoost: number;
	if (effectiveMB >= 1900) {
		rareBoost = 3.0;
	} else if (effectiveMB >= 1000) {
		rareBoost = 2.0;
	} else if (effectiveMB >= 500) {
		rareBoost = 1.5;
	} else {
		rareBoost = 1.0;
	}

	// Apply boost: rarer modifiers (lower base %) get boosted more
	const boosted: Record<string, number> = {};
	for (const [mod, basePct] of Object.entries(MODIFIER_BASE_DISTRIBUTION)) {
		// Rarity factor: inverse of base probability (rarer = higher factor)
		const rarityFactor = 1 / (basePct + 0.1);
		boosted[mod] = basePct * rareBoost ** Math.min(rarityFactor, 5);
	}

	// Normalize to sum to pct_modified
	const pctMod = pctOresModified(effectiveMB);
	const total = Object.values(boosted).reduce((a, b) => a + b, 0);
	const normalized: Record<string, number> = {};
	for (const [k, v] of Object.entries(boosted)) {
		normalized[k] = Math.round((v / total) * pctMod * 1000) / 1000;
	}

	return normalized;
}

export function qualityMultiplier(autopan = false, masteredShovel = false): number {
	// Manual: 100%
	// Autopan: 51% (⅔ luck)
	// Mastered shovel enchant restores 100% quality
	if (autopan) {
		if (masteredShovel) {
			return 1.0;
		}
		return 0.51;
	}
	return 1.0;
}

export function pansPerHour(
	capacity: number,
	digStrength: number,
	digSpeed: number,
	shakeStrength: number,
	shakeSpeed: number
): number {
	const digs = digsPerPan(capacity, digStrength);
	const digTime = digTimePerDig(digSpeed);
	const shakeSps = shakesPerSecond(shakeSpeed);
	const shakeTime =
		shakeStrength > 0 && shakeSps > 0 ? capacity / (shakeStrength * shakeSps) : 0;

	const panTime = digs * digTime + shakeTime;
	if (panTime <= 0) {
		return 0;
	}
	return 3600 / panTime;
}

export interface EVInputs {
	locationDropTable: { base_price?: number; base_weight?: number; rarity?: string }[];
	luck: number;
	modifierBoost: number;
	quality?: number;
	autopan?: boolean;
	masteredShovel?: boolean;
	solarMagnifier?: boolean;
	modifierSurge?: boolean;
	capacity?: number;
}

export interface EVOutput {
	evPerPan: number;
	itemsPerPan: number;
	qualityMultiplier: number;
	effectiveModifierBoost: number;
	modifierDistribution: Record<string, number>;
	pctModified: number;
}

export function calculateEV(inputs: EVInputs): EVOutput {
	const q = qualityMultiplier(inputs.autopan ?? false, inputs.masteredShovel ?? false);
	const effMB = effectiveModifierBoost(
		inputs.modifierBoost ?? 0,
		inputs.solarMagnifier ?? false,
		inputs.modifierSurge ?? false
	);
	const modDist = modifierDistribution(effMB);

	const totalEv = 0.0;

	return {
		evPerPan: totalEv,
		itemsPerPan: itemsPerPan(inputs.capacity ?? 0),
		qualityMultiplier: q,
		effectiveModifierBoost: effMB,
		modifierDistribution: modDist,
		pctModified: pctOresModified(effMB),
	};
}

export interface TTGInputs {
	goalValue: number;
	locationEvPerPan: number;
	capacity: number;
	digStrength: number;
	digSpeed: number;
	shakeStrength: number;
	shakeSpeed: number;
}

export interface TTGOutput {
	hoursToGoal: number;
	pansPerHour: number;
	evPerHour: number;
	evPerPan: number;
	digsPerPan: number;
	digTimePerDig: number;
	shakeTime: number;
}

export function calculateTTG(inputs: TTGInputs): TTGOutput {
	const pph = pansPerHour(
		inputs.capacity,
		inputs.digStrength,
		inputs.digSpeed,
		inputs.shakeStrength,
		inputs.shakeSpeed
	);
	const evPerHour = inputs.locationEvPerPan * pph;

	const hours = evPerHour <= 0 ? Infinity : inputs.goalValue / evPerHour;

	return {
		hoursToGoal: Math.round(hours * 100) / 100,
		pansPerHour: Math.round(pph * 100) / 100,
		evPerHour: Math.round(evPerHour * 100) / 100,
		evPerPan: Math.round(inputs.locationEvPerPan * 100) / 100,
		digsPerPan: digsPerPan(inputs.capacity, inputs.digStrength),
		digTimePerDig: Math.round(digTimePerDig(inputs.digSpeed) * 1000) / 1000,
		shakeTime:
			Math.round(
				(inputs.capacity / (inputs.shakeStrength * shakesPerSecond(inputs.shakeSpeed))) * 100
			) / 100,
	};
}

export interface ModifierOddsInputs {
	panelModifierBoost: number;
	solarMagnifier?: boolean;
	modifierSurge?: boolean;
}

export interface ModifierOddsOutput {
	effectiveModifierBoostJob1: number;
	effectiveModifierBoostJob2: number;
	pctOresModified: number;
	modifierDistribution: Record<string, number>;
	note: string;
}

export function calculateModifierOdds(inputs: ModifierOddsInputs): ModifierOddsOutput {
	const effMB1 = effectiveModifierBoost(
		inputs.panelModifierBoost,
		inputs.solarMagnifier ?? false,
		inputs.modifierSurge ?? false,
		false
	);
	const effMB2 = effectiveModifierBoost(
		inputs.panelModifierBoost,
		inputs.solarMagnifier ?? false,
		inputs.modifierSurge ?? false,
		true
	);

	const pctMod = pctOresModified(effMB1);
	const distribution = modifierDistribution(effMB2);

	return {
		effectiveModifierBoostJob1: Math.round(effMB1 * 10) / 10,
		effectiveModifierBoostJob2: Math.round(effMB2 * 10) / 10,
		pctOresModified: Math.round(pctMod * 10) / 10,
		modifierDistribution: distribution,
		note: "Solar Magnifier doubles for Job 1 only. Modifier Surge doubles for both jobs.",
	};
}

export interface BestPanInputPan {
	name: string;
	capacity: number;
	digStrength: number;
	shakeStrength: number;
	shakeSpeed: number;
	luck: number;
	sizeBoost: number;
	modifierBoost: number;
	data?: Record<string, unknown>;
}

export interface BestPanInputs {
	pans: BestPanInputPan[];
	digStrength: number;
	shakeStrength: number;
	shakeSpeed: number;
	targetCapacity?: number;
	minLuck?: number;
	minSizeBoost?: number;
	minModifierBoost?: number;
}

export interface BestPanRecommendation {
	pan: BestPanInputPan;
	score: number;
	capacity: number;
	digsPerPan: number;
	pansPerHour: number;
	luck: number;
	sizeBoost: number;
	modifierBoost: number;
}

export interface BestPanOutput {
	criteria: Record<string, number>;
	recommendations: BestPanRecommendation[];
}

export function calculateBestPan(inputs: BestPanInputs): BestPanOutput {
	const scoredPans: BestPanRecommendation[] = [];

	for (const pan of inputs.pans) {
		const data = pan.data ?? {};
		const capacity = (data.capacity as number ?? pan.capacity) ?? 0;
		const digStr = (data.dig_strength as number ?? pan.digStrength) ?? 0;
		const shakeStr = (data.shake_strength as number ?? pan.shakeStrength) ?? 0;
		const shakeSpd = (data.shake_speed as number ?? pan.shakeSpeed) ?? 0;
		const luck = (data.luck as number ?? pan.luck) ?? 0;
		const sizeBoost = (data.size_boost as number ?? pan.sizeBoost) ?? 0;
		const modBoost = (data.modifier_boost as number ?? pan.modifierBoost) ?? 0;

		// Apply filters
		if (inputs.targetCapacity && capacity < inputs.targetCapacity) {
			continue;
		}
		if (inputs.minLuck && luck < inputs.minLuck) {
			continue;
		}
		if (inputs.minSizeBoost && sizeBoost < inputs.minSizeBoost) {
			continue;
		}
		if (inputs.minModifierBoost && modBoost < inputs.minModifierBoost) {
			continue;
		}

		// Calculate digs (lower is better)
		const digs = digStr > 0 ? digsPerPan(capacity, digStr) : 999;

		// Calculate pans per hour
		const pph =
			digStr > 0
				? pansPerHour(capacity, digStr, 1000, shakeStr, shakeSpd)
				: 0;

		// Simple scoring: prioritize PPH, then capacity, then stats
		const score = pph * 0.5 + capacity * 0.2 + luck * 0.1 + sizeBoost * 0.1 + modBoost * 0.1;

		scoredPans.push({
			pan,
			score: Math.round(score * 100) / 100,
			capacity,
			digsPerPan: digs,
			pansPerHour: Math.round(pph * 100) / 100,
			luck,
			sizeBoost,
			modifierBoost: modBoost,
		});
	}

	// Sort by score descending
	scoredPans.sort((a, b) => b.score - a.score);

	return {
		criteria: {
			target_capacity: inputs.targetCapacity ?? 0,
			dig_strength: inputs.digStrength,
			shake_strength: inputs.shakeStrength,
			shake_speed: inputs.shakeSpeed,
		},
		recommendations: scoredPans.slice(0, 5),
	};
}

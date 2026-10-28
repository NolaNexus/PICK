import { describe, it, expect } from 'vitest'
import {
	shakesPerSecond,
	digsPerPan,
	digTimePerDig,
	itemsPerPan,
	weightMultiplier,
	sellMultiplier,
	modifierLuck,
	effectiveModifierBoost,
	pctOresModified,
	modifierDistribution,
	qualityMultiplier,
	pansPerHour,
	calculateEV,
	calculateTTG,
	calculateModifierOdds,
	calculateBestPan,
	MODIFIER_BASE_DISTRIBUTION,
} from './calculators'

describe('shakesPerSecond', () => {
	// The step table encodes the wiki's own "buggy" bands. The comment in
	// calculators.ts says so, so a failure here means the wiki changed, not
	// the code.
	it('scales the base rate by the band multiplier', () => {
		expect(shakesPerSecond(0)).toBeCloseTo(0.1 * 0.4, 10)
		expect(shakesPerSecond(400)).toBeCloseTo(0.1 * 0.6, 10)
		expect(shakesPerSecond(600)).toBeCloseTo(0.1 * 0.65, 10)
		expect(shakesPerSecond(650)).toBeCloseTo(0.1 * 0.9, 10)
		expect(shakesPerSecond(900)).toBeCloseTo(0.1 * 0.95, 10)
		expect(shakesPerSecond(1700)).toBeCloseTo(0.1 * 1.0, 10)
	})

	it('treats the 1000% band as the same as the 950% band', () => {
		// The table marks 1000-1700% as "BUGGED - same as 900%", but the 900%
		// band is 0.95 and the buggy one is 0.9, so it matches the 950-1000%
		// band instead. The table is what it is; the test pins it.
		expect(shakesPerSecond(1000)).toBe(shakesPerSecond(950))
		expect(shakesPerSecond(1000)).toBeCloseTo(0.1 * 0.9, 10)
	})

	it('falls back to the base rate below the first band', () => {
		expect(shakesPerSecond(-1)).toBeCloseTo(0.1, 10)
	})
})

describe('digsPerPan', () => {
	it('never drops below one dig', () => {
		expect(digsPerPan(0, 50)).toBe(1)
		expect(digsPerPan(1, 1000)).toBe(1)
	})

	it('returns one when there is no dig strength', () => {
		expect(digsPerPan(100, 0)).toBe(1)
		expect(digsPerPan(100, -5)).toBe(1)
	})

	it('rounds the dig count up', () => {
		// ceil(100 / (1.5 * 10)) = ceil(6.67) = 7
		expect(digsPerPan(100, 10)).toBe(7)
	})
})

describe('digTimePerDig', () => {
	it('returns one second when there is no dig speed', () => {
		expect(digTimePerDig(0)).toBe(1)
		expect(digTimePerDig(-1)).toBe(1)
	})

	it('gets faster as dig speed rises', () => {
		expect(digTimePerDig(200)).toBeLessThan(digTimePerDig(100))
		expect(digTimePerDig(100)).toBeLessThan(digTimePerDig(50))
	})
})

describe('itemsPerPan', () => {
	it('is zero for an empty pan', () => {
		expect(itemsPerPan(0)).toBe(0)
		expect(itemsPerPan(-10)).toBe(0)
	})

	it('is the square root of the capacity times 1.08', () => {
		expect(itemsPerPan(100)).toBeCloseTo(Math.sqrt(100) * 1.08, 10)
	})
})

describe('weightMultiplier', () => {
	it('is one without a boost', () => {
		expect(weightMultiplier(0)).toBe(1)
	})

	it('adds the boost as a percentage', () => {
		expect(weightMultiplier(100)).toBe(2)
		expect(weightMultiplier(50)).toBe(1.5)
	})

	it('handles a negative boost', () => {
		expect(weightMultiplier(-50)).toBe(0.5)
	})
})

describe('sellMultiplier', () => {
	it('is one without a boost', () => {
		expect(sellMultiplier(0)).toBe(1)
	})

	it('adds the boost as a percentage', () => {
		expect(sellMultiplier(100)).toBe(2)
	})
})

describe('modifierLuck', () => {
	it('is capped at fifty', () => {
		expect(modifierLuck(100000, 0)).toBe(50)
	})

	it('is zero with no luck and no boost', () => {
		expect(modifierLuck(0, 0)).toBe(0)
	})
})

describe('effectiveModifierBoost', () => {
	it('is unchanged with no flags', () => {
		expect(effectiveModifierBoost(100)).toBe(100)
	})

	it('doubles for the solar magnifier', () => {
		expect(effectiveModifierBoost(100, true, false)).toBe(200)
	})

	it('doubles for the modifier surge', () => {
		expect(effectiveModifierBoost(100, false, true)).toBe(200)
	})

	it('doubles twice when both flags are set', () => {
		expect(effectiveModifierBoost(100, true, true)).toBe(400)
	})

	it('doubles only for the modifier surge when asked for the modifier job', () => {
		// The solar magnifier is deliberately ignored here: it doubles for job 1
		// only. calculateModifierOdds relies on that asymmetry.
		expect(effectiveModifierBoost(100, true, false, true)).toBe(100)
		expect(effectiveModifierBoost(100, true, true, true)).toBe(200)
	})
})

describe('pctOresModified', () => {
	it('is zero without a modifier boost', () => {
		expect(pctOresModified(0)).toBe(0)
		expect(pctOresModified(-5)).toBe(0)
	})

	it('is capped at 99.4', () => {
		expect(pctOresModified(1900)).toBe(99.4)
		expect(pctOresModified(10000)).toBe(99.4)
	})

	it('rises with the modifier boost', () => {
		expect(pctOresModified(100)).toBeGreaterThan(0)
		expect(pctOresModified(500)).toBeGreaterThan(pctOresModified(100))
		expect(pctOresModified(1000)).toBeGreaterThan(pctOresModified(500))
	})
})

describe('modifierDistribution', () => {
	it('is all zeroes without a modifier boost', () => {
		const dist = modifierDistribution(0)
		for (const mod of Object.keys(MODIFIER_BASE_DISTRIBUTION)) {
			expect(dist[mod]).toBe(0)
		}
	})

	it('covers every modifier in the base distribution', () => {
		const dist = modifierDistribution(500)
		expect(Object.keys(dist).sort()).toEqual(
			Object.keys(MODIFIER_BASE_DISTRIBUTION).sort(),
		)
	})

	it('sums to the percentage of ores modified', () => {
		const effective = 300
		const dist = modifierDistribution(effective)
		const total = Object.values(dist).reduce((a, b) => a + b, 0)
		expect(total).toBeCloseTo(pctOresModified(effective), 6)
	})
})

describe('qualityMultiplier', () => {
	it('is one by default', () => {
		expect(qualityMultiplier()).toBe(1)
		expect(qualityMultiplier(false, false)).toBe(1)
	})

	it('is 0.51 when autopanning without a mastered shovel', () => {
		expect(qualityMultiplier(true, false)).toBe(0.51)
	})

	it('is one when autopanning with a mastered shovel', () => {
		expect(qualityMultiplier(true, true)).toBe(1)
	})
})

describe('pansPerHour', () => {
	it('is positive for sane inputs', () => {
		const pph = pansPerHour(100, 50, 100, 50, 500)
		expect(pph).toBeGreaterThan(0)
		expect(Number.isFinite(pph)).toBe(true)
	})

	it('is 3600 when a pan takes no measurable time', () => {
		// With no dig speed a dig still takes the fallback second, so a pan
		// takes one second and 3600 pans fit in an hour.
		expect(pansPerHour(0, 0, 0, 0, 0)).toBe(3600)
	})
})

describe('calculateEV', () => {
	const baseInputs = {
		locationDropTable: [{ base_price: 100, base_weight: 1, rarity: 'common' }],
		luck: 0,
		modifierBoost: 0,
		capacity: 100,
	}

	it('returns the shape the page reads', () => {
		const result = calculateEV(baseInputs)
		expect(result).toHaveProperty('evPerPan')
		expect(result).toHaveProperty('itemsPerPan')
		expect(result).toHaveProperty('qualityMultiplier')
		expect(result).toHaveProperty('effectiveModifierBoost')
		expect(result).toHaveProperty('modifierDistribution')
		expect(result).toHaveProperty('pctModified')
	})

	// TODO: the drop chance field is not in the item data yet, so `base_price`
	// is used as a proxy for it. The expected value below is provisional and
	// will change when the real drop chance is available.
	it('sums base_price squared times the weight multiplier', () => {
		const result = calculateEV(baseInputs)
		expect(result.evPerPan).toBeCloseTo(100 * 100 * 1, 6)
	})

	// TODO: `luck` and `quality` are not applied by the expected-value sum
	// yet. Pinned so the gap is visible rather than silent.
	it('ignores luck and quality', () => {
		const plain = calculateEV(baseInputs)
		const lucky = calculateEV({ ...baseInputs, luck: 500, quality: 0.5 })
		expect(lucky.evPerPan).toBe(plain.evPerPan)
	})

	it('applies the modifier boost to the effective boost', () => {
		const result = calculateEV({ ...baseInputs, modifierBoost: 100 })
		expect(result.effectiveModifierBoost).toBe(100)
	})

	it('counts the items in a pan from the capacity', () => {
		const result = calculateEV({ ...baseInputs, capacity: 100 })
		expect(result.itemsPerPan).toBeCloseTo(Math.sqrt(100) * 1.08, 10)
	})
})

describe('calculateTTG', () => {
	const baseInputs = {
		goalValue: 1_000_000,
		locationEvPerPan: 100,
		capacity: 100,
		digStrength: 50,
		digSpeed: 100,
		shakeStrength: 50,
		shakeSpeed: 500,
	}

	it('returns the shape the page reads', () => {
		const result = calculateTTG(baseInputs)
		expect(result).toHaveProperty('hoursToGoal')
		expect(result).toHaveProperty('pansPerHour')
		expect(result).toHaveProperty('evPerHour')
		expect(result).toHaveProperty('evPerPan')
		expect(result).toHaveProperty('digsPerPan')
		expect(result).toHaveProperty('digTimePerDig')
		expect(result).toHaveProperty('shakeTime')
	})

	it('takes the hours to the goal from the hourly value', () => {
		const result = calculateTTG(baseInputs)
		// Each field is rounded on its own, so the product of the rounded
		// values is not exactly the rounded product. The tolerance covers the
		// rounding the output applies.
		expect(Math.abs(result.evPerHour - result.evPerPan * result.pansPerHour)).toBeLessThan(0.5)
		expect(Math.abs(result.hoursToGoal - baseInputs.goalValue / result.evPerHour)).toBeLessThan(0.5)
	})

	it('is infinite when nothing can be earned', () => {
		const result = calculateTTG({ ...baseInputs, locationEvPerPan: 0 })
		expect(result.hoursToGoal).toBe(Infinity)
		expect(result.evPerHour).toBe(0)
	})
})

describe('calculateModifierOdds', () => {
	it('returns the shape the page reads', () => {
		const result = calculateModifierOdds({ panelModifierBoost: 100 })
		expect(result).toHaveProperty('effectiveModifierBoostJob1')
		expect(result).toHaveProperty('effectiveModifierBoostJob2')
		expect(result).toHaveProperty('pctOresModified')
		expect(result).toHaveProperty('modifierDistribution')
		expect(result).toHaveProperty('note')
	})

	it('doubles for job 1 and job 2 differently', () => {
		const result = calculateModifierOdds({
			panelModifierBoost: 100,
			solarMagnifier: true,
			modifierSurge: true,
		})
		// The solar magnifier doubles job 1 only; the surge doubles both.
		expect(result.effectiveModifierBoostJob1).toBe(400)
		expect(result.effectiveModifierBoostJob2).toBe(200)
	})

	it('explains the asymmetry in its note', () => {
		const result = calculateModifierOdds({ panelModifierBoost: 100 })
		expect(result.note).toContain('Solar Magnifier')
		expect(result.note).toContain('Job 1')
	})
})

describe('calculateBestPan', () => {
	const pans = [
		{
			name: 'Rusty Pan',
			capacity: 50,
			digStrength: 10,
			shakeStrength: 10,
			shakeSpeed: 100,
			luck: 0,
			sizeBoost: 0,
			modifierBoost: 0,
		},
		{
			name: 'Steel Pan',
			capacity: 100,
			digStrength: 20,
			shakeStrength: 20,
			shakeSpeed: 200,
			luck: 10,
			sizeBoost: 5,
			modifierBoost: 5,
		},
	]

	const baseInputs = {
		pans,
		digStrength: 50,
		shakeStrength: 50,
		shakeSpeed: 500,
	}

	it('returns the shape the page reads', () => {
		const result = calculateBestPan(baseInputs)
		expect(result).toHaveProperty('criteria')
		expect(result).toHaveProperty('recommendations')
	})

	it('recommends every pan when nothing is filtered out', () => {
		const result = calculateBestPan(baseInputs)
		expect(result.recommendations).toHaveLength(2)
	})

	it('scores each recommendation', () => {
		const result = calculateBestPan(baseInputs)
		for (const rec of result.recommendations) {
			expect(Number.isFinite(rec.score)).toBe(true)
			expect(rec.pan).toHaveProperty('name')
		}
	})

	it('filters out pans below the target capacity', () => {
		const result = calculateBestPan({ ...baseInputs, targetCapacity: 60 })
		expect(result.recommendations).toHaveLength(1)
		expect(result.recommendations[0].pan.name).toBe('Steel Pan')
	})

	it('filters out pans below the minimum luck', () => {
		const result = calculateBestPan({ ...baseInputs, minLuck: 5 })
		expect(result.recommendations).toHaveLength(1)
		expect(result.recommendations[0].pan.name).toBe('Steel Pan')
	})

	it('filters out pans below the minimum size boost', () => {
		const result = calculateBestPan({ ...baseInputs, minSizeBoost: 1 })
		expect(result.recommendations).toHaveLength(1)
		expect(result.recommendations[0].pan.name).toBe('Steel Pan')
	})

	it('filters out pans below the minimum modifier boost', () => {
		const result = calculateBestPan({ ...baseInputs, minModifierBoost: 1 })
		expect(result.recommendations).toHaveLength(1)
		expect(result.recommendations[0].pan.name).toBe('Steel Pan')
	})

	it('returns nothing when every pan is filtered out', () => {
		const result = calculateBestPan({ ...baseInputs, targetCapacity: 1000 })
		expect(result.recommendations).toHaveLength(0)
	})
})

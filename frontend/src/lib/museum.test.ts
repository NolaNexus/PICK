import { describe, it, expect } from 'vitest'
import {
	getModifierRider,
	weightFactor,
	parseBonusStat,
	calculateEffectiveBoost,
	calculateUnlockCosts,
	calculateWeightGate,
	calculateMuseumComparison,
	calculateMuseumOptimizer,
	MUSEUM_DISPLAYS,
	RARITY_ORDER,
	MODIFIER_RARITY_MULTIPLIERS,
	type CurrentDisplay,
} from './museum'

describe('getModifierRider', () => {
	it('returns nothing without a modifier', () => {
		expect(getModifierRider(null, 'Common')).toEqual({})
		expect(getModifierRider(undefined, 'Common')).toEqual({})
		expect(getModifierRider('', 'Common')).toEqual({})
	})

	it('returns nothing for an unknown modifier', () => {
		expect(getModifierRider('NotAModifier', 'Common')).toEqual({})
	})

	it('scales the base bonuses by the rarity multiplier', () => {
		const rider = getModifierRider('Perfect', 'Common')
		const multiplier = MODIFIER_RARITY_MULTIPLIERS['Common']
		expect(rider['Luck']).toBeCloseTo(1 * multiplier, 10)
		expect(rider['Capacity']).toBeCloseTo(1 * multiplier, 10)
		expect(rider['Size Boost']).toBeCloseTo(1 * multiplier, 10)
	})

	it('doubles the amount for the treasured modifier', () => {
		const common = getModifierRider('Treasured', 'Common')
		const multiplier = MODIFIER_RARITY_MULTIPLIERS['Common']
		expect(common['Luck']).toBeCloseTo(2 * multiplier * 2, 10)
	})

	it('is zero for a rarity with no multiplier', () => {
		// An unknown rarity has no multiplier, so the rider is present but
		// every bonus is zero.
		const rider = getModifierRider('Perfect', 'NotARarity')
		expect(rider).toEqual({ Luck: 0, Capacity: 0, 'Size Boost': 0 })
	})
})

describe('weightFactor', () => {
	it('is one when there is no minimum', () => {
		expect(weightFactor(10, 0)).toBe(1)
		expect(weightFactor(10, -1)).toBe(1)
	})

	it('is one at or above the minimum', () => {
		expect(weightFactor(100, 100)).toBe(1)
		expect(weightFactor(200, 100)).toBe(1)
	})

	it('is the fraction of the minimum below it', () => {
		expect(weightFactor(50, 100)).toBeCloseTo(0.5, 10)
	})
})

describe('parseBonusStat', () => {
	it('returns nothing for an empty string', () => {
		expect(parseBonusStat(null)).toEqual([])
		expect(parseBonusStat(undefined)).toEqual([])
		expect(parseBonusStat('')).toEqual([])
	})

	it('reads a single stat', () => {
		expect(parseBonusStat('{{Stat|Luck}}')).toEqual([['Luck', 1]])
	})

	it('reads several stats', () => {
		expect(parseBonusStat('{{Stat|Luck,Capacity}}')).toEqual([
			['Luck', 1],
			['Capacity', 1],
		])
	})

	it('reads a negative stat', () => {
		expect(parseBonusStat('{{Stat|-Luck}}')).toEqual([['Luck', -1]])
	})

	it('reads a multiplier', () => {
		expect(parseBonusStat('{{Stat|Luck×2}}')).toEqual([['Luck', 2]])
	})

	it('skips empty parts', () => {
		expect(parseBonusStat('{{Stat|Luck,,Capacity}}')).toEqual([
			['Luck', 1],
			['Capacity', 1],
		])
	})
})

describe('calculateEffectiveBoost', () => {
	it('is empty for an ore with no bonus stat', () => {
		expect(calculateEffectiveBoost({}, 100, null, 'Common')).toEqual({})
	})

	it('applies the boost times the weight factor', () => {
		// min_kg 100, so 50kg is half the weight.
		const boost = calculateEffectiveBoost(
			{ min_kg: 100, bonus_stat: '{{Stat|Luck}}', max_boost: '0.5×' },
			50,
			null,
			'Common',
		)
		expect(boost['Luck']).toBeCloseTo(0.5 * 0.5, 10)
	})

	it('is at full weight at or above the minimum', () => {
		const boost = calculateEffectiveBoost(
			{ min_kg: 100, bonus_stat: '{{Stat|Luck}}', max_boost: '0.5×' },
			100,
			null,
			'Common',
		)
		expect(boost['Luck']).toBeCloseTo(0.5, 10)
	})

	it('adds the modifier rider to the base boost', () => {
		const withoutModifier = calculateEffectiveBoost(
			{ bonus_stat: '{{Stat|Luck}}', max_boost: '0.5×' },
			100,
			null,
			'Common',
		)
		const withModifier = calculateEffectiveBoost(
			{ bonus_stat: '{{Stat|Luck}}', max_boost: '0.5×' },
			100,
			'Perfect',
			'Common',
		)
		expect(withModifier['Luck']).toBeGreaterThan(withoutModifier['Luck'])
	})
})

describe('calculateUnlockCosts', () => {
	it('costs nothing when everything is free', () => {
		// Common, Uncommon, Rare and Epic each have one free slot, but the
		// locked slots still cost, so an empty museum is not free.
		const costs = calculateUnlockCosts([])
		expect(costs.money_cost).toBeGreaterThan(0)
		expect(costs.shards_cost).toBeGreaterThan(0)
	})

	it('drops as slots are unlocked', () => {
		const empty = calculateUnlockCosts([])
		const oneUnlocked = calculateUnlockCosts([
			{
				slot_id: 'common-0',
				rarity: 'Common',
				slot_index: 0,
				ore_name: 'Ore',
				kg: 1,
			},
		])
		expect(oneUnlocked.money_cost).toBeLessThan(empty.money_cost)
		expect(oneUnlocked.shards_cost).toBeLessThan(empty.shards_cost)
	})

	it('reports the same totals in both places', () => {
		const costs = calculateUnlockCosts([])
		expect(costs.total_cost.money).toBe(costs.money_cost)
		expect(costs.total_cost.shards).toBe(costs.shards_cost)
	})

	it('never costs less than zero', () => {
		const many: CurrentDisplay[] = []
		for (const rarity of RARITY_ORDER) {
			const info = MUSEUM_DISPLAYS[rarity]
			for (let i = 0; i < info.total + 5; i++) {
				many.push({
					slot_id: `${rarity}-${i}`,
					rarity,
					slot_index: i,
					ore_name: 'Ore',
					kg: 1,
				})
			}
		}
		const costs = calculateUnlockCosts(many)
		expect(costs.money_cost).toBe(0)
		expect(costs.shards_cost).toBe(0)
	})
})

describe('calculateWeightGate', () => {
	const oreDatabase = {
		'Iron|Common': { min_kg: 100 },
	}

	it('reports the minimum, the current and the effective weight', () => {
		const result = calculateWeightGate({
			availableOres: [{ name: 'Iron', rarity: 'Common', kg: 50 }],
			sizeBoost: 0,
			oreDatabase,
		})
		expect(result).toHaveLength(1)
		expect(result[0].ore_name).toBe('Iron')
		expect(result[0].rarity).toBe('Common')
		expect(result[0].min_kg).toBe(100)
		expect(result[0].current_kg).toBe(50)
		expect(result[0].effective_kg).toBe(50)
		expect(result[0].meets_requirement).toBe(false)
	})

	it('counts a size boost towards the effective weight', () => {
		const result = calculateWeightGate({
			availableOres: [{ name: 'Iron', rarity: 'Common', kg: 50 }],
			sizeBoost: 100,
			oreDatabase,
		})
		expect(result[0].effective_kg).toBe(100)
		expect(result[0].meets_requirement).toBe(true)
	})

	it('treats an unknown ore as having no minimum', () => {
		const result = calculateWeightGate({
			availableOres: [{ name: 'Unknown', rarity: 'Common', kg: 1 }],
			sizeBoost: 0,
			oreDatabase,
		})
		expect(result[0].min_kg).toBe(0)
		expect(result[0].meets_requirement).toBe(true)
	})
})

describe('calculateMuseumComparison', () => {
	const oreDatabase = {
		'Iron|Common': { min_kg: 100, bonus_stat: '{{Stat|Luck}}', max_boost: '0.5×' },
		'Gold|Rare': { min_kg: 50, bonus_stat: '{{Stat|Capacity}}', max_boost: '1×' },
	}

	const currentDisplays: CurrentDisplay[] = [
		{
			slot_id: 'common-0',
			rarity: 'Common',
			slot_index: 0,
			ore_name: 'Iron',
			kg: 100,
			modifier: null,
		},
	]

	const availableOres = [
		{ name: 'Iron', rarity: 'Common', kg: 100, modifier: null },
		{ name: 'Gold', rarity: 'Rare', kg: 50, modifier: null },
	]

	const baseInputs = {
		currentDisplays,
		availableOres,
		targetStats: {},
		sizeBoost: 0,
		oreDatabase,
	}

	it('compares the current display and the empty slots that could be filled', () => {
		// One filled Common slot, two more Common slots, and three Rare slots
		// where an ore is available to place.
		const result = calculateMuseumComparison(baseInputs)
		expect(result.slot_comparisons).toHaveLength(6)
		expect(result.slot_comparisons[0].slot_id).toBe('common-0')
		expect(result.slot_comparisons[0].current_ore).toBe('Iron')
	})

	it('keeps the fields the old stale type discarded', () => {
		// These ten fields are what the retired `SlotRecommendation` type was
		// missing. They are asserted here so they cannot go missing again.
		const result = calculateMuseumComparison(baseInputs)
		const slot = result.slot_comparisons[0]
		expect(slot).toHaveProperty('current_ore')
		expect(slot).toHaveProperty('current_kg')
		expect(slot).toHaveProperty('current_modifier')
		expect(slot).toHaveProperty('current_boost')
		expect(slot).toHaveProperty('best_available_ore')
		expect(slot).toHaveProperty('best_available_kg')
		expect(slot).toHaveProperty('best_available_modifier')
		expect(slot).toHaveProperty('best_boost')
		expect(slot).toHaveProperty('stat_deltas')
		expect(slot).toHaveProperty('recommendation')
	})

	it('reports an empty slot as having no current ore', () => {
		const result = calculateMuseumComparison(baseInputs)
		const empty = result.slot_comparisons.find((s) => s.current_ore === null)
		expect(empty).toBeDefined()
		expect(empty?.current_kg).toBe(0)
	})

	it('produces both a current and an optimised total', () => {
		const result = calculateMuseumComparison(baseInputs)
		expect(result.current_total_stats).toBeDefined()
		expect(result.optimized_total_stats).toBeDefined()
	})

	it('breaks the totals down by rarity', () => {
		const result = calculateMuseumComparison(baseInputs)
		expect(result.by_rarity['Common']).toBeDefined()
		expect(result.by_rarity['Common'].total_slots).toBe(MUSEUM_DISPLAYS['Common'].total)
	})
})

describe('calculateMuseumOptimizer', () => {
	it('returns the shape the page reads', () => {
		const result = calculateMuseumOptimizer({
			availableOres: [{ name: 'Iron', rarity: 'Common', kg: 100, modifier: null }],
			unlockedDisplays: [],
			targetStats: {},
			sizeBoost: 0,
		})
		expect(result).toHaveProperty('slot_recommendations')
		expect(result).toHaveProperty('total_stats')
		expect(result).toHaveProperty('by_rarity')
		expect(result).toHaveProperty('unlock_costs')
		expect(result).toHaveProperty('weight_gate_info')
	})

	it('recommends a slot per unlocked display', () => {
		const result = calculateMuseumOptimizer({
			availableOres: [{ name: 'Iron', rarity: 'Common', kg: 100, modifier: null }],
			unlockedDisplays: [
				{
					slot_id: 'common-0',
					rarity: 'Common',
					slot_index: 0,
					ore_name: 'Iron',
					kg: 100,
					modifier: null,
				},
			],
			targetStats: {},
			sizeBoost: 0,
		})
		expect(result.slot_recommendations.length).toBeGreaterThan(0)
		for (const slot of result.slot_recommendations) {
			expect(slot).toHaveProperty('slot_id')
			expect(slot).toHaveProperty('recommendation')
			expect(slot).toHaveProperty('stat_deltas')
		}
	})

	it('reports the unlock costs of the museum', () => {
		const result = calculateMuseumOptimizer({
			availableOres: [],
			unlockedDisplays: [],
			targetStats: {},
			sizeBoost: 0,
		})
		expect(result.unlock_costs.money_cost).toBeGreaterThanOrEqual(0)
		expect(result.unlock_costs.shards_cost).toBeGreaterThanOrEqual(0)
	})
})

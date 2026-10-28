import { describe, it, expect } from 'vitest'
import {
  readTaxonomy,
  labelOf,
  areaOf,
  groupOf,
  typesInArea,
  typesInGroup,
  groupsInArea,
} from './taxonomy'
import type { TaxonomyEntry } from './snapshot.types'

const entry = (over: Partial<TaxonomyEntry> = {}): TaxonomyEntry => ({
  type: 'pan',
  area: 'items',
  group: 'gear',
  label: 'Pans',
  kind: 'item',
  listed: true,
  ...over,
})

describe('readTaxonomy', () => {
  it('reads a well-formed entry', () => {
    const taxonomy = readTaxonomy([entry()])
    expect(taxonomy.entries.get('pan')).toEqual({
      type: 'pan',
      area: 'items',
      group: 'gear',
      label: 'Pans',
      kind: 'item',
      listed: true,
    })
  })

  it('falls back to the items area', () => {
    const taxonomy = readTaxonomy([entry({ area: undefined as never })])
    expect(taxonomy.entries.get('pan')?.area).toBe('items')
  })

  it('humanises a missing label', () => {
    const taxonomy = readTaxonomy([entry({ label: '' })])
    expect(taxonomy.entries.get('pan')?.label).toBe('Pan')
  })

  it('humanises a multi-word type', () => {
    const taxonomy = readTaxonomy([entry({ type: 'enchant_book', label: '' })])
    expect(taxonomy.entries.get('enchant_book')?.label).toBe('Enchant Book')
  })

  it('defaults the kind to item', () => {
    const taxonomy = readTaxonomy([entry({ kind: undefined as never })])
    expect(taxonomy.entries.get('pan')?.kind).toBe('item')
  })

  it('defaults listed to true', () => {
    const taxonomy = readTaxonomy([entry({ listed: undefined as never })])
    expect(taxonomy.entries.get('pan')?.listed).toBe(true)
  })

  it('keeps an explicit listed of false', () => {
    const taxonomy = readTaxonomy([entry({ listed: false })])
    expect(taxonomy.entries.get('pan')?.listed).toBe(false)
  })

  it('returns an empty taxonomy for a non-array', () => {
    const taxonomy = readTaxonomy('not an array')
    expect(taxonomy.entries.size).toBe(0)
    expect(taxonomy.areas).toEqual([])
  })

  it('skips an entry with no type', () => {
    const taxonomy = readTaxonomy([entry({ type: undefined as never })])
    expect(taxonomy.entries.size).toBe(0)
  })

  it('lists the areas in sorted order', () => {
    const taxonomy = readTaxonomy([
      entry({ type: 'pan', area: 'items' }),
      entry({ type: 'npc', area: 'world' }),
      entry({ type: 'mineral', area: 'minerals' }),
    ])
    expect(taxonomy.areas).toEqual(['items', 'minerals', 'world'])
  })

  it('groups the types under their group', () => {
    const taxonomy = readTaxonomy([
      entry({ type: 'pan', group: 'gear' }),
      entry({ type: 'shovel', group: 'gear' }),
    ])
    expect(taxonomy.groups.get('gear')).toEqual(['pan', 'shovel'])
  })
})

describe('labelOf', () => {
  it('returns the label the server gave', () => {
    const taxonomy = readTaxonomy([entry({ label: 'Pans' })])
    expect(labelOf(taxonomy, 'pan')).toBe('Pans')
  })

  it('humanises an unknown type', () => {
    const taxonomy = readTaxonomy([])
    expect(labelOf(taxonomy, 'enchant_book')).toBe('Enchant Book')
  })
})

describe('areaOf', () => {
  it('returns the area the server gave', () => {
    const taxonomy = readTaxonomy([entry({ area: 'world' })])
    expect(areaOf(taxonomy, 'pan')).toBe('world')
  })

  it('falls back to items for an unknown type', () => {
    const taxonomy = readTaxonomy([])
    expect(areaOf(taxonomy, 'nope')).toBe('items')
  })
})

describe('groupOf', () => {
  it('returns the group the server gave', () => {
    const taxonomy = readTaxonomy([entry({ group: 'gear' })])
    expect(groupOf(taxonomy, 'pan')).toBe('gear')
  })

  it('is null for an unknown type', () => {
    const taxonomy = readTaxonomy([])
    expect(groupOf(taxonomy, 'nope')).toBeNull()
  })
})

describe('typesInArea', () => {
  it('returns the listed types of an area', () => {
    const taxonomy = readTaxonomy([
      entry({ type: 'pan', area: 'items' }),
      entry({ type: 'shovel', area: 'items' }),
      entry({ type: 'npc', area: 'world' }),
    ])
    expect(typesInArea(taxonomy, 'items')).toEqual(['pan', 'shovel'])
  })

  it('leaves out the types that are not listed', () => {
    const taxonomy = readTaxonomy([
      entry({ type: 'pan', area: 'items' }),
      entry({ type: 'mineral', area: 'items', listed: false }),
    ])
    expect(typesInArea(taxonomy, 'items')).toEqual(['pan'])
  })
})

describe('typesInGroup', () => {
  it('returns the listed types of a group', () => {
    const taxonomy = readTaxonomy([
      entry({ type: 'pan', group: 'gear' }),
      entry({ type: 'npc', group: 'people' }),
    ])
    expect(typesInGroup(taxonomy, 'gear')).toEqual(['pan'])
  })

  it('leaves out the types that are not listed', () => {
    const taxonomy = readTaxonomy([entry({ type: 'mineral', group: 'gear', listed: false })])
    expect(typesInGroup(taxonomy, 'gear')).toEqual([])
  })
})

describe('groupsInArea', () => {
  it('returns each group once, in the order the server gave them', () => {
    const taxonomy = readTaxonomy([
      entry({ type: 'pan', group: 'gear' }),
      entry({ type: 'shovel', group: 'gear' }),
      entry({ type: 'potion', group: 'consumables' }),
    ])
    expect(groupsInArea(taxonomy, 'items')).toEqual(['gear', 'consumables'])
  })

  it('leaves out a type with no group', () => {
    const taxonomy = readTaxonomy([entry({ type: 'pan', group: null })])
    expect(groupsInArea(taxonomy, 'items')).toEqual([])
  })
})

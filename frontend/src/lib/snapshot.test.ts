import { describe, it, expect } from 'vitest'
import {
  normalizeSnapshot,
  snapshotCache,
  SNAPSHOT_SCHEMA_VERSION,
  type SnapshotData,
} from './snapshot'
import type { Item } from './snapshot.types'

const item = (over: Partial<Item> = {}): Item => ({
  id: 1,
  type: 'pan',
  name: 'Rusty Pan',
  slug: 'pan-rusty-pan',
  data: {},
  image_url: null,
  description: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...over,
})

describe('normalizeSnapshot', () => {
  it('fills in the defaults for an empty payload', () => {
    const result = normalizeSnapshot(null)
    expect(result.schema_version).toBe(SNAPSHOT_SCHEMA_VERSION)
    expect(result.taxonomy).toEqual([])
    expect(result.items).toEqual([])
    expect(result.formulas).toEqual([])
    expect(result.wiki_pages).toEqual([])
    expect(result.counts).toEqual({ items: 0, formulas: 0, wiki_pages: 0 })
  })

  it('keeps the counts the server gave', () => {
    const result = normalizeSnapshot({
      counts: { items: 5, formulas: 2, wiki_pages: 1 },
    })
    expect(result.counts).toEqual({ items: 5, formulas: 2, wiki_pages: 1 })
  })

  it('derives the counts from the arrays when they are missing', () => {
    const result = normalizeSnapshot({
      items: [item(), item({ id: 2 })],
      formulas: [],
      wiki_pages: [],
    })
    expect(result.counts.items).toBe(2)
    expect(result.counts.formulas).toBe(0)
    expect(result.counts.wiki_pages).toBe(0)
  })

  it('keeps the items it is given', () => {
    const items = [item()]
    const result = normalizeSnapshot({ items })
    expect(result.items).toEqual(items)
  })

  it('reads the game version and the last scrape from the top level', () => {
    const result = normalizeSnapshot({
      game_version: { version: '1.2.3', detected_at: '2026-01-01T00:00:00Z' },
      last_scrape: { status: 'ok', pages_scraped: 21 },
    })
    expect(result.meta.game_version?.version).toBe('1.2.3')
    expect(result.meta.game_version?.detected_at).toBe('2026-01-01T00:00:00Z')
    expect(result.meta.last_scrape?.status).toBe('ok')
    expect(result.meta.last_scrape?.pages_scraped).toBe(21)
  })

  it('reads the game version and the last scrape from meta', () => {
    const result = normalizeSnapshot({
      meta: {
        game_version: { version: '1.2.3', detected_at: '2026-01-01T00:00:00Z' },
        last_scrape: { status: 'ok', pages_scraped: 21 },
      },
    })
    expect(result.meta.game_version?.version).toBe('1.2.3')
    expect(result.meta.last_scrape?.pages_scraped).toBe(21)
  })

  it('uses an empty game version and scrape when there are none', () => {
    const result = normalizeSnapshot({})
    expect(result.meta.game_version).toEqual({
      version: null,
      detected_at: null,
    })
    expect(result.meta.last_scrape).toEqual({
      status: 'never',
      started_at: null,
      finished_at: null,
      pages_scraped: 0,
      pages_changed: 0,
      pages_errors: 0,
    })
  })

  it('keeps a generated_at and does not invent one when it is there', () => {
    const result = normalizeSnapshot({ generated_at: '2026-01-01T00:00:00Z' })
    expect(result.generated_at).toBe('2026-01-01T00:00:00Z')
  })
})

describe('snapshotCache.isStale', () => {
  const data = (generatedAt: string): SnapshotData =>
    normalizeSnapshot({ generated_at: generatedAt })

  it('is not stale for a snapshot generated now', () => {
    const fresh = data(new Date().toISOString())
    expect(snapshotCache.isStale(fresh)).toBe(false)
  })

  it('is stale for a snapshot generated long ago', () => {
    const old = data('2020-01-01T00:00:00Z')
    expect(snapshotCache.isStale(old)).toBe(true)
  })

  it('is stale when there is no snapshot at all', () => {
    expect(snapshotCache.isStale(null)).toBe(true)
  })
})

describe('snapshotCache.getItems', () => {
  it('returns the items of the snapshot', () => {
    const items = [item(), item({ id: 2, name: 'Steel Pan', slug: 'pan-steel-pan' })]
    const data = normalizeSnapshot({ items })
    expect(snapshotCache.getItems(data)).toEqual(items)
  })
})

describe('snapshotCache.getItem', () => {
  it('finds an item by its slug', () => {
    const items = [item(), item({ id: 2, name: 'Steel Pan', slug: 'pan-steel-pan' })]
    const data = normalizeSnapshot({ items })
    expect(snapshotCache.getItem(data, 'pan-steel-pan')?.name).toBe('Steel Pan')
  })

  it('is undefined for a slug that is not there', () => {
    const data = normalizeSnapshot({ items: [item()] })
    expect(snapshotCache.getItem(data, 'nope')).toBeUndefined()
  })
})

describe('snapshotCache.getTypes', () => {
  it('returns the distinct types in order', () => {
    const data = normalizeSnapshot({
      items: [item({ type: 'pan' }), item({ id: 2, type: 'npc' }), item({ id: 3, type: 'pan' })],
    })
    expect(snapshotCache.getTypes(data)).toEqual(['npc', 'pan'])
  })
})

describe('snapshotCache.searchItems', () => {
  const items = [
    item({ name: 'Rusty Pan', slug: 'pan-rusty-pan', description: 'A rusty pan' }),
    item({ id: 2, name: 'Steel Pan', slug: 'pan-steel-pan', description: 'A steel pan' }),
    item({
      id: 3,
      name: 'Copper Ore',
      slug: 'mineral-copper-ore',
      type: 'mineral',
      description: null,
      data: { areas: ['Oasis'] },
    }),
  ]

  it('finds an item by its name', () => {
    const data = normalizeSnapshot({ items })
    const found = snapshotCache.searchItems(data, 'steel')
    expect(found).toHaveLength(1)
    expect(found[0].name).toBe('Steel Pan')
  })

  it('filters by type', () => {
    const data = normalizeSnapshot({ items })
    const found = snapshotCache.searchItems(data, '', 'mineral')
    expect(found).toHaveLength(1)
    expect(found[0].name).toBe('Copper Ore')
  })

  it('searches the item data for a location', () => {
    const data = normalizeSnapshot({ items })
    const found = snapshotCache.searchItems(data, '', null, 'Oasis')
    expect(found).toHaveLength(1)
    expect(found[0].name).toBe('Copper Ore')
  })
})

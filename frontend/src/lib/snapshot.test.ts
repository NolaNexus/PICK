import { describe, it, expect } from 'vitest'
import {
  normalizeSnapshot,
  snapshotCache,
  SNAPSHOT_SCHEMA_VERSION,
  type SnapshotData,
} from './snapshot'
import type { Item } from './snapshot.types'

const item = (over: Partial<Item> = {}): Item => ({
  type: 'pan',
  name: 'Rusty Pan',
  slug: 'pan-rusty-pan',
  data: {},
  image_url: null,
  description: null,
  ...over,
})

describe('normalizeSnapshot', () => {
  it('fills in the defaults for an empty payload', () => {
    const result = normalizeSnapshot(null)
    expect(result.schema_version).toBe(SNAPSHOT_SCHEMA_VERSION)
    expect(result.taxonomy).toEqual([])
    expect(result.items).toEqual([])
    expect(result.counts).toEqual({ items: 0 })
  })

  it('keeps the counts the server gave', () => {
    const result = normalizeSnapshot({
      counts: { items: 5 },
    })
    expect(result.counts).toEqual({ items: 5 })
  })

  it('derives the counts from the arrays when they are missing', () => {
    const result = normalizeSnapshot({
      items: [item(), item({ slug: 'pan-second' })],
    })
    expect(result.counts.items).toBe(2)
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
    expect(result.game_version!.version).toBe('1.2.3')
    expect(result.game_version!.detected_at).toBe('2026-01-01T00:00:00Z')
    expect(result.last_scrape!.status).toBe('ok')
    expect(result.last_scrape!.pages_scraped).toBe(21)
  })

  it('uses an empty game version and scrape when there are none', () => {
    const result = normalizeSnapshot({})
    expect(result.game_version).toEqual({
      version: null,
      detected_at: null,
    })
    expect(result.last_scrape).toEqual({
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

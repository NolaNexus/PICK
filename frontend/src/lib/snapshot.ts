import type { ItemResponse } from "@/api/pick.schemas"
import request from "@/api/client"
import { dbGet, dbPut, dbClear } from "./idb"

const STORE = "snapshot"
const KEY = "main"
const STALE_MS = 1000 * 60 * 60 * 24 // 24 hours

export interface SnapshotFormula {
  id: number
  formula_id: string
  name: string
  description: string | null
  formula: string
  params: unknown
  confidence: string
  source_url: string | null
  patch_version: string | null
  created_at: string | null
}

export interface SnapshotNews {
  id: number
  source: string
  external_id: string
  title: string
  url: string
  author: string | null
  score: number
  published_at: string | null
  fetched_at: string | null
  content: string | null
  tags: string[]
}

export interface SnapshotWikiPage {
  id: number
  title: string
  page_id: number
  last_revision_id: number
  last_scraped: string | null
  content_hash: string
  namespace: number
}

export interface SnapshotMeta {
  game_version: {
    version: string | null
    detected_at: string | null
    triggered_full_scrape: number
  } | null
  last_scrape: {
    status: string | null
    started_at: string | null
    finished_at: string | null
    pages_scraped: number
    pages_changed: number
    pages_errors: number
  } | null
}

export interface SnapshotData {
  generated_at: string
  counts: {
    items: number
    formulas: number
    news: number
    wiki_pages: number
  }
  items: ItemResponse[]
  formulas: SnapshotFormula[]
  news: SnapshotNews[]
  wiki_pages: SnapshotWikiPage[]
  meta: SnapshotMeta
}

export interface CachedSnapshot {
  key: string
  data: SnapshotData
  saved_at: number
}

class SnapshotCache {
  private cache: CachedSnapshot | null = null

  async load(): Promise<SnapshotData | null> {
    if (this.cache) return this.cache.data
    const raw = (await dbGet(STORE, KEY)) as CachedSnapshot | undefined
    if (!raw) return null
    this.cache = raw
    return raw.data
  }

  async save(data: SnapshotData): Promise<void> {
    const entry: CachedSnapshot = { key: KEY, data, saved_at: Date.now() }
    this.cache = entry
    await dbPut(STORE, entry)
  }

  async clear(): Promise<void> {
    this.cache = null
    await dbClear(STORE)
  }

  isStale(data: SnapshotData | null, maxAgeMs = STALE_MS): boolean {
    if (!data) return true
    return Date.now() - new Date(data.generated_at).getTime() > maxAgeMs
  }

  async fetch(force = false): Promise<SnapshotData> {
    const cached = await this.load()
    if (!force && cached && !this.isStale(cached)) {
      return cached
    }

    let data: SnapshotData
    try {
      data = (await request<SnapshotData>({
        url: "/snapshot.json",
        method: "GET",
      })) as SnapshotData
    } catch {
      data = (await request<SnapshotData>({
        url: "/api/v1/export/snapshot",
        method: "GET",
      })) as SnapshotData
    }

    await this.save(data)
    return data
  }

  getItems(data: SnapshotData): ItemResponse[] {
    return data.items
  }

  getItem(data: SnapshotData, slug: string): ItemResponse | undefined {
    return data.items.find((i) => i.slug === slug)
  }

  getTypes(data: SnapshotData): string[] {
    return Array.from(new Set(data.items.map((i) => i.type))).sort()
  }

  searchItems(
    data: SnapshotData,
    query: string,
    type?: string | null,
    location?: string | null
  ): ItemResponse[] {
    let list = data.items
    if (type) list = list.filter((i) => i.type === type)
    if (query) {
      const q = query.toLowerCase()
      list = list.filter(
        (i) =>
          i.name.toLowerCase().includes(q) ||
          (i.description ?? "").toLowerCase().includes(q)
      )
    }
    if (location) {
      const loc = location.toLowerCase()
      list = list.filter((i) => {
        const dataStr = JSON.stringify(i.data ?? {}).toLowerCase()
        return dataStr.includes(loc)
      })
    }
    return list.sort((a, b) => a.name.localeCompare(b.name))
  }

  getFormulas(data: SnapshotData): SnapshotFormula[] {
    return data.formulas
  }

  getNews(data: SnapshotData): SnapshotNews[] {
    return data.news
  }

  /** Look up an item's data object (ore bonuses: min_kg, bonus_stat, max_boost) by slug. */
  getOreData(data: SnapshotData, slug: string): Record<string, unknown> | undefined {
    const item = data.items.find((i) => i.slug === slug)
    return item?.data ?? undefined
  }

  /** Build the museum ore database keyed by "name|rarity" from snapshot items. */
  buildOreDatabase(data: SnapshotData): Record<string, Record<string, unknown>> {
    const db: Record<string, Record<string, unknown>> = {}
    for (const item of data.items) {
      const rarity = (item.data as Record<string, unknown> | undefined)?.rarity as string | undefined
      if (!rarity) continue
      db[`${item.name}|${rarity}`] = item.data as Record<string, unknown>
    }
    return db
  }
}

export const snapshotCache = new SnapshotCache()

import type { ItemResponse } from "@/api/pick.schemas";
import request from "@/api/client";
import { dbGet, dbPut, dbClear } from "./idb";
import type {
  Formula,
  GameVersion,
  ItemType,
  LastScrape,
  PICKSnapshot,
  TaxonomyEntry,
  WikiPage,
} from "./snapshot.types";

const STORE = "snapshot";
const KEY = "main";
const STALE_MS = 1000 * 60 * 60 * 24; // 24 hours

// Optional live API origin. When unset the site runs fully static and reads
// the snapshot.json committed alongside the build.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type {
  Formula,
  GameVersion,
  ItemType,
  LastScrape,
  PICKSnapshot,
  TaxonomyEntry,
  WikiPage,
};

export type SnapshotCounts = PICKSnapshot["counts"];
export type SnapshotFormula = Formula;
export type SnapshotWikiPage = WikiPage;
export type SnapshotItem = PICKSnapshot["items"][number];

export interface GameVersionResponse {
  version: string | null;
  detected_at: string | null;
  triggered_full_scrape: number;
}

export interface LastScrapeResponse {
  status: string | null;
  started_at: string | null;
  finished_at: string | null;
  pages_scraped: number;
  pages_changed: number;
  pages_errors: number;
}

export interface SnapshotMeta {
  game_version: GameVersionResponse | null;
  last_scrape: LastScrapeResponse | null;
}

/**
 * The shape the pages read.
 *
 * The snapshot itself is described by `snapshot.schema.json` at the root of
 * the repository, and the types are generated from it. This adds the `meta`
 * wrapper, which holds the two blocks the API can omit, so a page never has
 * to check whether they are there.
 */
export interface SnapshotData {
  schema_version: number;
  taxonomy: TaxonomyEntry[];
  generated_at: string;
  counts: SnapshotCounts;
  items: ItemResponse[];
  formulas: SnapshotFormula[];
  wiki_pages: SnapshotWikiPage[];
  meta: SnapshotMeta;
}

export interface CachedSnapshot {
  key: string;
  data: SnapshotData;
  saved_at: number;
}

const EMPTY_SCRAPE: LastScrapeResponse = {
  status: "never",
  started_at: null,
  finished_at: null,
  pages_scraped: 0,
  pages_changed: 0,
  pages_errors: 0,
};

const EMPTY_VERSION: GameVersionResponse = {
  version: null,
  detected_at: null,
  triggered_full_scrape: 0,
}

/**
 * The shape of the snapshot this build understands.
 *
 * The snapshot is cached in the browser for a day. When the server publishes
 * a snapshot of a different shape, the cached one is discarded so the new
 * data is fetched instead of the old data being rendered by new code.
 */
export const SNAPSHOT_SCHEMA_VERSION = 6;

/** Shape of a snapshot payload before it is normalized. */
interface RawSnapshot {
  schema_version?: number;
  taxonomy?: TaxonomyEntry[];
  generated_at?: string;
  counts?: SnapshotData["counts"];
  items?: SnapshotData["items"];
  formulas?: SnapshotData["formulas"];
  wiki_pages?: SnapshotData["wiki_pages"];
  game_version?: Partial<GameVersionResponse> | null;
  last_scrape?: Partial<LastScrapeResponse> | null;
  meta?: {
    game_version?: Partial<GameVersionResponse> | null;
    last_scrape?: Partial<LastScrapeResponse> | null;
  } | null;
}

/**
 * Brings a raw snapshot payload into the shape the pages expect.
 *
 * The API and the committed snapshot.json expose the same fields, but the
 * `meta` object is only present on payloads that have already been through
 * this normalization. Both sources are normalized here so every page can rely
 * on `meta.game_version` and `meta.last_scrape` being present.
 */
export function normalizeSnapshot(raw: RawSnapshot | null | undefined): SnapshotData {
  const gameVersion = raw?.game_version ?? raw?.meta?.game_version ?? null;
  const lastScrape = raw?.last_scrape ?? raw?.meta?.last_scrape ?? null;

  return {
    schema_version: raw?.schema_version ?? SNAPSHOT_SCHEMA_VERSION,
    taxonomy: raw?.taxonomy ?? [],
    generated_at: raw?.generated_at ?? new Date().toISOString(),
    counts: raw?.counts ?? {
      items: raw?.items?.length ?? 0,
      formulas: raw?.formulas?.length ?? 0,
      wiki_pages: raw?.wiki_pages?.length ?? 0,
    },
    items: raw?.items ?? [],
    formulas: raw?.formulas ?? [],
    wiki_pages: raw?.wiki_pages ?? [],
    meta: {
      game_version: gameVersion
        ? {
            version: gameVersion.version ?? null,
            detected_at: gameVersion.detected_at ?? null,
            triggered_full_scrape: gameVersion.triggered_full_scrape ?? 0,
          }
        : EMPTY_VERSION,
      last_scrape: lastScrape
        ? {
            status: lastScrape.status ?? null,
            started_at: lastScrape.started_at ?? null,
            finished_at: lastScrape.finished_at ?? null,
            pages_scraped: lastScrape.pages_scraped ?? 0,
            pages_changed: lastScrape.pages_changed ?? 0,
            pages_errors: lastScrape.pages_errors ?? 0,
          }
        : EMPTY_SCRAPE,
    },
  };
}

export class SnapshotCache {
  private cache: CachedSnapshot | null = null;

  async load(): Promise<SnapshotData | null> {
    if (this.cache) return this.cache.data;
    const raw = (await dbGet(STORE, KEY)) as CachedSnapshot | undefined;
    if (!raw?.data) return null;

    // A snapshot written before this build's shape is discarded, so the new
    // data is fetched instead of the old data being read by code that
    // expects the new shape. A snapshot from a newer server is kept: this
    // build is simply out of date, and refetching would not change that.
    const cachedVersion = raw.data.schema_version;
    if (typeof cachedVersion !== "number" || cachedVersion < SNAPSHOT_SCHEMA_VERSION) {
      await this.clear();
      return null;
    }

    this.cache = { ...raw, data: raw.data };
    return raw.data;
  }

  async save(data: SnapshotData): Promise<void> {
    const entry: CachedSnapshot = { key: KEY, data, saved_at: Date.now() };
    this.cache = entry;
    await dbPut(STORE, entry);
  }

  async clear(): Promise<void> {
    this.cache = null;
    await dbClear(STORE);
  }

  isStale(data: SnapshotData | null, maxAgeMs = STALE_MS): boolean {
    if (!data) return true;
    return Date.now() - new Date(data.generated_at).getTime() > maxAgeMs;
  }

  async fetch(force = false): Promise<SnapshotData> {
    const cached = await this.load();
    if (!force && cached && !this.isStale(cached)) {
      return cached;
    }

    let data: SnapshotData;
    try {
      if (!API_BASE_URL) {
        throw new Error("No API base URL configured");
      }
      const apiData = await request<RawSnapshot>({
        url: "/api/v1/export/snapshot",
        method: "GET",
      });
      data = normalizeSnapshot(apiData);
    } catch {
      // Static fallback: the committed snapshot shipped with the site.
      // It lives under the Vite base path (e.g. /PICK/snapshot.json), not the API origin.
      const response = await fetch(`${import.meta.env.BASE_URL}snapshot.json`);
      if (!response.ok) {
        throw new Error(`Failed to load snapshot.json (${response.status})`);
      }
      data = normalizeSnapshot(await response.json());
    }

    await this.save(data);
    return data;
  }

  getItems(data: SnapshotData): ItemResponse[] {
    return data.items;
  }

  getItem(data: SnapshotData, slug: string): ItemResponse | undefined {
    return data.items.find((i) => i.slug === slug);
  }

  getTypes(data: SnapshotData): string[] {
    return Array.from(new Set(data.items.map((i) => i.type))).filter((t): t is string => t != null).sort();
  }

  searchItems(
    data: SnapshotData,
    query: string,
    type?: string | null,
    location?: string | null
  ): ItemResponse[] {
    let list = data.items;
    if (type) list = list.filter((i) => i.type === type);
    if (query) {
      const q = query.toLowerCase();
      list = list.filter(
        (i) =>
          i.name.toLowerCase().includes(q) || (i.description ?? "").toLowerCase().includes(q)
      );
    }
    if (location) {
      const loc = location.toLowerCase();
      list = list.filter((i) => {
        const dataStr = JSON.stringify(i.data ?? {}).toLowerCase();
        return dataStr.includes(loc);
      });
    }
    return list.sort((a, b) => a.name.localeCompare(b.name));
  }

  getFormulas(data: SnapshotData): SnapshotFormula[] {
    return data.formulas;
  }

  getOreData(data: SnapshotData, slug: string): Record<string, unknown> | undefined {
    const item = data.items.find((i) => i.slug === slug);
    return item?.data ?? undefined;
  }

  buildOreDatabase(data: SnapshotData): Record<string, Record<string, unknown>> {
    const db: Record<string, Record<string, unknown>> = {};
    for (const item of data.items) {
      const rarity = (item.data as Record<string, unknown> | undefined)?.rarity as string | undefined;
      if (!rarity) continue;
      db[`${item.name}|${rarity}`] = item.data as Record<string, unknown>;
    }
    return db;
  }
}

export const snapshotCache = new SnapshotCache();

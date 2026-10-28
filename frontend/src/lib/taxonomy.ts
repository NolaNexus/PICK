/**
 * The taxonomy of item types.
 *
 * The taxonomy travels with the snapshot, so the site can label and group
 * item types without an API of its own to ask. A type the server does not
 * know about still renders: it is treated as an item in the items area and
 * its name is humanised.
 */

export type TaxonomyKind = "item" | "record" | "reference"

export interface TaxonomyEntry {
  type: string
  area: string
  group: string | null
  label: string
  kind: TaxonomyKind
  listed: boolean
}

export interface Taxonomy {
  entries: Map<string, TaxonomyEntry>
  areas: string[]
  groups: Map<string, string[]>
}

const FALLBACK_AREA = "items"

function humanise(type: string): string {
  return type.replace(/_/g, " ").trim().replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Read the taxonomy out of a snapshot.
 */
export function readTaxonomy(raw: unknown): Taxonomy {
  const entries = new Map<string, TaxonomyEntry>()
  const areas: string[] = []
  const groups = new Map<string, string[]>()

  const list = Array.isArray(raw) ? (raw as TaxonomyEntry[]) : []

  for (const entry of list) {
    if (!entry || typeof entry.type !== "string") continue
    entries.set(entry.type, {
      type: entry.type,
      area: entry.area ?? FALLBACK_AREA,
      group: entry.group ?? null,
      label: entry.label || humanise(entry.type),
      kind: entry.kind ?? "item",
      listed: entry.listed !== false,
    })
  }

  for (const entry of entries.values()) {
    if (!areas.includes(entry.area)) areas.push(entry.area)
  }
  areas.sort()

  for (const entry of entries.values()) {
    if (!entry.group) continue
    const existing = groups.get(entry.group) ?? []
    existing.push(entry.type)
    groups.set(entry.group, existing)
  }

  return { entries, areas, groups }
}

/**
 * The label to show for a type.
 */
export function labelOf(taxonomy: Taxonomy, type: string): string {
  return taxonomy.entries.get(type)?.label ?? humanise(type)
}

/**
 * The area a type belongs to.
 */
export function areaOf(taxonomy: Taxonomy, type: string): string {
  return taxonomy.entries.get(type)?.area ?? FALLBACK_AREA
}

/**
 * The group a type sits in inside its area.
 */
export function groupOf(taxonomy: Taxonomy, type: string): string | null {
  return taxonomy.entries.get(type)?.group ?? null
}

/**
 * The types to list in an area, in the order the server gave them.
 */
export function typesInArea(taxonomy: Taxonomy, area: string): string[] {
  return [...taxonomy.entries.values()]
    .filter((entry) => entry.area === area && entry.listed)
    .map((entry) => entry.type)
}

/**
 * The types to list in a group.
 */
export function typesInGroup(taxonomy: Taxonomy, group: string): string[] {
  return [...taxonomy.entries.values()]
    .filter((entry) => entry.group === group && entry.listed)
    .map((entry) => entry.type)
}

/**
 * The groups of an area, in the order the server gave them.
 */
export function groupsInArea(taxonomy: Taxonomy, area: string): string[] {
  const groups: string[] = []
  for (const entry of taxonomy.entries.values()) {
    if (entry.area === area && entry.group && !groups.includes(entry.group)) {
      groups.push(entry.group)
    }
  }
  return groups
}

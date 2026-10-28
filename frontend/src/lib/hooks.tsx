import { useEffect, useMemo, useState } from "react"
import { snapshotCache, type SnapshotData } from "@/lib/snapshot"
import { readTaxonomy, type Taxonomy } from "@/lib/taxonomy"
import { cn } from "@/lib/utils"

/**
 * Load the snapshot and its taxonomy.
 */
export function useSnapshot(): {
  snapshot: SnapshotData | null
  taxonomy: Taxonomy
  loading: boolean
  error: Error | null
  refresh: () => void
} {
  const [snapshot, setSnapshot] = useState<SnapshotData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    const load = async () => {
      try {
        const data = await snapshotCache.fetch(false)
        if (!cancelled) {
          setSnapshot(data)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err as Error)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [nonce])

  const taxonomy = useMemo(() => readTaxonomy(snapshot?.taxonomy), [snapshot])

  return {
    snapshot,
    taxonomy,
    loading,
    error,
    refresh: () => setNonce((value) => value + 1),
  }
}

/**
 * The items of a type, in name order.
 */
export function itemsOfType(snapshot: SnapshotData | null, type: string) {
  if (!snapshot) return []
  return snapshotCache
    .getItems(snapshot)
    .filter((item) => item.type === type)
    .sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))
}

/**
 * The areas a set of minerals is found in, with how many minerals each has.
 */
export function areasOf(items: { data?: unknown }[]): { area: string; count: number }[] {
  const counts = new Map<string, number>()

  for (const item of items) {
    const data = item.data as Record<string, unknown> | undefined
    const areas = data?.areas
    if (!Array.isArray(areas)) continue

    for (const area of areas) {
      if (typeof area !== "string") continue
      counts.set(area, (counts.get(area) ?? 0) + 1)
    }
  }

  return [...counts.entries()]
    .map(([area, count]) => ({ area, count }))
    .sort((a, b) => a.area.localeCompare(b.area))
}

/**
 * A row of filter buttons.
 */
export function FilterBar({
  options,
  value,
  onChange,
  className,
}: {
  options: { value: string; label: string; count?: number }[]
  value: string | null
  onChange: (value: string | null) => void
  className?: string
}) {
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {options.map((option) => {
        const active = value === option.value
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(active ? null : option.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-sm capitalize transition-colors",
              active
                ? "border-gold-500 bg-gold-500 text-neutral-900"
                : "border-border text-muted-foreground hover:border-gold-500 hover:text-foreground",
            )}
          >
            {option.label}
            {option.count != null && (
              <span className={cn("ml-1 text-xs", active ? "opacity-80" : "opacity-60")}>
                {option.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

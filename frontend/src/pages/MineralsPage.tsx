import { useMemo, useState } from "react"
import { useSnapshot, areasOf } from "@/lib/hooks"
import { ItemList } from "@/components/item-list"
import { FilterBar } from "@/components/item-list"

export default function MineralsPage() {
  const { snapshot, taxonomy, loading } = useSnapshot()
  const [area, setArea] = useState<string | null>(null)

  const minerals = useMemo(() => {
    if (!snapshot) return []
    return snapshot.items
      .filter((item) => item.type === "mineral")
      .sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))
  }, [snapshot])

  const areas = useMemo(() => areasOf(minerals), [minerals])

  const shown = useMemo(() => {
    if (!area) return minerals
    return minerals.filter((mineral) => {
      const data = mineral.data as Record<string, unknown> | undefined
      const list = data?.areas
      return Array.isArray(list) && list.includes(area)
    })
  }, [minerals, area])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Minerals</h1>
        <p className="text-sm text-muted-foreground">
          Every ore, with the areas it is found in.
        </p>
      </div>

      {areas.length > 0 && (
        <FilterBar
          options={areas.map((entry) => ({ value: entry.area, label: entry.area, count: entry.count }))}
          value={area}
          onChange={setArea}
        />
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <ItemList
          items={shown}
          taxonomy={taxonomy}
          emptyText="No minerals here."
        />
      )}
    </div>
  )
}

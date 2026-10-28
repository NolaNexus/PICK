import { useMemo, useState } from "react"
import { useSnapshot } from "@/lib/hooks"
import { GroupSelector, ItemList } from "@/components/item-list"
import { groupsInArea, labelOf, typesInGroup } from "@/lib/taxonomy"

const GROUP_LABELS: Record<string, string> = {
  gear: "Gear",
  consumables: "Consumables",
  treasure: "Treasure",
}

export default function ItemsPage() {
  const { snapshot, taxonomy, loading } = useSnapshot()
  const [group, setGroup] = useState("gear")
  const [type, setType] = useState<string | null>(null)

  const groups = useMemo(
    () =>
      groupsInArea(taxonomy, "items").map((value) => ({
        value,
        label: GROUP_LABELS[value] ?? labelOf(taxonomy, value),
        count: typesInGroup(taxonomy, value).reduce(
          (total, itemType) =>
            total + (snapshot?.items.filter((item) => item.type === itemType).length ?? 0),
          0,
        ),
      })),
    [taxonomy, snapshot],
  )

  const types = useMemo(() => typesInGroup(taxonomy, group), [taxonomy, group])

  const items = useMemo(() => {
    if (!snapshot) return []
    const wanted = type ? [type] : types
    return snapshot.items
      .filter((item) => wanted.includes(item.type))
      .sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))
  }, [snapshot, type, types])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Items</h1>
        <p className="text-sm text-muted-foreground">
          Everything a player can hold, grouped by what it is.
        </p>
      </div>

      <GroupSelector groups={groups} value={group} onChange={setGroup} />

      <div className="flex flex-wrap gap-2 border-b pb-3">
        <button
          type="button"
          onClick={() => setType(null)}
          className={
            type === null
              ? "rounded-full border border-gold-500 bg-gold-500 px-3 py-1 text-sm text-neutral-900"
              : "rounded-full border border-border px-3 py-1 text-sm text-muted-foreground hover:border-gold-500"
          }
        >
          All
        </button>
        {types.map((itemType) => (
          <button
            key={itemType}
            type="button"
            onClick={() => setType(itemType)}
            className={
              type === itemType
                ? "rounded-full border border-gold-500 bg-gold-500 px-3 py-1 text-sm text-neutral-900"
                : "rounded-full border border-border px-3 py-1 text-sm text-muted-foreground hover:border-gold-500"
            }
          >
            {labelOf(taxonomy, itemType)}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <ItemList
          items={items}
          taxonomy={taxonomy}
          emptyText="No items here yet."
          showType={type === null && types.length > 1}
        />
      )}
    </div>
  )
}

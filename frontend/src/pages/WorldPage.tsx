import { useMemo, useState } from "react"
import { useSnapshot } from "@/lib/hooks"
import { ItemList } from "@/components/item-list"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ItemResponse } from "@/api/pick.schemas"

const SECTIONS = [
  { type: "npc", label: "NPCs" },
  { type: "quest", label: "Quests" },
  { type: "location", label: "Locations" },
  { type: "excavation_site", label: "Excavation Sites" },
  { type: "event", label: "Events" },
]

export default function WorldPage() {
  const { snapshot, taxonomy, loading } = useSnapshot()
  const [section, setSection] = useState("npc")

  const items = useMemo(() => {
    if (!snapshot) return []
    return snapshot.items
      .filter((item) => item.type === section)
      .sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))
  }, [snapshot, section])

  const areas = useMemo(
    () =>
      items
        .filter((item) => item.type === "location")
        .map((item) => ({
          item,
          sublocations:
            ((item.data as Record<string, unknown> | undefined)?.sublocations as
              | { name: string; slug?: string; toughness: number | null; npcs: string[]; notes: string[] }[]
              | undefined) ?? [],
        })),
    [items],
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">World</h1>
        <p className="text-sm text-muted-foreground">
          The people, places and events of Prospecting.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 border-b pb-3">
        {SECTIONS.map((entry) => (
          <button
            key={entry.type}
            type="button"
            onClick={() => setSection(entry.type)}
            className={
              section === entry.type
                ? "rounded-full border border-gold-500 bg-gold-500 px-3 py-1 text-sm text-neutral-900"
                : "rounded-full border border-border px-3 py-1 text-sm text-muted-foreground hover:border-gold-500"
            }
          >
            {entry.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : section === "location" ? (
        <div className="space-y-4">
          {areas.map(({ item, sublocations }) => (
            <Card key={item.slug}>
              <CardHeader>
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-base">{item.name}</CardTitle>
                  <Badge variant="outline">
                    {(item.data as Record<string, unknown> | undefined)?.category === "limited_time"
                      ? "Limited time"
                      : "Always open"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {item.description ? (
                  <p className="text-sm text-muted-foreground">{item.description}</p>
                ) : null}
                {sublocations.length > 0 ? (
                  <ul className="space-y-2">
                    {sublocations.map((sub) => (
                      <li key={sub.slug ?? sub.name} className="text-sm">
                        <span className="font-medium">{sub.name}</span>
                        {sub.toughness != null ? (
                          <span className="ml-2 text-xs text-muted-foreground">
                            Toughness {sub.toughness}
                          </span>
                        ) : null}
                        {sub.npcs.length > 0 ? (
                          <span className="ml-2 text-xs text-muted-foreground">
                            {sub.npcs.join(", ")}
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <ItemList
          items={items as ItemResponse[]}
          taxonomy={taxonomy}
          emptyText="Nothing here yet."
        />
      )}
    </div>
  )
}

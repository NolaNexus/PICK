import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ItemDetail } from "@/components/item-detail"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/modal"
import type { ItemResponse } from "@/api/pick.schemas"
import { FilterBar } from "@/lib/hooks"
import { labelOf, type Taxonomy } from "@/lib/taxonomy"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 50

/**
 * A browsable list of items with a detail dialog.
 */
export function ItemList({
  items,
  taxonomy,
  emptyText = "Nothing here yet.",
  showType = false,
}: {
  items: ItemResponse[]
  taxonomy: Taxonomy
  emptyText?: string
  showType?: boolean
}) {
  const [query, setQuery] = useState("")
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<ItemResponse | null>(null)

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase()
    const list = term
      ? items.filter(
          (item) =>
            (item.name ?? "").toLowerCase().includes(term) ||
            (item.description ?? "").toLowerCase().includes(term),
        )
      : items
    return [...list].sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))
  }, [items, query])

  const page = filtered.slice(offset, offset + PAGE_SIZE)
  const pages = Math.ceil(filtered.length / PAGE_SIZE) || 1

  return (
    <div className="space-y-4">
      <Input
        placeholder="Filter by name…"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setOffset(0)
        }}
        className="max-w-sm"
      />

      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Name</th>
                  {showType && <th className="px-4 py-2 font-medium">Type</th>}
                  <th className="px-4 py-2 text-right font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {page.map((item) => (
                  <tr key={item.slug} className="border-t hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">
                      {item.name}
                      {item.description ? (
                        <span className="block text-xs text-muted-foreground">
                          {item.description}
                        </span>
                      ) : null}
                    </td>
                    {showType && (
                      <td className="px-4 py-2">
                        <Badge variant="outline">{labelOf(taxonomy, item.type)}</Badge>
                      </td>
                    )}
                    <td className="px-4 py-2 text-right">
                      <Button variant="ghost" size="sm" onClick={() => setSelected(item)}>
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pages > 1 && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, filtered.length)} of{" "}
                {filtered.length}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={offset + PAGE_SIZE >= filtered.length}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{selected?.name}</DialogTitle>
            <DialogDescription className="capitalize">
              {selected ? labelOf(taxonomy, selected.type) : null}
            </DialogDescription>
          </DialogHeader>
          {selected ? <ItemDetail item={selected} /> : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}

/**
 * A row of buttons that switch between groups.
 */
export function GroupSelector({
  groups,
  value,
  onChange,
}: {
  groups: { value: string; label: string; count?: number }[]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {groups.map((group) => (
        <button
          key={group.value}
          type="button"
          onClick={() => onChange(group.value)}
          className={cn(
            "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
            value === group.value
              ? "border-gold-500 bg-gold-500 text-neutral-900"
              : "border-border text-muted-foreground hover:border-gold-500 hover:text-foreground",
          )}
        >
          {group.label}
          {group.count != null && (
            <span className={cn("ml-1.5 text-xs", value === group.value ? "opacity-80" : "opacity-60")}>
              {group.count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

export { FilterBar }

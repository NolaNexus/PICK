import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { snapshotCache } from '@/lib/snapshot'
import type { SnapshotData } from '@/lib/snapshot'
import { labelOf, readTaxonomy } from '@/lib/taxonomy'
import { useDebounce } from '@/hooks/useDebounce'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/components/ui/toast'
import { ItemDetail } from '@/components/item-detail'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/modal'
import type { Item } from '@/lib/snapshot.types'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [size] = useState(15)
  const [type, setType] = useState<string | null>(null)
  const [area, setArea] = useState<string | null>(null)
  const [location, setLocation] = useState('')
  const [snapshot, setSnapshot] = useState<SnapshotData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [syncError, setSyncError] = useState<Error | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [selectedItem, setSelectedItem] = useState<Item | null>(null)
  const debounced = useDebounce(query, 300)
  const loadedRef = useRef(false)

  useEffect(() => {
    if (loadedRef.current) return
    loadedRef.current = true

    let cancelled = false
    const load = async () => {
      setIsLoading(true)
      setSyncError(null)
      try {
        const data = await snapshotCache.fetch(false)
        if (!cancelled) {
          setSnapshot(data)
          setIsLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setSyncError(err instanceof Error ? err : new Error(String(err)))
          setIsLoading(false)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  const syncData = useCallback(async () => {
    setIsSyncing(true)
    setSyncError(null)
    try {
      const data = await snapshotCache.fetch(true)
      setSnapshot(data)
      toast.success("Search index synced")
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err))
      setSyncError(e)
      toast.error(`Sync failed: ${e.message}`)
    } finally {
      setIsSyncing(false)
    }
  }, [])

  const taxonomy = useMemo(() => readTaxonomy(snapshot?.taxonomy), [snapshot])

  const types = useMemo(() => {
    if (!snapshot) return []
    // Only the types that are browsable on their own are offered as filters.
    return snapshotCache
      .getTypes(snapshot)
      .filter((type) => taxonomy.entries.get(type)?.listed !== false)
      .sort()
  }, [snapshot, taxonomy])

  const groups = useMemo(() => {
    const areas = new Set<string>()
    for (const type of types) {
      const area = taxonomy.entries.get(type)?.area
      if (area) areas.add(area)
    }
    return [...areas].sort()
  }, [types, taxonomy])

  const hasQuery = debounced.length >= 2

  const results = useMemo(() => {
    if (!snapshot || !hasQuery) return []
    const all = snapshotCache.searchItems(snapshot, debounced, type || undefined, location || undefined)
    if (!area) return all
    return all.filter((item) => taxonomy.entries.get(item.type)?.area === area)
  }, [snapshot, debounced, type, location, area, hasQuery, taxonomy])

  const total = results.length
  const totalPages = Math.max(1, Math.ceil(total / size))
  const clampedPage = Math.min(Math.max(page, 1), totalPages)
  const offset = (clampedPage - 1) * size
  const pageResults = results.slice(offset, offset + size)

  useEffect(() => {
    if (page !== clampedPage) setPage(clampedPage)
  }, [clampedPage, page])

  const isEmpty = hasQuery && results.length === 0
  const canPrev = clampedPage > 1
  const canNext = clampedPage < totalPages

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-muted-foreground">Full-text search across items.</p>
        <div className="h-32 w-full bg-muted rounded animate-pulse" />
      </div>
    )
  }

  if (syncError) {
    toast.error(`Failed to load search index: ${syncError.message}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
          <p className="text-muted-foreground">Full-text search across items. Data cached locally.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={syncData} disabled={isSyncing} variant="outline" size="sm">
            {isSyncing ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current" /> : null} Sync
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search items</CardTitle>
        </CardHeader>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Query</label>
              <Input
                placeholder="Search items..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              {!hasQuery && query.length > 0 && (
                <p className="text-xs text-muted-foreground">Type at least 2 characters</p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Area</label>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => setArea(null)}
                  variant={area === null ? 'default' : 'outline'}
                  size="sm"
                >
                  All
                </Button>
                {groups.map((group) => (
                  <Button
                    key={group}
                    onClick={() => setArea(group)}
                    variant={area === group ? 'default' : 'outline'}
                    size="sm"
                  >
                    {group}
                  </Button>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Type</label>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => setType(null)}
                  variant={type === null ? 'default' : 'outline'}
                  size="sm"
                >
                  All
                </Button>
                {types.map((t) => (
                  <Button
                    key={t}
                    onClick={() => setType(t)}
                    variant={type === t ? 'default' : 'outline'}
                    size="sm"
                  >
                    {labelOf(taxonomy, t)}
                  </Button>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Location</label>
              <Input
                placeholder="e.g. forest"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={() => setPage(1)} disabled={!hasQuery || isSyncing}>
                Search
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Results ({total})
            {isEmpty && <span className="text-sm text-muted-foreground">No matches</span>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!hasQuery && (
            <div className="text-muted-foreground text-sm py-4">
              Enter at least 2 characters to search.
            </div>
          )}
          {hasQuery && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Relevance</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pageResults.map((item) => (
                    <TableRow key={item.id} className="cursor-pointer hover:bg-muted/30">
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{labelOf(taxonomy, item.type)}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">—</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedItem(item)}
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {isEmpty && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground py-4">
                        No results found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
          {hasQuery && totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-sm">
              <div className="text-muted-foreground">Page {clampedPage} of {totalPages}</div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canPrev}
                  onClick={() => setPage(clampedPage - 1)}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canNext}
                  onClick={() => setPage(clampedPage + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selectedItem} onOpenChange={(open) => !open && setSelectedItem(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{selectedItem?.name}</DialogTitle>
            <DialogDescription className="capitalize">
              {selectedItem?.type?.replace(/_/g, " ")}
            </DialogDescription>
          </DialogHeader>
          {selectedItem ? <ItemDetail item={selectedItem} /> : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}

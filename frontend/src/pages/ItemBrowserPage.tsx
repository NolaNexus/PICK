import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ItemResponse } from '@/api/pick.schemas'
import { snapshotCache, type SnapshotData } from '@/lib/snapshot'
import { useDebounce } from '@/hooks/useDebounce'
import { useFilterStore } from '@/stores/filterStore'
import { toast } from '@/components/ui/toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ItemDetail } from '@/components/item-detail'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/modal'
import { Spinner } from '@/components/ui/spinner'

function SkeletonRow() {
  return (
    <TableRow className="animate-pulse">
      <TableCell className="h-12">
        <div className="h-4 w-3/4 bg-muted rounded animate-pulse"></div>
      </TableCell>
      <TableCell className="h-12">
        <div className="h-4 w-1/2 bg-muted rounded animate-pulse"></div>
      </TableCell>
      <TableCell className="h-12">
        <div className="h-4 w-1/3 bg-muted rounded animate-pulse"></div>
      </TableCell>
    </TableRow>
  )
}

export default function ItemBrowserPage() {
  const { itemType, searchQuery, setItemType, setSearchQuery } = useFilterStore()
  const [selectedItem, setSelectedItem] = useState<ItemResponse | null>(null)
  const [page, setPage] = useState(1)
  const [size] = useState(20)
  const [snapshot, setSnapshot] = useState<SnapshotData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [syncError, setSyncError] = useState<Error | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const debouncedSearch = useDebounce(searchQuery, 300)
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
      toast.success("Data synced from backend")
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err))
      setSyncError(e)
      toast.error(`Sync failed: ${e.message}`)
    } finally {
      setIsSyncing(false)
    }
  }, [])

  const items = useMemo(() => {
    if (!snapshot) return []
    let list = snapshot.items
    if (itemType) list = list.filter((i) => i.type === itemType)
    if (debouncedSearch) {
      const term = debouncedSearch.toLowerCase()
      list = list.filter(
        (i) => (i.name ?? "").toLowerCase().includes(term) || (i.description ?? "").toLowerCase().includes(term)
      )
    }
    return list.sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))
  }, [snapshot, itemType, debouncedSearch])

  const total = items.length
  const totalPages = Math.max(1, Math.ceil(total / size))
  const clampedPage = Math.min(Math.max(page, 1), totalPages)
  const offset = (clampedPage - 1) * size
  const pageItems = items.slice(offset, offset + size)

  useEffect(() => {
    if (page !== clampedPage) setPage(clampedPage)
  }, [clampedPage, page])

  const types = useMemo(() => (snapshot ? snapshotCache.getTypes(snapshot) : []), [snapshot])

  useEffect(() => {
    if (syncError) {
      toast.error(`Failed to load data: ${syncError.message}`)
    }
  }, [syncError])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex flex-col gap-4">
          <div className="h-10 w-1/3 bg-muted rounded animate-pulse" />
          <div className="h-10 w-3/4 bg-muted rounded animate-pulse" />
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Slug</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {[1, 2, 3, 4].map((i) => (
              <SkeletonRow key={i} />
            ))}
          </TableBody>
        </Table>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">Item Browser</h1>
          <p className="text-muted-foreground">
            Browse prospecting items. Data is cached locally on your machine.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={syncData}
            disabled={isSyncing}
            variant="outline"
            size="sm"
          >
            {isSyncing ? <Spinner className="h-4 w-4" /> : null} Sync
          </Button>
          <Button
            variant={snapshot ? "default" : "outline"}
            size="sm"
            disabled={!snapshot}
          >
            Local cache: {snapshot ? snapshot.counts.items : 0} items
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">Type</span>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => setItemType(null)}
                  variant={itemType === null ? "default" : "outline"}
                  size="sm"
                >
                  All
                </Button>
                {types.map((t) => (
                  <Button
                    key={t}
                    onClick={() => setItemType(t)}
                    variant={itemType === t ? "default" : "outline"}
                    size="sm"
                  >
                    {t}
                  </Button>
                ))}
              </div>
            </div>
            <div className="relative">
              <Input
                placeholder="Search items..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Items ({total} total)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Slug</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pageItems.map((item) => (
                  <TableRow
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className="cursor-pointer hover:bg-muted/30"
                  >
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{item.type}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {item.slug}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" onClick={(e) => {
                        e.stopPropagation()
                        setSelectedItem(item)
                      }}>
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {pageItems.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-4">
                      No items found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-sm">
              <div className="text-muted-foreground">
                Page {clampedPage} of {totalPages}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={clampedPage <= 1}
                  onClick={() => setPage(clampedPage - 1)}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={clampedPage >= totalPages}
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
        <DialogTrigger asChild>
          <button />
        </DialogTrigger>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{selectedItem?.name}</DialogTitle>
            <DialogDescription className="capitalize">
              {selectedItem?.type?.replace(/_/g, " ")}
            </DialogDescription>
          </DialogHeader>
          {selectedItem ? (
            <ItemDetail item={selectedItem} />
          ) : (
            <DialogFooter>
              <span className="text-sm text-muted-foreground">No details available.</span>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

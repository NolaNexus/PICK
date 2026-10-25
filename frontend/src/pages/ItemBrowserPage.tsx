import { useState } from 'react'
import {
  useListItemsApiV1ItemsGet,
  useListItemTypesApiV1ItemsTypesGet,
  useGetItemApiV1ItemsSlugGet,
} from '@/api/items/items'
import type { ItemResponse } from '@/api/pick.schemas'
import { useDebounce } from '@/hooks/useDebounce'
import { useFilterStore } from '@/stores/filterStore'
import { toast } from '@/components/ui/toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  const debouncedSearch = useDebounce(searchQuery, 300)

  const { data: typesData } = useListItemTypesApiV1ItemsTypesGet({
    query: { refetchInterval: 30_000 },
  })
  const types = typesData ?? []

  const {
    data,
    isLoading,
    error,
    refetch,
  } = useListItemsApiV1ItemsGet(
    {
      type: itemType || undefined,
      search: debouncedSearch || undefined,
      page,
      size,
    },
    { query: { refetchInterval: 30_000 } }
  )

  const items = (data?.items as ItemResponse[]) ?? []
  const totalPages = data?.pages ?? 0

  const itemDetail = useGetItemApiV1ItemsSlugGet(selectedItem?.slug ?? '', {
    query: { enabled: !!selectedItem?.slug },
  })

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

  if (error) {
    toast.error(`Failed to load items: ${(error as { message?: string }).message ?? String(error)}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">Item Browser</h1>
          <p className="text-muted-foreground">
            Browse prospecting items. Data refreshes every 30 seconds.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => refetch()}
            disabled={isLoading}
            variant="outline"
            size="sm"
          >
            {isLoading ? <Spinner className="h-4 w-4" /> : null} Refresh
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
                  variant={itemType === null ? 'default' : 'outline'}
                  size="sm"
                >
                  All
                </Button>
                {types.map((t) => (
                  <Button
                    key={t}
                    onClick={() => setItemType(t)}
                    variant={itemType === t ? 'default' : 'outline'}
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
            Items ({totalPages > 0 ? data?.total : 0} total)
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
                {items.map((item) => (
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
                {items.length === 0 && (
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
                Page {page} of {totalPages}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedItem?.name}</DialogTitle>
            <DialogDescription>{selectedItem?.description}</DialogDescription>
          </DialogHeader>
          {itemDetail.isLoading ? (
            <div className="py-4 flex items-center gap-2">
              <Spinner /> Loading details...
            </div>
          ) : itemDetail.error ? (
            <div className="p-4 text-destructive text-sm">
              Failed to load details: {(itemDetail.error as { message?: string }).message ?? String(itemDetail.error)}
            </div>
          ) : selectedItem && itemDetail.data ? (
            <DialogFooter>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Type</span>{' '}
                  <span className="font-medium">{selectedItem.type}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Slug</span>{' '}
                  <span className="font-medium">{selectedItem.slug}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Data</span>{' '}
                  <span className="font-mono text-xs">
                    {JSON.stringify(selectedItem.data).slice(0, 120)}...
                  </span>
                </div>
              </div>
            </DialogFooter>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}

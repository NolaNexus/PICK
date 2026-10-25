import { useState } from 'react'
import { useDebounce } from '@/hooks/useDebounce'
import { useSearchApiV1SearchGet } from '@/api/search/search'
import type { PaginatedResponse } from '@/api/pick.schemas'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/components/ui/toast'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [size] = useState(15)
  const [type, setType] = useState<string | null>(null)
  const [location, setLocation] = useState('')
  const debounced = useDebounce(query, 300)
  const hasQuery = debounced.length >= 2

  const { data, isLoading, error, refetch } = useSearchApiV1SearchGet(
    {
      q: debounced,
      type: type || undefined,
      location: location || undefined,
      page,
      size,
    },
    { query: { enabled: hasQuery } }
  )

  const paginated = data as PaginatedResponse | undefined
  const results = (paginated?.items as { id: number; name: string; type: string }[]) ?? []
  const totalPages = paginated?.pages ?? 0
  const isEmpty = hasQuery && results.length === 0
  const canPrev = page > 1
  const canNext = totalPages > page

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Search</h1>
        <div className="h-32 w-full bg-muted rounded animate-pulse" />
      </div>
    )
  }

  if (error) {
    toast.error(`Search failed: ${(error as { message?: string }).message ?? String(error)}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
          <p className="text-muted-foreground">Full-text search across items.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search items</CardTitle>
        </CardHeader>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
              <label className="text-sm font-medium">Type</label>
              <Input
                placeholder="e.g. pan"
                value={type ?? ''}
                onChange={(e) => setType(e.target.value || null)}
              />
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
              <Button onClick={() => refetch()} disabled={!hasQuery || isLoading}>
                Search
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Results ({paginated?.total ?? 0})
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
                  {results.map((item) => (
                    <TableRow key={item.id} className="cursor-pointer hover:bg-muted/30">
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{item.type}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">—</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm">View</Button>
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
              <div className="text-muted-foreground">Page {page} of {totalPages}</div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canPrev}
                  onClick={() => setPage(page - 1)}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canNext}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

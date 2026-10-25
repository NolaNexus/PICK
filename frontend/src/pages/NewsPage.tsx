import { useState } from 'react'
import { formatDistance } from 'date-fns'
import {
  useListNewsApiV1NewsGet,
  useLatestNewsApiV1NewsLatestGet,
  useListNewsTagsApiV1NewsTagsGet,
} from '@/api/news/news'
import type { PaginatedResponse } from '@/api/pick.schemas'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/components/ui/toast'

type NewsItem = {
  id: number
  title: string
  author?: string | null
  score?: number | null
  posted_at?: string | null
  tags?: string[]
}

export default function NewsPage() {
  const [tag, setTag] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [size] = useState(15)

  const { data: latestData, isLoading: latestLoading } = useLatestNewsApiV1NewsLatestGet(
    { limit: 5 },
    { query: { refetchInterval: 60_000 } }
  )

  const { data, isLoading, error, refetch } = useListNewsApiV1NewsGet(
    { tag, page, size },
    { query: { refetchInterval: 60_000 } }
  )

  const { data: tagsData } = useListNewsTagsApiV1NewsTagsGet({
    query: { refetchInterval: 60_000 },
  })

  const paginated = data as PaginatedResponse | undefined
  const news = (paginated?.items as NewsItem[]) ?? []
  const totalPages = paginated?.pages ?? 0

  if (isLoading || latestLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">News Feed</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    toast.error(`Failed to load news: ${(error as { message?: string }).message ?? String(error)}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">News Feed</h1>
          <p className="text-muted-foreground">Community news from Reddit.</p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Articles
                <Input
                  placeholder="Search..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </CardTitle>
            </CardHeader>
            <CardContent className="py-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Author</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                      <TableHead className="text-right">Posted</TableHead>
                      <TableHead className="text-right">Tags</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {news.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">{item.title}</TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {item.author ?? '—'}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {item.score ?? 0}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {item.posted_at
                            ? formatDistance(new Date(item.posted_at), new Date(), { addSuffix: true })
                            : '—'}
                        </TableCell>
                        <TableCell>
                          {item.tags?.slice(0, 3).map((t) => (
                            <Badge key={t} variant="outline">
                              {t}
                            </Badge>
                          ))}
                        </TableCell>
                      </TableRow>
                    ))}
                    {news.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground py-4">
                          No news articles found.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 text-sm">
                  <div className="text-muted-foreground">Page {page} of {totalPages}</div>
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
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Latest</CardTitle>
            </CardHeader>
            <CardContent className="py-3">
              <div className="space-y-3">
                {(latestData as NewsItem[] | undefined ?? []).map((item) => (
                  <div key={item.id} className="flex gap-3">
                    <div className="flex-shrink-0 h-8 w-8 rounded bg-muted" />
                    <div className="flex-1">
                      <div className="text-sm font-medium">{item.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.author ?? '—'} · {item.posted_at ? formatDistance(new Date(item.posted_at), new Date(), { addSuffix: true }) : '—'}
                      </div>
                    </div>
                  </div>
                ))}
                {!(latestData as NewsItem[] | undefined ?? []).length && (
                  <div className="text-xs text-muted-foreground">No latest news.</div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tags</CardTitle>
            </CardHeader>
            <CardContent className="py-3">
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => setTag(null)}
                  variant={tag === null ? 'default' : 'outline'}
                  size="sm"
                >
                  All
                </Button>
                {(tagsData as string[] | undefined ?? []).map((t) => (
                  <Button
                    key={t}
                    onClick={() => setTag(t)}
                    variant={tag === t ? 'default' : 'outline'}
                    size="sm"
                  >
                    {t}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

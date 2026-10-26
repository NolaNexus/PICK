import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { formatDistance } from 'date-fns'
import { snapshotCache } from '@/lib/snapshot'
import type { SnapshotNews } from '@/lib/snapshot'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/components/ui/toast'

export default function NewsPage() {
  const [tag, setTag] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [size] = useState(15)
  const [snapshot, setSnapshot] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [syncError, setSyncError] = useState<Error | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
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
      toast.success("News synced")
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err))
      setSyncError(e)
      toast.error(`Sync failed: ${e.message}`)
    } finally {
      setIsSyncing(false)
    }
  }, [])

  const allNews = useMemo(() => {
    if (!snapshot) return []
    let list = snapshot.news as SnapshotNews[]
    if (tag) list = list.filter((n) => (n.tags ?? []).includes(tag))
    if (query) {
      const q = query.toLowerCase()
      list = list.filter((n) => n.title.toLowerCase().includes(q))
    }
    return list.sort((a, b) => {
      const pa = new Date(a.published_at ?? 0).getTime()
      const pb = new Date(b.published_at ?? 0).getTime()
      return pb - pa
    })
  }, [snapshot, tag, query])

  const latest = useMemo(() => {
    if (!snapshot) return []
    return [...(snapshot.news as SnapshotNews[])]
      .sort((a, b) => {
        const pa = new Date(a.published_at ?? 0).getTime()
        const pb = new Date(b.published_at ?? 0).getTime()
        return pb - pa
      })
      .slice(0, 5)
  }, [snapshot])

  const news = useMemo(() => {
    if (!allNews) return []
    const start = (page - 1) * size
    return allNews.slice(start, start + size)
  }, [allNews, page, size])

  const totalPages = useMemo(() => {
    if (!allNews) return 1
    return Math.max(1, Math.ceil(allNews.length / size))
  }, [allNews, size])

  const tags = useMemo(() => {
    if (!snapshot) return []
    const tagSet = new Set<string>()
    for (const n of snapshot.news as SnapshotNews[]) {
      for (const t of n.tags ?? []) tagSet.add(t)
    }
    return Array.from(tagSet).sort()
  }, [snapshot])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">News Feed</h1>
        <p className="text-muted-foreground">Community news from Reddit.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (syncError) {
    toast.error(`Failed to load news: ${syncError.message}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">News Feed</h1>
          <p className="text-muted-foreground">Community news from Reddit. Data cached locally.</p>
        </div>
        <Button onClick={syncData} disabled={isSyncing} variant="outline" size="sm">
          {isSyncing ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current" /> : null} Sync
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
                          {item.published_at
                            ? formatDistance(new Date(item.published_at), new Date(), { addSuffix: true })
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
                {latest.map((item) => (
                  <div key={item.id} className="flex gap-3">
                    <div className="flex-shrink-0 h-8 w-8 rounded bg-muted" />
                    <div className="flex-1">
                      <div className="text-sm font-medium">{item.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.author ?? '—'} · {item.published_at ? formatDistance(new Date(item.published_at), new Date(), { addSuffix: true }) : '—'}
                      </div>
                    </div>
                  </div>
                ))}
                {!latest.length && (
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
                {tags.map((t) => (
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

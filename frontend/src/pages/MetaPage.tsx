import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { snapshotCache } from '@/lib/snapshot'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { toast } from '@/components/ui/toast'

export default function MetaPage() {
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
      toast.success("Status synced")
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err))
      setSyncError(e)
      toast.error(`Sync failed: ${e.message}`)
    } finally {
      setIsSyncing(false)
    }
  }, [])

  const meta = useMemo(() => {
    if (!snapshot) return null
    const counts = snapshot.counts
    const types = snapshotCache.getTypes(snapshot)
    const lastScrape = snapshot.last_scrape
    const game_version = snapshot.game_version

    return {
      total_items: counts.items,
      total_types: types.length,
      game_version: game_version?.version ?? null,
      detected_at: game_version?.detected_at ?? null,
      last_scrape: lastScrape?.started_at ?? null,
      scrape_status: lastScrape?.status ?? 'never',
      pages_changed: lastScrape?.pages_changed ?? 0,
      pages_errors: lastScrape?.pages_errors ?? 0,
      triggered_full_scrape: game_version?.triggered_full_scrape ?? 0,
    }
  }, [snapshot])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Status Dashboard</h1>
        <p className="text-muted-foreground">
          Scrape statistics and game version.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (syncError) {
    toast.error(`Failed to load status: ${syncError.message}`)
  }

  if (!meta) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Status Dashboard</h1>
        <p className="text-muted-foreground">No data available. Sync first.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Status Dashboard</h1>
          <p className="text-muted-foreground">
            Scrape statistics and game version from local cache.
          </p>
        </div>
        <Button
          onClick={syncData}
          disabled={isSyncing}
          variant="outline"
          size="sm"
        >
          {isSyncing ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current" /> : null} Sync
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Total Items</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{meta.total_items ?? '—'}</div>
            <div className="text-xs text-muted-foreground mt-1">Indexed wiki items</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Total Types</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{meta.total_types ?? '—'}</div>
            <div className="text-xs text-muted-foreground mt-1">Item types tracked</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Game Version</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-mono font-bold">{meta.game_version ?? '—'}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {meta.detected_at ? `Detected ${meta.detected_at}` : '—'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Last Scrape</CardTitle>
        </CardHeader>
        <CardContent className="py-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground">Status</div>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant={meta.scrape_status === 'success' ? 'default' : 'secondary'}>
                  {meta.scrape_status}
                </Badge>
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">Pages Changed</div>
              <div className="mt-1">{meta.pages_changed}</div>
            </div>
          </div>
          {meta.last_scrape && (
            <div className="mt-4 text-sm text-muted-foreground">
              Last scrape: {meta.last_scrape}
            </div>
          )}
          {meta.triggered_full_scrape !== undefined && (
            <div className="mt-1 text-sm text-muted-foreground">
              Full scrape triggered: {String(meta.triggered_full_scrape)}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

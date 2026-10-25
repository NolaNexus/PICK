import { useMetaApiV1MetaGet } from '@/api/meta/meta'
import {
  useHealthCheckApiV1HealthHealthGet,
  useReadinessCheckApiV1HealthHealthReadyGet,
} from '@/api/health/health'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { toast } from '@/components/ui/toast'

type MetaData = {
  total_items?: number
  total_types?: number
  last_scrape?: string | null
  game_version?: string | null
  detected_at?: string | null
  triggered_full_scrape?: boolean
  status?: string | null
}

export default function MetaPage() {
  const { data, isLoading, error, refetch: refetchMeta } = useMetaApiV1MetaGet({
    query: { refetchInterval: 30_000 },
  })

  const meta = (data as MetaData | undefined) ?? {}

  const { data: health, isLoading: healthLoading } = useHealthCheckApiV1HealthHealthGet({
    query: { refetchInterval: 30_000 },
  })
  const { data: ready, isLoading: readyLoading } =
    useReadinessCheckApiV1HealthHealthReadyGet({
      query: { refetchInterval: 30_000 },
    })

  if (isLoading || healthLoading || readyLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Status Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    toast.error(`Failed to load status: ${(error as { message?: string }).message ?? String(error)}`)
  }

  const healthStatus = (health as { status?: string } | undefined)?.status ?? 'unknown'
  const readyStatus = (ready as { status?: string } | undefined)?.status ?? 'unknown'

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Status Dashboard</h1>
          <p className="text-muted-foreground">
            Scrape statistics, game version, and service health.
          </p>
        </div>
        <Button
          onClick={() => refetchMeta()}
          variant="outline"
          size="sm"
          disabled={isLoading || healthLoading || readyLoading}
        >
          Refresh
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
          <CardTitle>Service Health</CardTitle>
        </CardHeader>
        <CardContent className="py-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground">Health</div>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant={healthStatus === 'ok' || healthStatus === 'healthy' ? 'default' : 'secondary'}>
                  {healthStatus}
                </Badge>
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">Readiness</div>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant={readyStatus === 'ok' || readyStatus === 'ready' ? 'default' : 'secondary'}>
                  {readyStatus}
                </Badge>
              </div>
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

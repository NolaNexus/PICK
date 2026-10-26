import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { snapshotCache } from '@/lib/snapshot'
import { useDebounce } from '@/hooks/useDebounce'
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

export default function FormulasPage() {
  const [query, setQuery] = useState('')
  const [detailId, setDetailId] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [syncError, setSyncError] = useState<Error | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
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
      toast.success("Formulas synced")
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err))
      setSyncError(e)
      toast.error(`Sync failed: ${e.message}`)
    } finally {
      setIsSyncing(false)
    }
  }, [])

  const formulas = useMemo(() => {
    if (!snapshot) return []
    return snapshotCache.getFormulas(snapshot)
  }, [snapshot])

  const filtered = useMemo(() => {
    if (!debounced) return formulas
    const q = debounced.toLowerCase()
    return formulas.filter(
      (f) =>
        f.formula_id.toLowerCase().includes(q) ||
        f.name.toLowerCase().includes(q)
    )
  }, [formulas, debounced])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Formula Reference</h1>
        <p className="text-muted-foreground">
          Lookup formulas used by the calculators.
        </p>
        <div className="h-32 w-full bg-muted rounded animate-pulse" />
      </div>
    )
  }

  if (syncError) {
    toast.error(`Failed to load formulas: ${syncError.message}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Formula Reference</h1>
          <p className="text-muted-foreground">
            Lookup formulas used by the calculators. Data cached locally.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={syncData}
            disabled={isSyncing}
            variant="outline"
            size="sm"
          >
            {isSyncing ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current" /> : null} Sync
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search formulas</CardTitle>
        </CardHeader>
        <CardContent className="py-4">
          <Input
            placeholder="Search by formula ID or name..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Formulas ({filtered.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Formula ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((formula) => (
                  <TableRow
                    key={formula.formula_id}
                    onClick={() => setDetailId(formula.formula_id)}
                    className="cursor-pointer hover:bg-muted/30"
                  >
                    <TableCell className="font-medium">{formula.formula_id}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">{formula.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{formula.confidence}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" onClick={(e) => {
                        e.stopPropagation()
                        setDetailId(formula.formula_id)
                      }}>
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-4">
                      No formulas found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {detailId && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center" onClick={() => setDetailId(null)}>
          <div className="bg-background p-6 rounded-xl shadow-2xl border w-full max-w-lg mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-lg font-semibold">Formula Detail</h2>
              <Button variant="ghost" size="sm" onClick={() => setDetailId(null)}>
                Close
              </Button>
            </div>
            <div className="space-y-3">
              {(() => {
                const formula = formulas.find((f) => f.formula_id === detailId)
                if (!formula) return <span className="text-muted-foreground">Loading...</span>
                return (
                  <>
                    <div>
                      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Formula ID</span>
                      <p className="font-mono text-sm">{formula.formula_id}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Name</span>
                      <p className="text-sm">{formula.name}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Confidence</span>
                      <p>{formula.confidence}</p>
                    </div>
                    {formula.source_url && (
                      <div>
                        <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Source</span>
                        <a href={formula.source_url} target="_blank" rel="noopener noreferrer" className="text-primary underline text-sm">
                          {formula.source_url}
                        </a>
                      </div>
                    )}
                    <div>
                      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Description</span>
                      <p className="text-sm">{formula.description ?? '—'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Formula</span>
                      <p className="font-mono text-xs break-all">{formula.formula}</p>
                    </div>
                  </>
                )
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { useListFormulasApiV1FormulasGet } from '@/api/formulas/formulas'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useDebounce } from '@/hooks/useDebounce'
import { Spinner } from '@/components/ui/spinner'
import { toast } from '@/components/ui/toast'

export default function FormulasPage() {
  const [query, setQuery] = useState('')
  const [detailId, setDetailId] = useState<string | null>(null)
  const debounced = useDebounce(query, 300)

  const { data, isLoading, error, refetch } = useListFormulasApiV1FormulasGet({
    query: { refetchInterval: 60_000 },
  })

  const formulas = data ?? []
  const filtered = formulas.filter(
    (f) =>
      f.formula_id.toLowerCase().includes(debounced.toLowerCase()) ||
      f.name.toLowerCase().includes(debounced.toLowerCase())
  )

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Formula Reference</h1>
        <div className="h-32 w-full bg-muted rounded animate-pulse" />
      </div>
    )
  }

  if (error) {
    toast.error(`Failed to load formulas: ${(error as Error).message ?? String(error)}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Formula Reference</h1>
          <p className="text-muted-foreground">
            Lookup formulas used by the calculators.
          </p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          Refresh
        </Button>
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
            {(() => {
              const formula = formulas.find((f) => f.formula_id === detailId)
              if (!formula) return <Spinner />
              return (
                <div className="space-y-3">
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
                </div>
              )
            })()}
          </div>
        </div>
      )}
    </div>
  )
}

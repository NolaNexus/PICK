import { useMemo, useState } from "react"
import { useSnapshot } from "@/lib/hooks"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"

interface FormulaRow {
  formula_id?: string
  name?: string
  description?: string
  formula?: string
  example?: string
  components?: string
  category?: string
  patch_version?: string
  confidence?: string
}

/**
 * The formulas the calculators use, and the ones the stat guide documents.
 */
export function FormulasTab() {
  const { snapshot } = useSnapshot()
  const [query, setQuery] = useState("")

  const calculatorFormulas = snapshot?.formulas ?? []
  const documented = useMemo(
    () =>
      (snapshot?.items ?? []).filter((item) => item.type === "formula") as unknown as FormulaRow[],
    [snapshot],
  )

  const term = query.trim().toLowerCase()
  const matches = (row: FormulaRow) =>
    !term ||
    (row.name ?? "").toLowerCase().includes(term) ||
    (row.formula_id ?? "").toLowerCase().includes(term) ||
    (row.description ?? "").toLowerCase().includes(term)

  const shownCalculator = calculatorFormulas.filter((row) =>
    matches(row as unknown as FormulaRow),
  )
  const shownDocumented = documented.filter(matches)

  return (
    <div className="space-y-6">
      <Input
        placeholder="Search formulas…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="max-w-sm"
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Calculator formulas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {shownCalculator.length === 0 ? (
            <p className="text-sm text-muted-foreground">No formulas found.</p>
          ) : (
            shownCalculator.map((row) => {
              const formula = row as unknown as FormulaRow
              return (
                <div key={formula.formula_id} className="border-b pb-3 last:border-b-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{formula.name}</span>
                    <Badge variant="outline">{formula.formula_id}</Badge>
                  </div>
                  {formula.description ? (
                    <p className="text-sm text-muted-foreground">{formula.description}</p>
                  ) : null}
                  {formula.formula ? (
                    <p className="mt-1 font-mono text-xs">{formula.formula}</p>
                  ) : null}
                </div>
              )
            })
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Documented formulas</CardTitle>
        </CardHeader>
        <CardContent>
          {shownDocumented.length === 0 ? (
            <p className="text-sm text-muted-foreground">No formulas found.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Formula</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shownDocumented.map((row, index) => (
                  <TableRow key={`${row.name}-${index}`}>
                    <TableCell className="font-medium">{row.name}</TableCell>
                    <TableCell>
                      {row.category ? <Badge variant="outline">{row.category}</Badge> : null}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{row.formula}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * The mastery ladder of each area.
 */
export function MasteryTab() {
  const { snapshot } = useSnapshot()
  const [query, setQuery] = useState("")

  const areas = useMemo(() => {
    const entries = (snapshot?.items ?? []).filter((item) => item.type === "mastery")
    const byArea = new Map<string, typeof entries>()

    for (const entry of entries) {
      const data = entry.data as Record<string, unknown> | undefined
      const location = typeof data?.location === "string" ? data.location : "Unknown"
      const list = byArea.get(location) ?? []
      list.push(entry)
      byArea.set(location, list)
    }

    return [...byArea.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [snapshot])

  const term = query.trim().toLowerCase()
  const shown = term
    ? areas.filter(([area]) => area.toLowerCase().includes(term))
    : areas

  return (
    <div className="space-y-4">
      <Input
        placeholder="Search areas…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="max-w-sm"
      />

      {shown.length === 0 ? (
        <p className="text-sm text-muted-foreground">No mastery found.</p>
      ) : (
        shown.map(([area, entries]) => (
          <Card key={area}>
            <CardHeader>
              <CardTitle className="text-base">{area}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {entries.map((entry) => {
                const data = entry.data as Record<string, unknown> | undefined
                const steps = Array.isArray(data?.steps) ? (data?.steps as string[]) : []
                const boost = typeof data?.boost_type === "string" ? data.boost_type : null
                const rewards = typeof data?.rewards === "string" ? data.rewards : null

                return (
                  <div key={entry.slug} className="border-b pb-2 last:border-b-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{entry.name}</span>
                      {boost ? <Badge variant="outline">{boost}</Badge> : null}
                    </div>
                    {steps.length > 0 ? (
                      <ul className="mt-1 list-disc pl-5 text-xs text-muted-foreground">
                        {steps.map((step, index) => (
                          <li key={index}>{step}</li>
                        ))}
                      </ul>
                    ) : null}
                    {rewards ? (
                      <p className="mt-1 text-xs text-muted-foreground">{rewards}</p>
                    ) : null}
                  </div>
                )
              })}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  )
}

/**
 * The chance tables for rolling a mutation.
 */
export function MutationsTab() {
  const { snapshot } = useSnapshot()

  const effects = useMemo(
    () => (snapshot?.items ?? []).filter((item) => item.type === "mutation_effect"),
    [snapshot],
  )
  const chances = useMemo(
    () => (snapshot?.items ?? []).filter((item) => item.type === "mutation_chance"),
    [snapshot],
  )

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mutations</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mutation</TableHead>
                <TableHead>Multiplier</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {effects.map((entry) => {
                const data = entry.data as Record<string, unknown> | undefined
                return (
                  <TableRow key={entry.slug}>
                    <TableCell className="font-medium">{entry.name}</TableCell>
                    <TableCell>
                      {data?.multiplier != null ? `${data.multiplier}x` : "—"}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Chances</CardTitle>
        </CardHeader>
        <CardContent>
          {chances.length === 0 ? (
            <p className="text-sm text-muted-foreground">No chance tables yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Mineral</TableHead>
                  <TableHead>Chance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {chances.map((entry) => {
                  const data = entry.data as Record<string, unknown> | undefined
                  return (
                    <TableRow key={entry.slug}>
                      <TableCell className="font-medium">{entry.name}</TableCell>
                      <TableCell>
                        {data?.chance != null ? `${data.chance}%` : "—"}
                        {data?.one_in != null ? (
                          <span className="ml-2 text-xs text-muted-foreground">
                            1 in {Number(data.one_in).toLocaleString("en-US")}
                          </span>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

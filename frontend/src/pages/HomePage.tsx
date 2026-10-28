import { Link } from "react-router-dom"
import { useMemo } from "react"
import { useSnapshot } from "@/lib/hooks"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Gem, Shovel, MapPin, Calculator, Newspaper } from "lucide-react"

const SECTIONS = [
  {
    to: "/items",
    title: "Items",
    description: "Gear, consumables and treasure",
    icon: Gem,
    area: "items",
  },
  {
    to: "/minerals",
    title: "Minerals",
    description: "Every ore, sorted by the area it is found in",
    icon: Shovel,
    area: "minerals",
  },
  {
    to: "/world",
    title: "World",
    description: "NPCs, quests, locations and events",
    icon: MapPin,
    area: "world",
  },
  {
    to: "/calculators",
    title: "Calculators",
    description: "Formulas, mastery and mutations",
    icon: Calculator,
    area: "calculators",
  },
]

export default function HomePage() {
  const { snapshot, taxonomy, loading } = useSnapshot()

  const sectionCounts = useMemo(() => {
    const result: Record<string, number> = {}
    if (!snapshot) return result

    for (const item of snapshot.items) {
      const area = taxonomy.entries.get(item.type)?.area
      if (!area) continue
      result[area] = (result[area] ?? 0) + 1
    }
    return result
  }, [snapshot, taxonomy])

  const updated = snapshot?.meta?.last_scrape?.finished_at
    ? new Date(snapshot.meta.last_scrape.finished_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Prospecting, documented.
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          A community-built companion for Prospecting! — every item, ore and place, with where to
          find them and what they do.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SECTIONS.map((section) => {
          const Icon = section.icon
          return (
            <Link key={section.to} to={section.to}>
              <Card className="h-full transition-colors hover:border-gold-500">
                <CardHeader>
                  <Icon className="h-5 w-5 text-gold-500" />
                  <CardTitle className="text-lg">{section.title}</CardTitle>
                  <p className="text-sm text-muted-foreground">{section.description}</p>
                </CardHeader>
                <CardContent>
                  <span className="text-sm text-muted-foreground">
                    {loading ? "…" : `${sectionCounts[section.area] ?? 0} entries`}
                  </span>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Look something up
        </h2>
        <Link to="/search" className="block max-w-xl">
          <Input placeholder="Search items, ores, quests and places…" readOnly />
        </Link>
        <p className="text-xs text-muted-foreground">
          <Link to="/news" className="underline underline-offset-2 hover:text-foreground">
            <Newspaper className="mr-1 inline h-3 w-3" />
            Community news
          </Link>
          {updated && (
            <>
              {" · "}
              Data updated {updated}
            </>
          )}
          {snapshot?.meta?.game_version?.version && (
            <> · Game version {snapshot.meta.game_version.version}</>
          )}
        </p>
      </section>
    </div>
  )
}

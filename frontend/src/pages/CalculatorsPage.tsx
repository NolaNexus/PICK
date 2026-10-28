import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  calculateEV,
  calculateTTG,
  calculateModifierOdds,
  calculateBestPan,
} from '@/lib/calculators'
import {
  calculateMuseumOptimizer,
} from '@/lib/museum'
import { snapshotCache } from '@/lib/snapshot'
import type { SnapshotData } from '@/lib/snapshot'
import { FormulasTab, MasteryTab, MutationsTab } from '@/components/calculators/reference'
import type {
  EVResponse,
  TTGResponse,
  ModifierOddsResponse,
  BestPanResponse,
  MuseumCalculatorResponse,
  PanRecommendation,
  PanRecommendationPan,
  SlotRecommendation,
} from '@/api/pick.schemas'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Plus, Clock, ShieldAlert, Compass, TrendingUp, Sigma, Sparkles } from 'lucide-react'

const evSchema = z.object({
  luck: z.coerce.number().default(0),
  modifier_boost: z.coerce.number().default(0),
  capacity: z.coerce.number().default(0),
  quality: z.coerce.number().min(0).max(1).default(1),
  autopan: z.boolean().default(false),
  mastered_shovel: z.boolean().default(false),
  solar_magnifier: z.boolean().default(false),
  modifier_surge: z.boolean().default(false),
})

const ttgSchema = z.object({
  goal_value: z.coerce.number().gt(0),
  location_ev_per_pan: z.coerce.number().min(0).default(0),
  capacity: z.coerce.number().gt(0),
  dig_strength: z.coerce.number().gt(0),
  dig_speed: z.coerce.number().gt(0),
  shake_strength: z.coerce.number().gt(0),
  shake_speed: z.coerce.number().min(0).default(0),
})

const morSchema = z.object({
  panel_modifier_boost: z.coerce.number().min(0).default(0),
  solar_magnifier: z.boolean().default(false),
  modifier_surge: z.boolean().default(false),
})

const bpgSchema = z.object({
  dig_strength: z.coerce.number().gt(0),
  shake_strength: z.coerce.number().gt(0),
  shake_speed: z.coerce.number().min(0).default(0),
  target_capacity: z.coerce.number().min(0).default(0),
  min_luck: z.coerce.number().min(0).default(0),
  min_size_boost: z.coerce.number().min(0).default(0),
  min_modifier_boost: z.coerce.number().min(0).default(0),
})

const museumSchema = z.object({
  size_boost: z.coerce.number().min(0).default(0),
  mode: z.enum(['optimize', 'project', 'weight_gate', 'unlock_cost']).default('optimize'),
})

type EvRow = { name: string; base_price: number; base_weight: number; rarity: string }
type BpgPan = { name: string; capacity: number; dig_strength: number; shake_strength: number; shake_speed: number; luck: number; size_boost: number; modifier_boost: number }
type MuseumOre = { name: string; rarity: string; kg: number; modifier: string | null }

function statRow(label: string, value: React.ReactNode) {
  return (
    <div className="flex justify-between text-sm mb-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export default function CalculatorsPage() {
  const [activeTab, setActiveTab] = useState('ev')

  const evForm = useForm<z.infer<typeof evSchema>>({
    resolver: zodResolver(evSchema),
    defaultValues: { luck: 0, modifier_boost: 0, capacity: 0, quality: 1, autopan: false, mastered_shovel: false, solar_magnifier: false, modifier_surge: false },
  })
  const [evDropTable, setEvDropTable] = useState<EvRow[]>([
    { name: '', base_price: 0, base_weight: 1, rarity: 'common' },
  ])
  const [evResult, setEvResult] = useState<EVResponse | null>(null)
  const [evSubmitting, setEvSubmitting] = useState(false)

  const ttgForm = useForm<z.infer<typeof ttgSchema>>({
    resolver: zodResolver(ttgSchema),
    defaultValues: { goal_value: 1000000, location_ev_per_pan: 0, capacity: 100, dig_strength: 50, dig_speed: 100, shake_strength: 50, shake_speed: 500 },
  })
  const [ttgResult, setTtgResult] = useState<TTGResponse | null>(null)
  const [ttgSubmitting, setTtgSubmitting] = useState(false)

  const morForm = useForm<z.infer<typeof morSchema>>({
    resolver: zodResolver(morSchema),
    defaultValues: { panel_modifier_boost: 0, solar_magnifier: false, modifier_surge: false },
  })
  const [morResult, setMorResult] = useState<ModifierOddsResponse | null>(null)
  const [morSubmitting, setMorSubmitting] = useState(false)

  const bpgForm = useForm<z.infer<typeof bpgSchema>>({
    resolver: zodResolver(bpgSchema),
    defaultValues: { dig_strength: 50, shake_strength: 50, shake_speed: 500, target_capacity: 0, min_luck: 0, min_size_boost: 0, min_modifier_boost: 0 },
  })
  const [bpgPans, setBpgPans] = useState<BpgPan[]>([
    { name: '', capacity: 50, dig_strength: 10, shake_strength: 10, shake_speed: 100, luck: 0, size_boost: 0, modifier_boost: 0 },
  ])
  const [bpgResult, setBpgResult] = useState<BestPanResponse | null>(null)
  const [bpgSubmitting, setBpgSubmitting] = useState(false)

  const museumForm = useForm<z.infer<typeof museumSchema>>({
    resolver: zodResolver(museumSchema),
    defaultValues: { size_boost: 0, mode: 'optimize' },
  })
  const [museumOres, setMuseumOres] = useState<MuseumOre[]>([
    { name: '', rarity: 'common', kg: 0, modifier: null },
  ])
  const [museumResult, setMuseumResult] = useState<MuseumCalculatorResponse | null>(null)
  const [museumSubmitting, setMuseumSubmitting] = useState(false)

  const [snapshot, setSnapshot] = useState<SnapshotData | null>(null)

  const addEvRow = () => setEvDropTable([...evDropTable, { name: '', base_price: 0, base_weight: 1, rarity: 'common' }])
  const setEvRow = (i: number, field: keyof EvRow, value: string | number) => {
    const next = [...evDropTable]
    next[i] = { ...next[i], [field]: value }
    setEvDropTable(next)
  }
  const handleEvSubmit = async (values: z.infer<typeof evSchema>) => {
    setEvSubmitting(true)
    try {
      const result = calculateEV({
        locationDropTable: evDropTable.map((r) => ({ base_price: r.base_price, base_weight: r.base_weight, rarity: r.rarity })),
        luck: values.luck,
        modifierBoost: values.modifier_boost,
        quality: values.quality,
        autopan: values.autopan,
        masteredShovel: values.mastered_shovel,
        solarMagnifier: values.solar_magnifier,
        modifierSurge: values.modifier_surge,
        capacity: values.capacity,
      })
      setEvResult({
        ev_per_pan: result.evPerPan,
        items_per_pan: result.itemsPerPan,
        quality_multiplier: result.qualityMultiplier,
        effective_modifier_boost: result.effectiveModifierBoost,
        modifier_distribution: result.modifierDistribution,
        pct_modified: result.pctModified,
      })
    } finally {
      setEvSubmitting(false)
    }
  }

  const handleTtgSubmit = async (values: z.infer<typeof ttgSchema>) => {
    setTtgSubmitting(true)
    try {
      const result = calculateTTG({
        goalValue: values.goal_value,
        locationEvPerPan: values.location_ev_per_pan,
        capacity: values.capacity,
        digStrength: values.dig_strength,
        digSpeed: values.dig_speed,
        shakeStrength: values.shake_strength,
        shakeSpeed: values.shake_speed,
      })
      setTtgResult({
        hours_to_goal: result.hoursToGoal,
        pans_per_hour: result.pansPerHour,
        ev_per_hour: result.evPerHour,
        ev_per_pan: result.evPerPan,
        digs_per_pan: result.digsPerPan,
        dig_time_per_dig: result.digTimePerDig,
        shake_time: result.shakeTime,
      })
    } finally {
      setTtgSubmitting(false)
    }
  }

  const handleMorSubmit = async (values: z.infer<typeof morSchema>) => {
    setMorSubmitting(true)
    try {
      const result = calculateModifierOdds({
        panelModifierBoost: values.panel_modifier_boost,
        solarMagnifier: values.solar_magnifier,
        modifierSurge: values.modifier_surge,
      })
      setMorResult({
        effective_modifier_boost_job1: result.effectiveModifierBoostJob1,
        effective_modifier_boost_job2: result.effectiveModifierBoostJob2,
        pct_ores_modified: result.pctOresModified,
        modifier_distribution: result.modifierDistribution,
        note: result.note,
      })
    } finally {
      setMorSubmitting(false)
    }
  }

  const setBpgPan = (i: number, field: keyof BpgPan, value: string | number) => {
    const next = [...bpgPans]
    next[i] = { ...next[i], [field]: value }
    setBpgPans(next)
  }
  const addBpgPan = () => setBpgPans([...bpgPans, { name: '', capacity: 50, dig_strength: 10, shake_strength: 10, shake_speed: 100, luck: 0, size_boost: 0, modifier_boost: 0 }])
  const handleBpgSubmit = async (values: z.infer<typeof bpgSchema>) => {
    setBpgSubmitting(true)
    try {
      const result = calculateBestPan({
        pans: bpgPans.map((p) => ({
          name: p.name,
          capacity: p.capacity,
          digStrength: p.dig_strength,
          shakeStrength: p.shake_strength,
          shakeSpeed: p.shake_speed,
          luck: p.luck,
          sizeBoost: p.size_boost,
          modifierBoost: p.modifier_boost,
          data: {
            capacity: p.capacity,
            dig_strength: p.dig_strength,
            shake_strength: p.shake_strength,
            shake_speed: p.shake_speed,
            luck: p.luck,
            size_boost: p.size_boost,
            modifier_boost: p.modifier_boost,
          },
        })),
        digStrength: values.dig_strength,
        shakeStrength: values.shake_strength,
        shakeSpeed: values.shake_speed,
        targetCapacity: values.target_capacity || undefined,
        minLuck: values.min_luck || undefined,
        minSizeBoost: values.min_size_boost || undefined,
        minModifierBoost: values.min_modifier_boost || undefined,
      })
      setBpgResult({
        criteria: result.criteria,
        recommendations: result.recommendations.map((rec) => ({
          pan: rec.pan as unknown as PanRecommendationPan,
          score: rec.score,
          capacity: rec.capacity,
          digs_per_pan: rec.digsPerPan,
          pans_per_hour: rec.pansPerHour,
          luck: rec.luck,
          size_boost: rec.sizeBoost,
          modifier_boost: rec.modifierBoost,
        })),
      })
    } finally {
      setBpgSubmitting(false)
    }
  }

  const setMuseumOre = (i: number, field: keyof MuseumOre, value: string | number | null) => {
    const next = [...museumOres]
    next[i] = { ...next[i], [field]: value }
    setMuseumOres(next)
  }
  const addMuseumOre = () => setMuseumOres([...museumOres, { name: '', rarity: 'common', kg: 0, modifier: null }])
  const handleMuseumSubmit = async (values: z.infer<typeof museumSchema>) => {
    setMuseumSubmitting(true)
    try {
      const oreDb: Record<string, Record<string, unknown>> = {}
      if (snapshot) {
        const items = snapshotCache.getItems(snapshot)
        for (const item of items) {
          const data = item.data as Record<string, unknown> | undefined
          const rarity = data?.rarity as string | undefined
          if (rarity) {
            oreDb[`${item.name}|${rarity}`] = data ?? {}
          }
        }
      }
      for (const ore of museumOres) {
        if (!oreDb[`${ore.name}|${ore.rarity}`]) {
          oreDb[`${ore.name}|${ore.rarity}`] = { rarity: ore.rarity }
        }
      }

      const result = calculateMuseumOptimizer({
        availableOres: museumOres.map((o) => ({ name: o.name, rarity: o.rarity, kg: o.kg, modifier: o.modifier ?? undefined })),
        unlockedDisplays: [],
        targetStats: {},
        sizeBoost: values.size_boost,
      })

      setMuseumResult({
        slot_recommendations: result.slot_recommendations.map((rec) => ({
          slot_id: rec.slot_id,
          rarity: rec.rarity,
          slot_index: rec.slot_index,
          current_ore: rec.current_ore,
          current_kg: rec.current_kg,
          current_modifier: rec.current_modifier,
          current_boost: rec.current_boost,
          effective_boost: rec.current_boost,
          ore_kg: rec.current_kg,
          score: 0,
          modifier: rec.current_modifier,
          best_available_ore: rec.best_available_ore,
          recommended_ore: rec.best_available_ore ?? rec.current_ore ?? '',
          best_available_kg: rec.best_available_kg,
          best_available_modifier: rec.best_available_modifier,
          best_boost: rec.best_boost,
          stat_deltas: rec.stat_deltas,
          recommendation: rec.recommendation,
        })),
        total_stats: result.total_stats,
        by_rarity: result.by_rarity,
        unlock_costs: {
          next_unlock: null,
          total_remaining_money: result.unlock_costs.money_cost,
          total_remaining_shards: result.unlock_costs.shards_cost,
        },
        weight_gate_info: result.weight_gate_info,
      })
    } finally {
      setMuseumSubmitting(false)
    }
  }

  const loadSnapshot = async () => {
    try {
      const data = await snapshotCache.fetch(false)
      setSnapshot(data)
    } catch {
      // Non-fatal; the museum will use an empty ore DB
    }
  }

  // The museum and the reference tabs read the snapshot.
  const needsSnapshot =
    activeTab === 'museum' ||
    activeTab === 'formulas' ||
    activeTab === 'mastery' ||
    activeTab === 'mutations'

  useEffect(() => {
    if (needsSnapshot && !snapshot) {
      void loadSnapshot()
    }
  }, [needsSnapshot, snapshot])

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Calculators</h1>
          <p className="text-muted-foreground">Prospecting calculators. Runs entirely in your browser.</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="ev" className="text-sm">
            <Plus className="h-3 w-3 mr-2" /> Expected Value
          </TabsTrigger>
          <TabsTrigger value="ttg" className="text-sm">
            <Clock className="h-3 w-3 mr-2" /> Time to Goal
          </TabsTrigger>
          <TabsTrigger value="mor" className="text-sm">
            <ShieldAlert className="h-3 w-3 mr-2" /> Modifier Odds
          </TabsTrigger>
          <TabsTrigger value="bpg" className="text-sm">
            <Compass className="h-3 w-3 mr-2" /> Best Pan
          </TabsTrigger>
          <TabsTrigger value="museum" className="text-sm">
            <TrendingUp className="h-3 w-3 mr-2" /> Museum
          </TabsTrigger>
          <TabsTrigger value="formulas" className="text-sm">
            <Sigma className="h-3 w-3 mr-2" /> Formulas
          </TabsTrigger>
          <TabsTrigger value="mastery" className="text-sm">
            <TrendingUp className="h-3 w-3 mr-2" /> Mastery
          </TabsTrigger>
          <TabsTrigger value="mutations" className="text-sm">
            <Sparkles className="h-3 w-3 mr-2" /> Mutations
          </TabsTrigger>
        </TabsList>

        <TabsContent value="formulas">
          <FormulasTab />
        </TabsContent>

        <TabsContent value="mastery">
          <MasteryTab />
        </TabsContent>

        <TabsContent value="mutations">
          <MutationsTab />
        </TabsContent>

        <TabsContent value="ev" className="space-y-4">
          <form onSubmit={evForm.handleSubmit(handleEvSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="col-span-1">
                <Card>
                  <CardHeader><CardTitle>Drop Table</CardTitle></CardHeader>
                  <CardContent className="p-3">
                    <div className="space-y-3">
                      {evDropTable.map((row, i) => (
                        <div key={i} className="grid grid-cols-4 gap-2 items-end">
                          <Input value={row.name} onChange={(e) => setEvRow(i, 'name', e.target.value)} placeholder="Item name" />
                          <Input type="number" value={row.base_price} onChange={(e) => setEvRow(i, 'base_price', Number(e.target.value) || 0)} placeholder="Price" />
                          <Input type="number" value={row.base_weight} onChange={(e) => setEvRow(i, 'base_weight', Number(e.target.value) || 1)} placeholder="Weight" />
                          <Input value={row.rarity} onChange={(e) => setEvRow(i, 'rarity', e.target.value)} placeholder="Rarity" />
                        </div>
                      ))}
                      <Button type="button" variant="outline" size="sm" onClick={addEvRow} className="w-auto">
                        Add row
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
              <div className="space-y-4">
                <Card>
                  <CardHeader><CardTitle>Panel & Boosts</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <Input {...evForm.register('luck')} type="number" placeholder="Luck" />
                      <Input {...evForm.register('modifier_boost')} type="number" placeholder="Modifier Boost" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Input {...evForm.register('capacity')} type="number" placeholder="Capacity" />
                      <Input {...evForm.register('quality')} type="number" step="0.01" placeholder="Quality (0-1)" />
                    </div>
                    <div className="flex items-center gap-2">
                      <input id="autopan" type="checkbox" {...evForm.register('autopan')} className="h-4 w-4" />
                      <label htmlFor="autopan" className="text-sm">Auto-pan</label>
                    </div>
                    <div className="flex items-center gap-2">
                      <input id="mastered" type="checkbox" {...evForm.register('mastered_shovel')} className="h-4 w-4" />
                      <label htmlFor="mastered" className="text-sm">Mastered shovel</label>
                    </div>
                    <div className="flex items-center gap-2">
                      <input id="solar" type="checkbox" {...evForm.register('solar_magnifier')} className="h-4 w-4" />
                      <label htmlFor="solar" className="text-sm">Solar magnifier</label>
                    </div>
                    <div className="flex items-center gap-2">
                      <input id="surge" type="checkbox" {...evForm.register('modifier_surge')} className="h-4 w-4" />
                      <label htmlFor="surge" className="text-sm">Modifier surge</label>
                    </div>
                  </CardContent>
                </Card>
                <Button type="submit" className="w-full" disabled={evSubmitting}>
                  {evSubmitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current mr-2" /> : null} Calculate EV
                </Button>
              </div>
            </div>
            {evResult && (
              <Card>
                <CardHeader><CardTitle>EV Result</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {statRow('EV / pan', evResult.ev_per_pan ?? '—')}
                  {statRow('Items / pan', evResult.items_per_pan ?? '—')}
                  {statRow('Quality mult.', evResult.quality_multiplier ?? '—')}
                  {statRow('Effective modifier boost', evResult.effective_modifier_boost ?? '—')}
                  {statRow('% modified', evResult.pct_modified ?? '—')}
                </CardContent>
              </Card>
            )}
          </form>
        </TabsContent>

        <TabsContent value="ttg" className="space-y-4">
          <form onSubmit={ttgForm.handleSubmit(handleTtgSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Input {...ttgForm.register('goal_value')} type="number" placeholder="Goal value" />
              <Input {...ttgForm.register('location_ev_per_pan')} type="number" placeholder="Location EV / pan" />
              <Input {...ttgForm.register('capacity')} type="number" placeholder="Capacity" />
              <Input {...ttgForm.register('dig_strength')} type="number" placeholder="Dig strength" />
              <Input {...ttgForm.register('dig_speed')} type="number" placeholder="Dig speed" />
              <Input {...ttgForm.register('shake_strength')} type="number" placeholder="Shake strength" />
              <Input {...ttgForm.register('shake_speed')} type="number" placeholder="Shake speed" />
              <Button type="submit" className="w-full" disabled={ttgSubmitting}>
                {ttgSubmitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current mr-2" /> : null} Calculate TTG
              </Button>
            </div>
            {ttgResult && (
              <Card>
                <CardHeader><CardTitle>TTG Result</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {statRow('Hours to goal', ttgResult.hours_to_goal ?? '—')}
                  {statRow('Pans / hour', ttgResult.pans_per_hour ?? '—')}
                  {statRow('EV / hour', ttgResult.ev_per_hour ?? '—')}
                  {statRow('EV / pan', ttgResult.ev_per_pan ?? '—')}
                  {statRow('Digs / pan', ttgResult.digs_per_pan ?? '—')}
                  {statRow('Dig time / dig', ttgResult.dig_time_per_dig ?? '—')}
                  {statRow('Shake time', ttgResult.shake_time ?? '—')}
                </CardContent>
              </Card>
            )}
          </form>
        </TabsContent>

        <TabsContent value="mor" className="space-y-4">
          <form onSubmit={morForm.handleSubmit(handleMorSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Input {...morForm.register('panel_modifier_boost')} type="number" placeholder="Panel modifier boost" />
              <div className="flex items-center gap-2">
                <input id="morSolar" type="checkbox" {...morForm.register('solar_magnifier')} className="h-4 w-4" />
                <label htmlFor="morSolar" className="text-sm">Solar magnifier</label>
              </div>
              <div className="flex items-center gap-2">
                <input id="morSurge" type="checkbox" {...morForm.register('modifier_surge')} className="h-4 w-4" />
                <label htmlFor="morSurge" className="text-sm">Modifier surge</label>
              </div>
              <Button type="submit" className="w-full" disabled={morSubmitting}>
                {morSubmitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current mr-2" /> : null} Calculate Odds
              </Button>
            </div>
            {morResult && (
              <Card>
                <CardHeader><CardTitle>Modifier Odds</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  {statRow('Effective boost (job 1)', morResult.effective_modifier_boost_job1 ?? '—')}
                  {statRow('Effective boost (job 2)', morResult.effective_modifier_boost_job2 ?? '—')}
                  {statRow('% ores modified', morResult.pct_ores_modified ?? '—')}
                  {morResult.note && <p className="text-sm text-muted-foreground">{morResult.note}</p>}
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Modifier distribution</h3>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      {Object.entries(morResult.modifier_distribution ?? {}).map(([mod, pct]) => (
                        <div key={mod} className="flex justify-between">
                          <span className="text-muted-foreground">{mod}</span>
                          <span>{Number(pct).toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </form>
        </TabsContent>

        <TabsContent value="bpg" className="space-y-4">
          <form onSubmit={bpgForm.handleSubmit(handleBpgSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="col-span-1">
                <Card>
                  <CardHeader><CardTitle>Pans</CardTitle></CardHeader>
                  <CardContent className="p-3">
                    <div className="space-y-3">
                      {bpgPans.map((pan, i) => (
                        <div key={i} className="grid grid-cols-7 gap-2 items-end">
                          <Input value={pan.name} onChange={(e) => setBpgPan(i, 'name', e.target.value)} placeholder="Pan name" />
                          <Input type="number" value={pan.capacity} onChange={(e) => setBpgPan(i, 'capacity', Number(e.target.value) || 0)} placeholder="Capacity" />
                          <Input type="number" value={pan.dig_strength} onChange={(e) => setBpgPan(i, 'dig_strength', Number(e.target.value) || 0)} placeholder="Dig str." />
                          <Input type="number" value={pan.shake_strength} onChange={(e) => setBpgPan(i, 'shake_strength', Number(e.target.value) || 0)} placeholder="Shake str." />
                          <Input type="number" value={pan.shake_speed} onChange={(e) => setBpgPan(i, 'shake_speed', Number(e.target.value) || 0)} placeholder="Shake spd." />
                          <Input type="number" value={pan.luck} onChange={(e) => setBpgPan(i, 'luck', Number(e.target.value) || 0)} placeholder="Luck" />
                          <Input type="number" value={pan.modifier_boost} onChange={(e) => setBpgPan(i, 'modifier_boost', Number(e.target.value) || 0)} placeholder="Mod. boost" />
                        </div>
                      ))}
                      <Button type="button" variant="outline" size="sm" onClick={addBpgPan} className="w-auto">
                        Add pan
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
              <div className="space-y-4">
                <Card>
                  <CardHeader><CardTitle>Build params</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <Input {...bpgForm.register('dig_strength')} type="number" placeholder="Dig strength" />
                    <Input {...bpgForm.register('shake_strength')} type="number" placeholder="Shake strength" />
                    <Input {...bpgForm.register('shake_speed')} type="number" placeholder="Shake speed" />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <Input {...bpgForm.register('target_capacity')} type="number" placeholder="Target capacity" />
                    <Input {...bpgForm.register('min_luck')} type="number" placeholder="Min luck" />
                    <Input {...bpgForm.register('min_size_boost')} type="number" placeholder="Min size boost" />
                    <Input {...bpgForm.register('min_modifier_boost')} type="number" placeholder="Min modifier boost" />
                  </CardContent>
                </Card>
                <Button type="submit" className="w-full" disabled={bpgSubmitting}>
                  {bpgSubmitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current mr-2" /> : null} Find Best Pan
                </Button>
              </div>
            </div>
            {bpgResult && bpgResult.recommendations && (
              <Card>
                <CardHeader><CardTitle>Recommendations</CardTitle></CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Pan</TableHead>
                          <TableHead className="text-right">Score</TableHead>
                          <TableHead className="text-right">Capacity</TableHead>
                          <TableHead className="text-right">Pans/hr</TableHead>
                          <TableHead className="text-right">Luck</TableHead>
                          <TableHead className="text-right">Size boost</TableHead>
                          <TableHead className="text-right">Mod. boost</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {bpgResult.recommendations.map((rec: PanRecommendation, i: number) => (
                          <TableRow key={i}>
                            <TableCell className="font-medium">{String(rec.pan?.name) ?? '—'}</TableCell>
                            <TableCell className="text-right">{rec.score?.toFixed(1) ?? '—'}</TableCell>
                            <TableCell className="text-right">{rec.capacity ?? '—'}</TableCell>
                            <TableCell className="text-right">{rec.pans_per_hour?.toFixed(1) ?? '—'}</TableCell>
                            <TableCell className="text-right">{rec.luck ?? '—'}</TableCell>
                            <TableCell className="text-right">{rec.size_boost ?? '—'}</TableCell>
                            <TableCell className="text-right">{rec.modifier_boost ?? '—'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            )}
          </form>
        </TabsContent>

        <TabsContent value="museum" className="space-y-4">
          <form onSubmit={museumForm.handleSubmit(handleMuseumSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="col-span-1">
                <Card>
                  <CardHeader><CardTitle>Available Ores</CardTitle></CardHeader>
                  <CardContent className="p-3">
                    <div className="space-y-3">
                      {museumOres.map((ore, i) => (
                        <div key={i} className="grid grid-cols-4 gap-2 items-end">
                          <Input value={ore.name} onChange={(e) => setMuseumOre(i, 'name', e.target.value)} placeholder="Ore name" />
                          <Input value={ore.rarity} onChange={(e) => setMuseumOre(i, 'rarity', e.target.value)} placeholder="Rarity" />
                          <Input type="number" value={ore.kg} onChange={(e) => setMuseumOre(i, 'kg', Number(e.target.value) || 0)} placeholder="kg" />
                          <Input value={ore.modifier ?? ''} onChange={(e) => setMuseumOre(i, 'modifier', e.target.value || null)} placeholder="Modifier" />
                        </div>
                      ))}
                      <Button type="button" variant="outline" size="sm" onClick={addMuseumOre} className="w-auto">
                        Add ore
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
              <div className="space-y-4">
                <Card>
                  <CardHeader><CardTitle>Settings</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <Input {...museumForm.register('size_boost')} type="number" placeholder="Size boost" />
                    <div className="flex items-center gap-2">
                      <label className="text-sm">Mode</label>
                      <select {...museumForm.register('mode')} className="border-input bg-background rounded-md border px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        <option value="optimize">Optimize</option>
                        <option value="project">Project</option>
                        <option value="weight_gate">Weight gate</option>
                        <option value="unlock_cost">Unlock cost</option>
                      </select>
                    </div>
                  </CardContent>
                </Card>
                <Button type="submit" className="w-full" disabled={museumSubmitting}>
                  {museumSubmitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current mr-2" /> : null} Calculate Museum
                </Button>
              </div>
            </div>
            {museumResult && (
              <Card>
                <CardHeader><CardTitle>Museum Result</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  {museumResult.slot_recommendations && (
                    <div>
                      <h3 className="text-sm font-semibold mb-2">Slot recommendations</h3>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        {museumResult.slot_recommendations.map((rec: SlotRecommendation, i: number) => (
                          <div key={i} className="flex justify-between">
                            <span className="text-muted-foreground">{rec.slot_id ?? `Slot ${i + 1}`}</span>
                            <span>{rec.recommended_ore ?? '—'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {museumResult.total_stats && (
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      {Object.entries(museumResult.total_stats ?? {}).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-muted-foreground">{k}</span>
                          <span>{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </form>
        </TabsContent>
      </Tabs>
    </div>
  )
}

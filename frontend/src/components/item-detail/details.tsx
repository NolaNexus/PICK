import type { Item } from "@/lib/snapshot.types"
import {
  BulletList,
  Field,
  ItemImage,
  Section,
  StatList,
  TextBlock,
  formatCurrency,
  formatNumber,
  formatTimestamp,
  type StatModifier,
} from "./primitives"

/**
 * The data of an item, as stored on the snapshot.
 *
 * Every field is optional: the shape differs per item type and a payload
 * written by an older build may not have every field.
 */
export type ItemData = Record<string, unknown>

function str(data: ItemData, key: string): string | undefined {
  const value = data[key]
  return typeof value === "string" && value.trim() ? value : undefined
}

function num(data: ItemData, key: string): number | undefined {
  const value = data[key]
  return typeof value === "number" && Number.isFinite(value) ? value : undefined
}

function list(data: ItemData, key: string): string[] | undefined {
  const value = data[key]
  if (!Array.isArray(value)) return undefined
  const entries = value.filter(
    (entry): entry is string => typeof entry === "string" && entry.trim().length > 0,
  )
  return entries.length ? entries : undefined
}

function modifiers(data: ItemData): StatModifier[] | undefined {
  const value = data["modifiers"]
  if (!Array.isArray(value)) return undefined
  const entries = value.filter(
    (entry): entry is StatModifier =>
      !!entry && typeof entry === "object" && typeof (entry as StatModifier).stat === "string",
  )
  return entries.length ? entries : undefined
}

function records(data: ItemData, key: string): Record<string, unknown>[] | undefined {
  const value = data[key]
  if (!Array.isArray(value)) return undefined
  const entries = value.filter((entry): entry is Record<string, unknown> => !!entry && typeof entry === "object")
  return entries.length ? entries : undefined
}

/**
 * The shared shell of a detail view.
 */
export function ItemDetailShell({
  item,
  children,
}: {
  item: Item
  children: React.ReactNode
}) {
  const data = (item.data ?? {}) as ItemData

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <ItemImage src={item.image_url} alt={item.name} />
        <div className="min-w-0 flex-1 space-y-2">
          {str(data, "description") ? (
            <TextBlock>{str(data, "description")}</TextBlock>
          ) : null}
        </div>
      </div>
      {children}
    </div>
  )
}

/**
 * The tools of the game: pans, shovels and sluices share their shape.
 */
export function ToolDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)
  const enchantments = records(data, "enchantments")

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "location") ? <Field label="Location">{str(data, "location")}</Field> : null}
        {str(data, "obtained") ? <Field label="Obtained">{str(data, "obtained")}</Field> : null}
        {str(data, "price") ? <Field label="Price">{str(data, "price")}</Field> : null}
        {str(data, "perk") ? <Field label="Perk">{str(data, "perk")}</Field> : null}
        {str(data, "value") ? <Field label="Value">{str(data, "value")}</Field> : null}
        {str(data, "rarity") ? <Field label="Rarity">{str(data, "rarity")}</Field> : null}
      </dl>
      {statModifiers ? (
        <Section title="Stats">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
      {str(data, "overview") ? (
        <Section title="Overview">
          <TextBlock>{str(data, "overview")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "obtainment") ? (
        <Section title="Obtainment">
          <TextBlock>{str(data, "obtainment")}</TextBlock>
        </Section>
      ) : null}
      {enchantments?.length ? (
        <Section title="Enchantments">
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {enchantments.map((enchantment, index) => {
              const name = str(enchantment, "name") ?? str(enchantment, "effect")
              return (
                <li key={index}>
                  {name}
                  {str(enchantment, "applies_to") ? (
                    <span className="ml-2 text-xs text-muted-foreground">
                      {str(enchantment, "applies_to")}
                    </span>
                  ) : null}
                </li>
              )
            })}
          </ul>
        </Section>
      ) : null}
      {str(data, "trivia") ? (
        <Section title="Trivia">
          <TextBlock>{str(data, "trivia")}</TextBlock>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A recipe: one ingredient per line.
 */
function Recipe({ text }: { text: string }) {
  const lines = text.split("\n").map((line) => line.trim()).filter(Boolean)

  if (lines.length <= 1) {
    return <span>{text}</span>
  }

  return (
    <ul className="list-disc space-y-0.5 pl-4">
      {lines.map((line, index) => (
        <li key={index}>{line}</li>
      ))}
    </ul>
  )
}

/**
 * Equipment: a slot, a recipe and the stats it rolls.
 */
export function EquipmentDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)
  const blueprint = data["blueprint"] as Record<string, unknown> | undefined
  const catalyst = data["catalyst"] as Record<string, unknown> | undefined
  const questSteps = blueprint
    ? (Array.isArray(blueprint.quest_steps) ? blueprint.quest_steps : [])
    : []

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "slot") ? <Field label="Slot">{str(data, "slot")}</Field> : null}
        {str(data, "rarity") ? <Field label="Rarity">{str(data, "rarity")}</Field> : null}
        {str(data, "recipe") ? (
          <Field label="Recipe">
            <Recipe text={str(data, "recipe")!} />
          </Field>
        ) : null}
        {num(data, "price") != null ? (
          <Field label="Price">{formatCurrency(num(data, "price"))}</Field>
        ) : null}
        {catalyst ? (
          <Field label="Mutation catalyst">
            {str(catalyst, "name")}
            {str(catalyst, "mineral") ? (
              <span className="ml-1 text-xs text-muted-foreground">
                ({str(catalyst, "mineral")})
              </span>
            ) : null}
          </Field>
        ) : null}
      </dl>
      {statModifiers ? (
        <Section title="Stats">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
      {blueprint ? (
        <Section title="How to get it">
          <dl className="space-y-2 text-sm">
            {str(blueprint, "quest_giver") ? (
              <Field label="Quest giver">{str(blueprint, "quest_giver")}</Field>
            ) : null}
            {str(blueprint, "quest_name") ? (
              <Field label="Quest">{str(blueprint, "quest_name")}</Field>
            ) : null}
            {str(blueprint, "event_shop") ? (
              <Field label="Event shop">{str(blueprint, "event_shop")}</Field>
            ) : null}
            {str(blueprint, "purchase_info") ? (
              <Field label="Purchase">{str(blueprint, "purchase_info")}</Field>
            ) : null}
          </dl>
          {questSteps.length > 0 ? (
            <ul className="mt-2 space-y-2 text-sm">
              {questSteps.map((step, index) => {
                const entry = step as Record<string, unknown>
                const quest = str(entry, "Quest")
                const sub = str(entry, "QuestSub")
                const rewards = str(entry, "Rewards")
                const lines = Object.entries(entry)
                  .filter(([key]) => key.startsWith("QuestStep"))
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([, value]) => (typeof value === "string" ? value : ""))
                  .filter(Boolean)

                return (
                  <li key={index} className="border-l-2 border-gold-500/40 pl-3">
                    {quest ? <div className="font-medium">{quest}</div> : null}
                    {sub ? <div className="text-muted-foreground">{sub}</div> : null}
                    {lines.length > 0 ? (
                      <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                        {lines.map((line, lineIndex) => (
                          <li key={lineIndex}>{line}</li>
                        ))}
                      </ul>
                    ) : null}
                    {rewards ? (
                      <div className="mt-1 text-xs text-muted-foreground">Rewards: {rewards}</div>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          ) : null}
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A mineral and the places it can be dug up.
 */
export function MineralDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const chances = records(data, "chances")
  const recipes = records(data, "recipes")
  const museum = data["museum"] as Record<string, unknown> | undefined
  const areas = list(data, "areas")

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {num(data, "value") != null ? (
          <Field label="Value">{formatNumber(num(data, "value"))}</Field>
        ) : null}
        {str(data, "tier") ? <Field label="Tier">{str(data, "tier")}</Field> : null}
        {str(data, "rarity") ? <Field label="Rarity">{str(data, "rarity")}</Field> : null}
        {museum ? (
          <>
            {num(museum, "min_weight_kg") != null ? (
              <Field label="Museum weight">
                {formatNumber(num(museum, "min_weight_kg"))} kg
              </Field>
            ) : null}
            {str(museum, "bonus_stat") ? (
              <Field label="Museum bonus">{str(museum, "bonus_stat")}</Field>
            ) : null}
            {str(museum, "max_boost") ? (
              <Field label="Maximum boost">{str(museum, "max_boost")}</Field>
            ) : null}
          </>
        ) : null}
      </dl>
      {areas?.length ? (
        <Section title="Areas">
          <BulletList items={areas} />
        </Section>
      ) : null}
      {list(data, "locations") ? (
        <Section title="Found at">
          <BulletList items={list(data, "locations")} />
        </Section>
      ) : null}
      {chances?.length ? (
        <Section title="Drop chances">
          <ul className="space-y-1 text-sm">
            {chances.map((chance, index) => {
              const location = str(chance, "location")
              const percent = num(chance, "chance_percent")
              const oneIn = num(chance, "one_in")
              return (
                <li key={index} className="flex items-baseline justify-between gap-3">
                  <span className="text-muted-foreground">{location}</span>
                  <span className="font-medium tabular-nums">
                    {percent != null ? `${percent}%` : null}
                    {oneIn != null ? (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        1 in {oneIn.toLocaleString("en-US")}
                      </span>
                    ) : null}
                  </span>
                </li>
              )
            })}
          </ul>
        </Section>
      ) : null}
      {recipes?.length ? (
        <Section title="Recipes">
          <ul className="space-y-2 text-sm">
            {recipes.map((recipe, index) => {
              const station = str(recipe, "station")
              const rarity = str(recipe, "rarity")
              const ingredients = list(recipe, "ingredients")
              return (
                <li key={index}>
                  <div className="font-medium">
                    {station}
                    {rarity ? (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        {rarity}
                      </span>
                    ) : null}
                  </div>
                  {ingredients ? (
                    <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                      {ingredients.map((ingredient, ingredientIndex) => (
                        <li key={ingredientIndex}>{ingredient}</li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              )
            })}
          </ul>
        </Section>
      ) : null}
      {str(data, "museum_usage") ? (
        <Section title="Museum usage">
          <TextBlock>{str(data, "museum_usage")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "trivia") ? (
        <Section title="Trivia">
          <TextBlock>{str(data, "trivia")}</TextBlock>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * An ore that can be placed in a museum display.
 */
export function MuseumOreDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "rarity") ? <Field label="Rarity">{str(data, "rarity")}</Field> : null}
        {num(data, "min_kg") != null ? (
          <Field label="Minimum weight">{formatNumber(num(data, "min_kg"))} kg</Field>
        ) : null}
        {str(data, "bonus_stat") ? (
          <Field label="Bonus stat">{str(data, "bonus_stat")}</Field>
        ) : null}
        {str(data, "max_boost") ? (
          <Field label="Maximum boost">{str(data, "max_boost")}</Field>
        ) : null}
      </dl>
      {statModifiers ? (
        <Section title="Bonus">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A potion: what it costs, what it grants and where to buy it.
 */
export function PotionDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)
  const merchant = data["merchant"] as Record<string, unknown> | undefined

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {num(data, "cost_cash") != null ? (
          <Field label="Price">{formatCurrency(num(data, "cost_cash"))}</Field>
        ) : null}
        {num(data, "cost_shards") != null ? (
          <Field label="Shards">{formatNumber(num(data, "cost_shards"))}</Field>
        ) : null}
        {num(data, "duration_min") != null ? (
          <Field label="Duration">{num(data, "duration_min")} minutes</Field>
        ) : null}
        {str(data, "sold_by") ? <Field label="Sold by">{str(data, "sold_by")}</Field> : null}
        {str(data, "source_location") ? (
          <Field label="Location">{str(data, "source_location")}</Field>
        ) : null}
        {str(data, "effect") ? <Field label="Effect">{str(data, "effect")}</Field> : null}
      </dl>
      {statModifiers ? (
        <Section title="Grants">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
      {merchant ? (
        <Section title="Currently sold">
          <dl className="space-y-2">
            {num(merchant, "stock") != null ? (
              <Field label="Stock">{formatNumber(merchant["stock"] as number)}</Field>
            ) : null}
            {num(merchant, "chance_percent") != null ? (
              <Field label="Chance">
                {formatNumber(merchant["chance_percent"] as number)}%
              </Field>
            ) : null}
            {num(merchant, "price_cash") != null ? (
              <Field label="Price">{formatCurrency(merchant["price_cash"] as number)}</Field>
            ) : null}
            {num(merchant, "price_shards") != null ? (
              <Field label="Shards">
                {formatNumber(merchant["price_shards"] as number)}
              </Field>
            ) : null}
            {str(merchant, "last_seen") ? (
              <Field label="Last seen">{formatTimestamp(str(merchant, "last_seen"))}</Field>
            ) : null}
          </dl>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A consumable: an item that is used up, like a flare or a token.
 */
export function ConsumableDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)
  const merchant = data["merchant"] as Record<string, unknown> | undefined

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {num(data, "cost_cash") != null ? (
          <Field label="Price">{formatCurrency(num(data, "cost_cash"))}</Field>
        ) : null}
        {num(data, "cost_shards") != null ? (
          <Field label="Shards">{formatNumber(num(data, "cost_shards"))}</Field>
        ) : null}
        {str(data, "sold_by") ? <Field label="Sold by">{str(data, "sold_by")}</Field> : null}
        {str(data, "duration_min") ? (
          <Field label="Duration">{str(data, "duration_min")}</Field>
        ) : null}
      </dl>
      {str(data, "obtained") ? (
        <Section title="Obtained">
          <TextBlock>{str(data, "obtained")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "obtainment") ? (
        <Section title="Obtainment">
          <TextBlock>{str(data, "obtainment")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "usage") ? (
        <Section title="Usage">
          <TextBlock>{str(data, "usage")}</TextBlock>
        </Section>
      ) : null}
      {statModifiers ? (
        <Section title="Grants">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
      {merchant ? (
        <Section title="Currently sold">
          <dl className="space-y-2">
            {num(merchant, "stock") != null ? (
              <Field label="Stock">{formatNumber(merchant["stock"] as number)}</Field>
            ) : null}
            {num(merchant, "chance_percent") != null ? (
              <Field label="Chance">
                {formatNumber(merchant["chance_percent"] as number)}%
              </Field>
            ) : null}
            {str(merchant, "last_seen") ? (
              <Field label="Last seen">{formatTimestamp(str(merchant, "last_seen"))}</Field>
            ) : null}
          </dl>
        </Section>
      ) : null}
      {str(data, "notes") ? (
        <Section title="Notes">
          <TextBlock>{str(data, "notes")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "trivia") ? (
        <Section title="Trivia">
          <TextBlock>{str(data, "trivia")}</TextBlock>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A relic: what it does, where to get it and how to use it.
 */
export function RelicDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      {str(data, "obtainment") ? (
        <Section title="Obtainment">
          <TextBlock>{str(data, "obtainment")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "usage") ? (
        <Section title="Usage">
          <TextBlock>{str(data, "usage")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "notes") ? (
        <Section title="Notes">
          <TextBlock>{str(data, "notes")}</TextBlock>
        </Section>
      ) : null}
      {str(data, "trivia") ? (
        <Section title="Trivia">
          <TextBlock>{str(data, "trivia")}</TextBlock>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A quest: who gives it, what it needs and what it pays.
 */
export function QuestDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "location") ? <Field label="Location">{str(data, "location")}</Field> : null}
        {str(data, "npc") ? <Field label="Quest giver">{str(data, "npc")}</Field> : null}
      </dl>
      {list(data, "steps") ? (
        <Section title="Steps">
          <BulletList items={list(data, "steps")} />
        </Section>
      ) : null}
      {str(data, "rewards") ? (
        <Section title="Rewards">
          <TextBlock>{str(data, "rewards")}</TextBlock>
        </Section>
      ) : null}
      {statModifiers ? (
        <Section title="Buffs">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A mastery: the quest that raises it and what it grants.
 */
export function MasteryDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "location") ? <Field label="Location">{str(data, "location")}</Field> : null}
        {str(data, "boost_type") ? (
          <Field label="Boosts">{str(data, "boost_type")}</Field>
        ) : null}
      </dl>
      {list(data, "steps") ? (
        <Section title="Steps">
          <BulletList items={list(data, "steps")} />
        </Section>
      ) : null}
      {str(data, "rewards") ? (
        <Section title="Rewards">
          <TextBlock>{str(data, "rewards")}</TextBlock>
        </Section>
      ) : null}
      {statModifiers ? (
        <Section title="Grants">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A blueprint: what it makes and how to get it.
 */
export function BlueprintDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const steps = records(data, "quest_steps")

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "quest_giver") ? (
          <Field label="Quest giver">{str(data, "quest_giver")}</Field>
        ) : null}
        {str(data, "quest_name") ? (
          <Field label="Quest">{str(data, "quest_name")}</Field>
        ) : null}
        {str(data, "purchase_info") ? (
          <Field label="Purchase">{str(data, "purchase_info")}</Field>
        ) : null}
        {str(data, "event_shop") ? (
          <Field label="Event shop">{str(data, "event_shop")}</Field>
        ) : null}
      </dl>
      {steps?.length ? (
        <Section title="Quest steps">
          <ul className="space-y-3 text-sm">
            {steps.map((step, index) => {
              const quest = str(step, "Quest")
              const sub = str(step, "QuestSub")
              const rewards = str(step, "Rewards")
              const stepLines = Object.entries(step)
                .filter(([key]) => key.startsWith("QuestStep"))
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([, value]) => (typeof value === "string" ? value : ""))
                .filter(Boolean)

              return (
                <li key={index} className="border-l-2 border-gold-500/40 pl-3">
                  {quest ? <div className="font-medium">{quest}</div> : null}
                  {sub ? <div className="text-muted-foreground">{sub}</div> : null}
                  {stepLines.length ? (
                    <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                      {stepLines.map((line, lineIndex) => (
                        <li key={lineIndex}>{line}</li>
                      ))}
                    </ul>
                  ) : null}
                  {rewards ? (
                    <div className="mt-1 text-xs text-muted-foreground">Rewards: {rewards}</div>
                  ) : null}
                </li>
              )
            })}
          </ul>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A rune: what it does and where to find it.
 */
export function RuneDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "location") ? <Field label="Location">{str(data, "location")}</Field> : null}
      </dl>
      {statModifiers ? (
        <Section title="Effect">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * An enchantment and the book it is read from.
 */
export function EnchantmentDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "applies_to") ? (
          <Field label="Applies to">{str(data, "applies_to")}</Field>
        ) : null}
        {str(data, "rarity") ? <Field label="Rarity">{str(data, "rarity")}</Field> : null}
        {str(data, "source") ? <Field label="Source">{str(data, "source")}</Field> : null}
        {str(data, "effects") ? <Field label="Effects">{str(data, "effects")}</Field> : null}
      </dl>
      {statModifiers ? (
        <Section title="Bonus">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A formula from the stat systems guide.
 */
export function FormulaDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "formula") ? (
          <Field label="Formula">
            <span className="font-mono text-xs">{str(data, "formula")}</span>
          </Field>
        ) : null}
        {str(data, "example") ? (
          <Field label="Example">
            <span className="font-mono text-xs">{str(data, "example")}</span>
          </Field>
        ) : null}
        {str(data, "patch_version") ? (
          <Field label="Patch">{str(data, "patch_version")}</Field>
        ) : null}
      </dl>
    </ItemDetailShell>
  )
}

/**
 * An NPC and the places it turns up.
 */
export function NpcDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "region") ? <Field label="Region">{str(data, "region")}</Field> : null}
        {str(data, "role") ? <Field label="Role">{str(data, "role")}</Field> : null}
      </dl>
      {list(data, "locations") ? (
        <Section title="Found at">
          <BulletList items={list(data, "locations")} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A location, an event or any other place in the world.
 */
export function LocationDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "region") ? <Field label="Region">{str(data, "region")}</Field> : null}
        {str(data, "level") ? <Field label="Level">{str(data, "level")}</Field> : null}
        {str(data, "requires") ? <Field label="Requires">{str(data, "requires")}</Field> : null}
        {str(data, "requires_geothermal") ? (
          <Field label="Requires geothermal">Yes</Field>
        ) : null}
      </dl>
      {list(data, "locations") ? (
        <Section title="Sub-locations">
          <BulletList items={list(data, "locations")} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * Treasure chests and treasure maps.
 */
export function TreasureDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const loot = records(data, "loot")

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "obtained_from") ? (
          <Field label="Obtained from">{str(data, "obtained_from")}</Field>
        ) : null}
        {str(data, "location") ? <Field label="Location">{str(data, "location")}</Field> : null}
        {num(data, "base_drop_chance_percent") != null ? (
          <Field label="Drop chance">
            {formatNumber(num(data, "base_drop_chance_percent"))}%
          </Field>
        ) : null}
        {num(data, "max_inventory") != null ? (
          <Field label="Max inventory">{formatNumber(num(data, "max_inventory"))}</Field>
        ) : null}
      </dl>
      {loot?.length ? (
        <Section title="Contains">
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {loot.map((entry, index) => {
              const name = str(entry, "name") ?? str(entry, "label") ?? str(entry, "kind")
              return <li key={index}>{name}</li>
            })}
          </ul>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A museum, its displays and how it works.
 */
export function MuseumDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "rarity") ? <Field label="Rarity">{str(data, "rarity")}</Field> : null}
        {num(data, "free_displays") != null ? (
          <Field label="Free displays">{formatNumber(num(data, "free_displays"))}</Field>
        ) : null}
        {num(data, "locked_displays") != null ? (
          <Field label="Locked displays">{formatNumber(num(data, "locked_displays"))}</Field>
        ) : null}
        {num(data, "total_displays") != null ? (
          <Field label="Total displays">{formatNumber(num(data, "total_displays"))}</Field>
        ) : null}
        {num(data, "money_price") != null ? (
          <Field label="Price">{formatCurrency(num(data, "money_price"))}</Field>
        ) : null}
        {num(data, "shards_price") != null ? (
          <Field label="Shards">{formatNumber(num(data, "shards_price"))}</Field>
        ) : null}
      </dl>
      {list(data, "how_it_works") ? (
        <Section title="How it works">
          <BulletList items={list(data, "how_it_works")} />
        </Section>
      ) : null}
      {list(data, "requirements") ? (
        <Section title="Requirements">
          <BulletList items={list(data, "requirements")} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * An excavation: its sites, its levels and what it drops.
 */
export function ExcavationDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "location") ? <Field label="Location">{str(data, "location")}</Field> : null}
        {str(data, "site") ? <Field label="Site">{str(data, "site")}</Field> : null}
        {num(data, "level") != null ? (
          <Field label="Level">{formatNumber(num(data, "level"))}</Field>
        ) : null}
        {str(data, "cost") ? <Field label="Cost">{str(data, "cost")}</Field> : null}
        {str(data, "unlock_requirement") ? (
          <Field label="Unlock requirement">{str(data, "unlock_requirement")}</Field>
        ) : null}
      </dl>
      {list(data, "rewards") ? (
        <Section title="Rewards">
          <BulletList items={list(data, "rewards")} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A geode and where it is dug up.
 */
export function GeodeDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "location") ? <Field label="Location">{str(data, "location")}</Field> : null}
        {str(data, "requires_geothermal") ? (
          <Field label="Requires geothermal">Yes</Field>
        ) : null}
      </dl>
    </ItemDetailShell>
  )
}

/**
 * A modifier: what it changes and how it is bought.
 */
export function ModifierDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const statModifiers = modifiers(data)

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {num(data, "sell_price_multiplier") != null ? (
          <Field label="Sell price">
            {num(data, "sell_price_multiplier")}x
          </Field>
        ) : null}
        {str(data, "museum_bonus") ? (
          <Field label="Museum bonus">{str(data, "museum_bonus")}</Field>
        ) : null}
        {str(data, "tools") ? <Field label="Tools">{str(data, "tools")}</Field> : null}
        {str(data, "equipment") ? (
          <Field label="Equipment">{str(data, "equipment")}</Field>
        ) : null}
        {str(data, "location_boosts") ? (
          <Field label="Location boosts">{str(data, "location_boosts")}</Field>
        ) : null}
        {str(data, "event_boosts") ? (
          <Field label="Event boosts">{str(data, "event_boosts")}</Field>
        ) : null}
        {str(data, "chance") ? <Field label="Chance">{str(data, "chance")}</Field> : null}
      </dl>
      {statModifiers ? (
        <Section title="Boosts">
          <StatList modifiers={statModifiers} />
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * A trinket and where it is bought.
 */
export function TrinketDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "obtainment") ? (
          <Field label="Obtainment">{str(data, "obtainment")}</Field>
        ) : null}
        {str(data, "effect") ? <Field label="Effect">{str(data, "effect")}</Field> : null}
        {str(data, "rarity") ? <Field label="Rarity">{str(data, "rarity")}</Field> : null}
      </dl>
    </ItemDetailShell>
  )
}

/**
 * A merchant listing that has no item of its own, e.g. a backpack.
 */
export function MerchantItemDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {num(data, "stock") != null ? (
          <Field label="Stock">{formatNumber(num(data, "stock"))}</Field>
        ) : null}
        {num(data, "chance_percent") != null ? (
          <Field label="Chance">{formatNumber(num(data, "chance_percent"))}%</Field>
        ) : null}
        {num(data, "price_cash") != null ? (
          <Field label="Price">{formatCurrency(num(data, "price_cash"))}</Field>
        ) : null}
        {num(data, "price_shards") != null ? (
          <Field label="Shards">{formatNumber(num(data, "price_shards"))}</Field>
        ) : null}
      </dl>
    </ItemDetailShell>
  )
}

/**
 * The fallback for a type without its own view: list what is known.
 */
export function FallbackDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData

  const entries = Object.entries(data).filter(([, value]) => {
    if (value == null) return false
    if (typeof value === "string") return value.trim().length > 0
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === "object") return Object.keys(value as object).length > 0
    return true
  })

  return (
    <ItemDetailShell item={item}>
      {entries.length ? (
        <dl className="space-y-2">
          {entries.map(([key, value]) => (
            <Field key={key} label={key.replace(/_/g, " ")}>
              {typeof value === "object" && value !== null ? (
                <span className="font-mono text-xs">{JSON.stringify(value)}</span>
              ) : (
                String(value)
              )}
            </Field>
          ))}
        </dl>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * An excavation site: what it costs, how long it takes and what it drops.
 */
export function ExcavationSiteDetail({ item }: { item: Item }) {
  const data = (item.data ?? {}) as ItemData
  const drops = records(data, "drops")

  return (
    <ItemDetailShell item={item}>
      <dl className="space-y-2">
        {str(data, "region") ? <Field label="Region">{str(data, "region")}</Field> : null}
        {str(data, "permit_cost") ? (
          <Field label="Permit">{str(data, "permit_cost")}</Field>
        ) : null}
        {str(data, "excavation_cost") ? (
          <Field label="Excavation cost">{str(data, "excavation_cost")}</Field>
        ) : null}
        {str(data, "duration") ? <Field label="Duration">{str(data, "duration")}</Field> : null}
        {str(data, "items_range") ? (
          <Field label="Items per run">{str(data, "items_range")}</Field>
        ) : null}
      </dl>
      {drops?.length ? (
        <Section title="Drops">
          <ul className="space-y-1 text-sm">
            {drops.map((drop, index) => {
              const name = str(drop, "name")
              const chance = str(drop, "chance")
              return (
                <li key={index} className="flex items-baseline justify-between gap-3">
                  <span className="text-muted-foreground">{name}</span>
                  <span className="font-medium tabular-nums">{chance}</span>
                </li>
              )
            })}
          </ul>
        </Section>
      ) : null}
    </ItemDetailShell>
  )
}

/**
 * The detail view to use for an item, by its type.
 */
const DETAILS: Record<string, (props: { item: Item }) => React.ReactElement> = {
  pan: ToolDetail,
  shovel: ToolDetail,
  sluice: ToolDetail,
  equipment: EquipmentDetail,
  mineral: MineralDetail,
  museum_ore: MuseumOreDetail,
  potion: PotionDetail,
  consumable: ConsumableDetail,
  relic: RelicDetail,
  quest: QuestDetail,
  mastery: MasteryDetail,
  blueprint: BlueprintDetail,
  rune: RuneDetail,
  enchantment: EnchantmentDetail,
  enchant_book: EnchantmentDetail,
  formula: FormulaDetail,
  npc: NpcDetail,
  location: LocationDetail,
  event: LocationDetail,
  treasure_chest: TreasureDetail,
  treasure_map: TreasureDetail,
  museum_display: MuseumDetail,
  museum_info: MuseumDetail,
  excavation_site: ExcavationSiteDetail,
  excavation_level: ExcavationSiteDetail,
  geode: GeodeDetail,
  modifier: ModifierDetail,
  trinket: TrinketDetail,
  merchant_item: MerchantItemDetail,
}

/**
 * Render the details of an item.
 */
export function ItemDetail({ item }: { item: Item }) {
  const Detail = DETAILS[item.type] ?? FallbackDetail
  return <Detail item={item} />
}

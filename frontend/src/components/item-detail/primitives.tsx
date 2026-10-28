import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

/**
 * A stat modifier as stored on an item.
 *
 * The shape is shared by every item type that grants stats, so the details
 * of an equipment piece, a potion and a relic read the same way.
 */
export interface StatModifier {
  stat: string
  amount: number
  amount_max?: number
  unit?: "flat" | "percent" | "multiplier"
  duration_min?: number
  stage?: number
  condition?: string
}

function formatAmount(modifier: StatModifier): string {
  const { amount, amount_max: max, unit } = modifier

  const value = (n: number) => {
    const rounded = Math.round(n * 100) / 100
    if (unit === "percent") return `${rounded}%`
    if (unit === "multiplier") return `${rounded}x`
    return `${rounded}`
  }

  if (max != null && max !== amount) {
    return `${value(amount)} – ${value(max)}`
  }
  return value(amount)
}

/**
 * Render the stat modifiers of an item.
 */
export function StatList({
  modifiers,
  className,
}: {
  modifiers?: StatModifier[] | null
  className?: string
}) {
  if (!modifiers || modifiers.length === 0) return null

  return (
    <ul className={cn("space-y-1", className)}>
      {modifiers.map((modifier, index) => (
        <li
          key={`${modifier.stat}-${modifier.amount}-${index}`}
          className="flex items-baseline justify-between gap-3 text-sm"
        >
          <span className="text-muted-foreground">
            {modifier.stat}
            {modifier.condition ? (
              <span className="text-xs"> ({modifier.condition})</span>
            ) : null}
            {modifier.stage ? (
              <span className="text-xs"> (stage {modifier.stage})</span>
            ) : null}
          </span>
          <span className="font-medium tabular-nums">
            {formatAmount(modifier)}
            {modifier.duration_min != null ? (
              <span className="ml-1 text-xs font-normal text-muted-foreground">
                {modifier.duration_min} min
              </span>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  )
}

/**
 * A labelled value in a detail panel.
 */
export function Field({
  label,
  children,
  className,
}: {
  label: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn("grid grid-cols-[9rem_1fr] gap-3 text-sm", className)}>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words font-medium">{children}</dd>
    </div>
  )
}

/**
 * A block of text in a detail panel, keeping its line breaks.
 */
export function TextBlock({ children }: { children: ReactNode }) {
  return <div className="whitespace-pre-line leading-relaxed">{children}</div>
}

/**
 * The heading of a group of fields.
 */
export function Section({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      {children}
    </section>
  )
}

/**
 * A list of values, e.g. the steps of a quest.
 */
export function BulletList({
  items,
  className,
}: {
  items?: string[] | null
  className?: string
}) {
  if (!items || items.length === 0) return null

  return (
    <ul className={cn("list-disc space-y-1 pl-5 text-sm", className)}>
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  )
}

/**
 * The picture of an item, with a placeholder when there is none.
 */
export function ItemImage({
  src,
  alt,
  className,
}: {
  src?: string | null
  alt: string
  className?: string
}) {
  if (!src) {
    return (
      <div
        className={cn(
          "flex h-32 w-32 items-center justify-center rounded-lg border border-dashed text-xs text-muted-foreground",
          className,
        )}
      >
        No image
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      className={cn("h-32 w-32 rounded-lg border bg-white/80 object-contain", className)}
    />
  )
}

/**
 * Format a timestamp for display.
 */
export function formatTimestamp(value?: string | null): string | null {
  if (!value) return null

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value

  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

/**
 * Format a currency amount the way the game writes it.
 */
export function formatCurrency(value?: number | null): string | null {
  if (value == null) return null
  return `$${value.toLocaleString("en-US")}`
}

/**
 * Format a stat amount for display.
 */
export function formatNumber(value?: number | null): string | null {
  if (value == null) return null
  return value.toLocaleString("en-US")
}

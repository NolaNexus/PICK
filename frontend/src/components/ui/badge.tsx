import * as React from 'react'
import { cn } from '@/lib/utils'
import { rarityBadgeClasses, type Rarity } from '@/lib/theme'

export type BadgeVariant =
  | 'default'
  | 'secondary'
  | 'destructive'
  | 'outline'
  | `rarity-${Rarity}`

const rarityVariants: Record<string, string> = {
  'rarity-common': rarityBadgeClasses.common,
  'rarity-uncommon': rarityBadgeClasses.uncommon,
  'rarity-rare': rarityBadgeClasses.rare,
  'rarity-epic': rarityBadgeClasses.epic,
  'rarity-legendary': rarityBadgeClasses.legendary,
  'rarity-mythical': rarityBadgeClasses.mythical,
  'rarity-exotic': rarityBadgeClasses.exotic,
}

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: BadgeVariant }) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variant === 'default' && 'bg-primary text-primary-foreground',
        variant === 'secondary' && 'bg-secondary text-secondary-foreground',
        variant === 'destructive' && 'bg-destructive text-destructive-foreground',
        variant === 'outline' && 'border-input text-foreground',
        variant && rarityVariants[variant],
        className
      )}
      {...props}
    />
  )
}

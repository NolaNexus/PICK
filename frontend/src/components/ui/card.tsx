import * as React from 'react'
import { cn } from '@/lib/utils'
import { rarityBorderClasses, type Rarity } from '@/lib/theme'

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-xl border bg-card text-card-foreground shadow', className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6 pt-0', className)} {...props} />
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex items-center p-6 pt-0', className)} {...props} />
}

// Prospecting! specific card variants
export function MineralCard({
  className,
  rarity,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { rarity?: Rarity }) {
  const rarityClass = rarity ? rarityBorderClasses[rarity] : ''

  return (
    <Card
      className={cn(
        'relative overflow-hidden transition-all hover:shadow-md',
        rarityClass,
        className
      )}
      {...props}
    >
      {children}
    </Card>
  )
}

export function EquipmentCard({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <Card
      className={cn(
        'border-2 border-earth bg-gradient-to-br from-earth/10 to-transparent',
        className
      )}
      {...props}
    >
      {children}
    </Card>
  )
}

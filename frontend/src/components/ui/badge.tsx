import * as React from 'react'
import { cn } from '@/lib/utils'

export function Badge({ className, variant, ...props }: React.HTMLAttributes<HTMLDivElement> & { variant?: 'default' | 'secondary' | 'destructive' | 'outline' }) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variant === 'default' && 'bg-primary text-primary-foreground',
        variant === 'secondary' && 'bg-secondary text-secondary-foreground',
        variant === 'destructive' && 'bg-destructive text-destructive-foreground',
        variant === 'outline' && 'border-input',
        className
      )}
      {...props}
    />
  )
}

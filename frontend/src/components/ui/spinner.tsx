import * as React from 'react'
import { cn } from '@/lib/utils'

export function Spinner({ className }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('h-6 w-6 animate-spin rounded-full border-2 border-current', className)}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  )
}

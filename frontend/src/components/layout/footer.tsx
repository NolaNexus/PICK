import { cn } from '@/lib/utils'

export function Footer({ className }: React.HTMLAttributes<HTMLDivElement> = {}) {
  return (
    <footer className={cn('border-t py-8 mt-auto', className)}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col items-center gap-2 text-sm text-muted-foreground">
        <p>PICK - Prospecting Information & Community Kit</p>
        <p>Data sourced from the community wiki.</p>
      </div>
    </footer>
  )
}

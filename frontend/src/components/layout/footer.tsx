import { cn } from '@/lib/utils'
import { ProspectingIcons } from '@/assets/icons/prospecting'

const { Gem, Pan, Anchor } = ProspectingIcons

export function Footer({ className }: React.HTMLAttributes<HTMLDivElement> = {}) {
  return (
    <footer className={cn('border-t py-8 mt-auto relative', className)}>
      {/* River wave divider */}
      <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-gold-500 via-water to-gold-500 rounded-t-full" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col items-center gap-2 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <Gem className="h-4 w-4 text-gold-500" />
          <Pan className="h-4 w-4 text-water" />
          <Anchor className="h-4 w-4 text-earth" />
        </div>
        <p>PICK - Prospecting Information & Community Kit</p>
        <p>Data sourced from the community wiki.</p>
      </div>
    </footer>
  )
}

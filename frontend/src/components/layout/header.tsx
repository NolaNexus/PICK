import { Link, NavLink } from 'react-router-dom'
import { Menu, LayoutList, Calculator, Newspaper, Activity, Search } from 'lucide-react'
import { ProspectingIcons } from '@/assets/icons/prospecting'
import { cn } from '@/lib/utils'

const { Shovel } = ProspectingIcons

const navItems = [
  { href: '/', label: 'Items', icon: LayoutList },
  { href: '/calculators', label: 'Calculators', icon: Calculator },
  { href: '/formulas', label: 'Formulas', icon: Shovel },
  { href: '/news', label: 'News', icon: Newspaper },
  { href: '/search', label: 'Search', icon: Search },
  { href: '/meta', label: 'Status', icon: Activity },
]

export function Header({ className }: React.HTMLAttributes<HTMLDivElement> = {}) {
  return (
    <div className={cn('sticky top-0 z-40 border-b bg-background/95 backdrop-blur', className)}>
      <div className="flex items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <Shovel className="h-6 w-6 text-gold-500" />
          <span className="font-bold text-lg tracking-tight text-gold-600">PICK</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.href}
                to={item.href}
                end={item.href === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'text-gold-600 underline decoration-gold-500 decoration-2 underline-offset-4'
                      : 'text-foreground/80 hover:text-gold-600'
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
        <div className="flex items-center gap-3">
          <button className="md:hidden" aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

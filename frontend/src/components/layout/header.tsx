import { Link } from 'react-router-dom'
import { Menu, Coffee, LayoutList, Calculator, Newspaper, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/', label: 'Items', icon: LayoutList },
  { href: '/calculators', label: 'Calculators', icon: Calculator },
  { href: '/formulas', label: 'Formulas', icon: HelpCircle },
  { href: '/news', label: 'News', icon: Newspaper },
  { href: '/meta', label: 'Status', icon: Coffee },
]

export function Header({ className }: React.HTMLAttributes<HTMLDivElement> = {}) {
  return (
    <div className={cn('sticky top-0 z-40 border-b', className)}>
      <div className="flex items-center justify-between px-4 py-3 bg-background border-b">
        <Link to="/" className="flex items-center gap-2">
          <Coffee className="h-6 w-6" />
          <span className="font-bold text-lg tracking-tight">PICK</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                to={item.href}
                className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
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

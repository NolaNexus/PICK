import { useState } from "react"
import { Link, NavLink } from "react-router-dom"
import { Menu, Shovel, LayoutList, Calculator, Activity, Search, X } from "lucide-react"
import { ProspectingIcons } from "@/assets/icons/prospecting"
import { cn } from "@/lib/utils"

const { Gem } = ProspectingIcons

const navItems = [
  { href: "/", label: "Home", icon: Gem, end: true },
  { href: "/items", label: "Items", icon: LayoutList },
  { href: "/minerals", label: "Minerals", icon: Shovel },
  { href: "/world", label: "World", icon: LayoutList },
  { href: "/calculators", label: "Calculators", icon: Calculator },
  { href: "/search", label: "Search", icon: Search },
  { href: "/meta", label: "Status", icon: Activity },
]

export function Header({ className }: React.HTMLAttributes<HTMLDivElement> = {}) {
  const [open, setOpen] = useState(false)

  return (
    <div className={cn("sticky top-0 z-40 border-b bg-background/95 backdrop-blur", className)}>
      <div className="flex items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <Shovel className="h-6 w-6 text-gold-500" />
          <span className="font-bold text-lg tracking-tight text-gold-600">PICK</span>
        </Link>

        <nav className="hidden md:flex items-center gap-5">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.href}
                to={item.href}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "text-gold-600 underline decoration-gold-500 decoration-2 underline-offset-4"
                      : "text-foreground/80 hover:text-gold-600",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        <button
          type="button"
          className="md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <nav className="border-t px-4 py-2 md:hidden">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.href}>
                  <NavLink
                    to={item.href}
                    end={item.end}
                    onClick={() => setOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
                        isActive
                          ? "bg-gold-500/15 text-gold-600"
                          : "text-foreground/80 hover:bg-muted",
                      )
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </nav>
      )}
    </div>
  )
}

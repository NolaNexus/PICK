// Prospecting! Theme Utilities
// Helper functions for the Prospecting! themed UI
//
// NOTE: every class string below must be a static literal. Tailwind only sees
// class names that appear verbatim in the source, so values assembled at
// runtime (e.g. `border-[${color}]`) are never emitted in the build. Dynamic
// rarity colors are therefore applied with inline styles instead.

export const rarityColors = {
  common: 'hsl(var(--rarity-common))',
  uncommon: 'hsl(var(--rarity-uncommon))',
  rare: 'hsl(var(--rarity-rare))',
  epic: 'hsl(var(--rarity-epic))',
  legendary: 'hsl(var(--rarity-legendary))',
  mythical: 'hsl(var(--rarity-mythical))',
  exotic: 'hsl(var(--rarity-exotic))',
}

// Static class maps (one literal per rarity) so Tailwind can emit them.
export const rarityBadgeClasses = {
  common: 'bg-rarity-common text-white',
  uncommon: 'bg-rarity-uncommon text-white',
  rare: 'bg-rarity-rare text-white',
  epic: 'bg-rarity-epic text-white',
  legendary: 'bg-rarity-legendary text-white',
  mythical: 'bg-rarity-mythical text-white',
  exotic: 'bg-rarity-exotic text-white',
}

export const rarityBorderClasses = {
  common: 'border-l-4 border-rarity-common',
  uncommon: 'border-l-4 border-rarity-uncommon',
  rare: 'border-l-4 border-rarity-rare',
  epic: 'border-l-4 border-rarity-epic',
  legendary: 'border-l-4 border-rarity-legendary',
  mythical: 'border-l-4 border-rarity-mythical',
  exotic: 'border-l-4 border-rarity-exotic',
}

export const rarityTextClasses = {
  common: 'text-rarity-common',
  uncommon: 'text-rarity-uncommon',
  rare: 'text-rarity-rare',
  epic: 'text-rarity-epic',
  legendary: 'text-rarity-legendary',
  mythical: 'text-rarity-mythical',
  exotic: 'text-rarity-exotic',
}

export const themeClasses = {
  gold: 'bg-gold-500 text-neutral-900',
  gem: 'bg-water text-white',
  earth: 'bg-earth text-earth-foreground',
  water: 'bg-water text-white',
  cave: 'bg-cave text-cave-foreground',
}

export const animationClasses = {
  panShake: 'animate-pan-shake',
  gemPulse: 'animate-gem-pulse',
  goldShimmer: 'animate-gold-shimmer',
  riverFlow: 'animate-river-flow',
}

export const hoverEffects = {
  rarity: {
    epic: 'hover:brightness-110 hover:shadow-[0_0_20px_rgba(156,39,176,0.3)]',
    legendary: 'hover:brightness-110 hover:shadow-[0_0_20px_rgba(255,152,0,0.3)]',
    mythical: 'hover:brightness-110 hover:shadow-[0_0_20px_rgba(244,67,54,0.3)]',
    exotic: 'hover:brightness-110 hover:shadow-[0_0_20px_rgba(233,30,99,0.3)]',
  },
  gold: 'hover:bg-gold-600 hover:shadow-md',
  gem: 'hover:bg-water/90 hover:shadow-md',
  earth: 'hover:bg-earth/90 hover:shadow-md',
  water: 'hover:bg-water/90 hover:shadow-md',
}

export const cardVariants = {
  mineral: 'border-2 border-earth bg-gradient-to-br from-earth/5 to-transparent',
  equipment: 'border-2 border-earth bg-gradient-to-br from-earth/10 to-transparent',
  default: 'border bg-card text-card-foreground shadow',
}

export const badgeVariants = {
  rarity: 'text-white font-semibold',
  default: 'border border-input',
}

export const buttonVariants = {
  gold: 'bg-gold-500 text-neutral-900 hover:bg-gold-600 hover:shadow-md',
  gem: 'bg-water text-white hover:bg-water/90 hover:shadow-md',
  earth: 'bg-earth text-earth-foreground hover:bg-earth/90 hover:shadow-md',
  default: 'bg-primary text-primary-foreground hover:bg-primary/90',
}

// CSS Custom Properties for dynamic theming
export const cssVariables = {
  rarity: {
    common: '--rarity-common',
    uncommon: '--rarity-uncommon',
    rare: '--rarity-rare',
    epic: '--rarity-epic',
    legendary: '--rarity-legendary',
    mythical: '--rarity-mythical',
    exotic: '--rarity-exotic',
  },
  theme: {
    gold: '--primary',
    gem: '--water',
    earth: '--earth',
    water: '--water',
    cave: '--cave',
  },
  animation: {
    panShake: '--pan-shake',
    gemPulse: '--gem-pulse',
    goldShimmer: '--gold-shimmer',
    riverFlow: '--river-flow',
  },
}

export type Rarity = keyof typeof rarityColors
export type ThemeVariant = keyof typeof themeClasses
export type AnimationVariant = keyof typeof animationClasses
export type BadgeVariant = keyof typeof badgeVariants
export type ButtonVariant = keyof typeof buttonVariants
export type CardVariant = keyof typeof cardVariants

# Prospecting! Web Theme Design Plan

## Overview
Create a cohesive visual theme for the PICK frontend inspired by the Roblox game **Prospecting!** — a gold-panning/mining simulator. The theme should evoke the game's core activities: panning for gold in rivers, mining in caves, discovering gems/minerals, and upgrading equipment.

## Game Visual Identity Analysis

### Core Color Palette (from game/wiki)
| Category | Colors | Usage |
|----------|--------|-------|
| **Gold/Wealth** | `#FFD700` (gold), `#FFA500` (orange-gold), `#FFEB3B` (bright yellow) | Primary actions, highlights, currency, rarity accents |
| **Gems/Minerals** | `#00BFFF` (deep sky blue), `#9B59B6` (amethyst), `#2ECC71` (emerald), `#E74C3C` (ruby), `#FF6B35` (orange), `#FF1493` (deep pink) | Rarity badges, mineral cards, accent colors |
| **Earth/Mining** | `#8B7355` (beige/brown), `#A0522D` (sienna), `#5D4E37` (dark earth), `#C19A6B` (sand) | Backgrounds, cards, borders, secondary elements |
| **Water/Rivers** | `#1E90FF` (dodger blue), `#00CED1` (dark turquoise), `#4682B4` (steel blue) | Navigation, links, water-themed sections |
| **Cave/Dark** | `#1A1A2E` (deep navy), `#16213E` (dark blue), `#0F0F1A` (near black) | Dark mode backgrounds, headers, footers |
| **UI Neutrals** | `#F5F5F0` (warm white), `#E8E4D9` (warm gray), `#8B8680` (muted) | Light mode backgrounds, text, dividers |

### Rarity Tier Colors (direct from game)
| Tier | Color | Hex |
|------|-------|-----|
| Common | Gray | `#9E9E9E` |
| Uncommon | Green | `#4CAF50` |
| Rare | Blue | `#2196F3` |
| Epic | Purple | `#9C27B0` |
| Legendary | Orange | `#FF9800` |
| Mythical | Red | `#F44336` |
| Exotic | Pink/Magenta | `#E91E63` |

### Visual Motifs
- **Pan/shovel silhouettes** as decorative elements
- **Gem/mineral crystal shapes** for badges/icons
- **River wave patterns** for section dividers
- **Cave/rock textures** for card backgrounds (subtle)
- **Gold nugget sparkle** for loading states/highlights

---

## Implementation Plan

### 1. Tailwind Config Overhaul (`frontend/tailwind.config.js`)
Extend theme with Prospecting! color palette and design tokens.

**New color families:**
- `prospecting.gold` — 50-950 scale
- `prospecting.gem` — sub-colors per rarity (common, uncommon, rare, epic, legendary, mythical, exotic)
- `prospecting.earth` — warm browns/beiges
- `prospecting.water` — river blues
- `prospecting.cave` — dark mode neutrals

**Custom utilities:**
- `bg-rarity-{tier}` for badge backgrounds
- `text-rarity-{tier}` for text colors
- `border-rarity-{tier}` for borders
- `animate-pan-shake` for loading spinners
- `animate-gem-glow` for hover effects

### 2. CSS Variables Update (`frontend/src/index.css`)
Replace generic shadcn variables with semantic Prospecting! tokens.

**Light mode:**
- `--background`: warm off-white (`prospecting.earth.50`)
- `--foreground`: dark earth (`prospecting.earth.900`)
- `--primary`: gold (`prospecting.gold.600`)
- `--primary-foreground`: dark earth
- `--card`: white with subtle earth tint
- `--border`: warm gray (`prospecting.earth.200`)
- `--ring`: gold (`prospecting.gold.500`)

**Dark mode:**
- `--background`: cave dark (`prospecting.cave.950`)
- `--foreground`: warm white (`prospecting.earth.50`)
- `--primary`: bright gold (`prospecting.gold.400`)
- `--card`: cave (`prospecting.cave.900`)
- `--border`: muted cave (`prospecting.cave.700`)
- `--ring`: gold (`prospecting.gold.400`)

**Rarity CSS variables (both modes):**
- `--rarity-common`, `--rarity-uncommon`, ..., `--rarity-exotic`

### 3. Component Updates

#### Badge Component (`frontend/src/components/ui/badge.tsx`)
- Add `rarity` variant prop: `common | uncommon | rare | epic | legendary | mythical | exotic`
- Map to `bg-rarity-{tier}` / `text-rarity-{tier}` / `border-rarity-{tier}`
- Add subtle glow on hover for epic+

#### Button Component (`frontend/src/components/ui/button.tsx`)
- Add `gold` variant (primary actions): gold bg, dark text, hover darker gold
- Add `gem` variant (secondary): water blue bg, white text
- Add `earth` variant (tertiary): earth tone bg, dark text
- Keep existing variants for compatibility

#### Card Component (`frontend/src/components/ui/card.tsx`)
- Add `mineral` variant: subtle gem-colored border-left accent based on rarity
- Add `equipment` variant: earth-textured background (CSS pattern)
- Add `pan-shake` hover animation on interactive cards

#### Header (`frontend/src/components/layout/header.tsx`)
- Replace coffee icon with custom pan/shovel SVG
- Add gold gradient text for "PICK" logo
- Navigation: gold underline on active, gem glow on hover

#### Footer (`frontend/src/components/layout/footer.tsx`)
- River wave divider at top
- Community links with gem icons

### 4. Page-Specific Enhancements

#### Item Browser (`ItemBrowserPage.tsx`)
- Mineral cards: rarity-colored left border + hover gem glow
- Type filter buttons: earth variant with gold active state
- Table rows: subtle pan-shake on hover

#### Calculators Page
- Input fields: water-blue focus ring
- Result cards: gold accent border
- Sliders: gold thumb, water track

#### Formulas Page
- Code blocks: cave dark background, gold syntax highlighting
- Formula cards: rarity-coded by complexity

#### News Page
- News cards: river wave bottom border
- Tags: rarity badges
- Featured: gold gradient background

#### Meta/Status Page
- Status badges: rarity system (operational = mythical, degraded = rare, etc.)
- Charts: gold/water color scheme

### 5. Icon System
Create `frontend/src/assets/icons/prospecting.ts` with:
- `PanIcon` — gold panning pan
- `ShovelIcon` — mining shovel
- `GemIcon` — faceted gem (configurable color)
- `GoldNuggetIcon` — gold nugget
- `SluiceIcon` — sluice box
- `RelicIcon` — ancient relic
- `MineralIcon` — raw mineral chunk

### 6. Animation & Micro-interactions
- **Pan shake**: `@keyframes pan-shake` — subtle rotation for loading/buttons
- **Gem pulse**: `@keyframes gem-pulse` — glow animation for rare+ items
- **Gold shimmer**: `@keyframes gold-shimmer` — sweep across gold elements
- **River flow**: `@keyframes river-flow` — background pattern for hero sections

### 7. Responsive & Accessibility
- All colors meet WCAG AA contrast (test both light/dark)
- Reduced motion: disable animations via `prefers-reduced-motion`
- Focus visible: gold ring (light) / bright gold ring (dark)
- Touch targets: min 44px

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/tailwind.config.js` | Major rewrite | Full Prospecting! theme extension |
| `frontend/src/index.css` | Major rewrite | Semantic CSS variables for light/dark |
| `frontend/src/components/ui/badge.tsx` | Modify | Add rarity variants |
| `frontend/src/components/ui/button.tsx` | Modify | Add gold/gem/earth variants |
| `frontend/src/components/ui/card.tsx` | Modify | Add mineral/equipment variants |
| `frontend/src/components/layout/header.tsx` | Modify | Custom logo, gold accents |
| `frontend/src/components/layout/footer.tsx` | Modify | Wave divider, gem icons |
| `frontend/src/assets/icons/prospecting.ts` | New | Custom icon components |
| `frontend/src/lib/theme.ts` | New | Theme utilities, rarity helpers |
| `frontend/src/pages/*.tsx` | Minor | Apply new variants where appropriate |

---

## Validation Checklist

- [ ] Light mode: all text readable, gold primary visible on earth backgrounds
- [ ] Dark mode: gold pops on cave backgrounds, water blues visible
- [ ] Rarity badges: distinct at small sizes, colorblind-safe (add patterns/icons)
- [ ] Buttons: clear hierarchy (gold > gem > earth > ghost)
- [ ] Cards: subtle depth, rarity accents don't overwhelm
- [ ] Animations: smooth, respect reduced motion
- [ ] Build passes: `npm run build` in frontend
- [ ] Lint passes: `npm run lint` in frontend

---

## Out of Scope
- Full redesign of page layouts (keep existing structure)
- New page components
- Backend changes
- Mobile app / PWA features
- Internationalization

---

## Next Steps
1. Implement tailwind.config.js with full color palette
2. Update index.css with semantic variables
3. Update badge, button, card components
4. Update header/footer
5. Create icon system
6. Apply to pages incrementally
7. Test both light/dark modes across all pages
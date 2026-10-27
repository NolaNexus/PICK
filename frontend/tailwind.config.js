/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Prospecting! Gold Colors
        prospecting: {
          gold: {
            50: '#fffbeb',
            100: '#fef3c7',
            200: '#fde68a',
            300: '#fcd34d',
            400: '#fbbf24',
            500: '#f59e0b',
            600: '#d97706',
            700: '#b45309',
            800: '#92400e',
            900: '#78350f',
            950: '#451a03',
          },
          // Gem/Mineral colors by rarity
          common: {
            50: '#f9fafb',
            100: '#f3f4f6',
            200: '#e5e7eb',
            300: '#d1d5db',
            400: '#9ca3af',
            500: '#9e9e9e', // grayish
            600: '#757575',
            700: '#616161',
            800: '#424242',
            900: '#212121',
          },
          uncommon: {
            50: '#f0fdf4',
            100: '#dcfce7',
            200: '#bbf7d0',
            300: '#86efac',
            400: '#4ade80',
            500: '#4caf50', // green
            600: '#16a34a',
            700: '#15803d',
            800: '#166534',
            900: '#14532d',
          },
          rare: {
            50: '#eff6ff',
            100: '#dbeafe',
            200: '#bfdbfe',
            300: '#93c5fd',
            400: '#60a5fa',
            500: '#2196f3', // blue
            600: '#2563eb',
            700: '#1d4ed8',
            800: '#1e40af',
            900: '#1e3a8a',
          },
          epic: {
            50: '#faf5ff',
            100: '#f3e8ff',
            200: '#e9d5ff',
            300: '#d8b4fe',
            400: '#c084fc',
            500: '#9c27b0', // purple
            600: '#9333ea',
            700: '#7e22ce',
            800: '#6b21a8',
            900: '#581c87',
          },
          legendary: {
            50: '#fff7ed',
            100: '#ffedd5',
            200: '#fed7aa',
            300: '#fdba74',
            400: '#fb923c',
            500: '#ff9800', // orange
            600: '#f97316',
            700: '#ea580c',
            800: '#c2410c',
            900: '#9a3412',
          },
          mythical: {
            50: '#fef2f2',
            100: '#fee2e2',
            200: '#fecaca',
            300: '#fca5a5',
            400: '#f87171',
            500: '#f44336', // red
            600: '#ef4444',
            700: '#dc2626',
            800: '#b91c1c',
            900: '#991b1b',
          },
          exotic: {
            50: '#fce8f3',
            100: '#fce4ef',
            200: '#fbcfe8',
            300: '#f9a8d4',
            400: '#f472b6',
            500: '#e91e63', // pink magenta
            600: '#db2777',
            700: '#be185d',
            800: '#9d174d',
            900: '#831843',
          },
          // Earth/Mining colors
          earth: {
            50: '#f5f4f0',
            100: '#e8e4d9',
            200: '#d9d4c0',
            300: '#c4b8a1',
            400: '#a69c7f',
            500: '#8b8680',
            600: '#716e69',
            700: '#5a5955',
            800: '#46443f',
            900: '#32312b',
          },
          // Water/River colors
          water: {
            50: '#eff6ff',
            100: '#dbeafe',
            200: '#bfdbfe',
            300: '#93c5fd',
            400: '#60a5fa',
            500: '#1e90ff', // dodger blue
            600: '#2563eb',
            700: '#1d4ed8',
            800: '#1e40af',
            900: '#1e3a8a',
          },
          // Cave/Dark colors
          cave: {
            50: '#f8fafc',
            100: '#f1f5f9',
            200: '#e2e8f0',
            300: '#cbd5e1',
            400: '#94a3b8',
            500: '#64748b',
            600: '#475569',
            700: '#334155',
            800: '#1e293b',
            900: '#0f172a',
            950: '#020617',
          },
        },
      },
      // Custom rarity utilities
      borderRadius: {
        'prospecting': '0.5rem',
      },
      // Custom animations
      animation: {
        'pan-shake': 'pan-shake 0.5s ease-in-out infinite',
        'gem-pulse': 'gem-pulse 2s ease-in-out infinite',
        'gold-shimmer': 'gold-shimmer 3s ease-in-out infinite',
        'river-flow': 'river-flow 20s linear infinite',
      },
      keyframes: {
        'pan-shake': {
          '0%, 100%': { transform: 'rotate(-2deg)' },
          '50%': { transform: 'rotate(2deg)' },
        },
        'gem-pulse': {
          '0%, 100%': { opacity: '0.8', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        'gold-shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'river-flow': {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '100px 0' },
        },
      },
      backgroundSize: {
        'river-pattern': '100px 20px',
      },
      backgroundImage: {
        'river-pattern': 'linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
      },
    },
  },
  plugins: [],
}

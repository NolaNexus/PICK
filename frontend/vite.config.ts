import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: '/PICK/',
  plugins: [react()],
  // Vite 8 resolves the tsconfig `paths` aliases natively. The `@/` alias is
  // used all over `src/`.
  resolve: {
    tsconfigPaths: true,
  },
})

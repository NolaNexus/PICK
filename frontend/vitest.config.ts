import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

/**
 * The test configuration.
 *
 * The app's config lives in `vite.config.ts`; this one adds the test runner to
 * it. Vite resolves the `@/` alias natively from `tsconfig.app.json`, so the
 * `vite-tsconfig-paths` plugin that the app build still uses is not needed
 * here — and using it would print a deprecation notice.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    tsconfigPaths: true,
  },
  test: {
    // The modules under test are pure: the calculators, the museum maths and
    // the taxonomy read no browser API. The one module that does is
    // `lib/idb.ts`, which uses IndexedDB, and it is not under test. A test
    // that needs the DOM can opt in with a
    // `// @vitest-environment jsdom` docblock rather than the whole suite
    // paying for it.
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
    },
  },
})

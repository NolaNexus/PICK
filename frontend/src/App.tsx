import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { Toaster } from '@/components/ui/toast'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Header } from '@/components/layout/header'
import { Footer } from '@/components/layout/footer'
import { container } from '@/components/layout/container'
import { queryClient } from '@/lib/queryClient'

import HomePage from '@/pages/HomePage'
import ItemsPage from '@/pages/ItemsPage'
import MineralsPage from '@/pages/MineralsPage'
import WorldPage from '@/pages/WorldPage'
import CalculatorsPage from '@/pages/CalculatorsPage'
import NewsPage from '@/pages/NewsPage'
import MetaPage from '@/pages/MetaPage'
import SearchPage from '@/pages/SearchPage'

const REDIRECT_KEY = 'pick:redirect'

/**
 * Restores the route that GitHub Pages' 404 fallback stashed before it
 * redirected to the app entry point.
 */
function RedirectHandler() {
  const navigate = useNavigate()

  useEffect(() => {
    let target: string | null = null
    try {
      target = window.sessionStorage.getItem(REDIRECT_KEY)
      if (target) window.sessionStorage.removeItem(REDIRECT_KEY)
    } catch {
      target = null
    }
    if (target) {
      navigate(target, { replace: true })
    }
  }, [navigate])

  return null
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/PICK">
        <div className="min-h-screen flex flex-col">
          <Toaster />
          <Header />
          <ErrorBoundary>
            <main className={`flex-1 ${container.base} py-6`}>
              <RedirectHandler />
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/items" element={<ItemsPage />} />
                <Route path="/minerals" element={<MineralsPage />} />
                <Route path="/world" element={<WorldPage />} />
                <Route path="/calculators" element={<CalculatorsPage />} />
                <Route path="/news" element={<NewsPage />} />
                <Route path="/meta" element={<MetaPage />} />
                <Route path="/search" element={<SearchPage />} />
              </Routes>
            </main>
          </ErrorBoundary>
          <Footer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App

import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/toast'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { queryClient } from '@/lib/queryClient'

import ItemBrowserPage from '@/pages/ItemBrowserPage'
import CalculatorsPage from '@/pages/CalculatorsPage'
import FormulasPage from '@/pages/FormulasPage'
import NewsPage from '@/pages/NewsPage'
import MetaPage from '@/pages/MetaPage'
import SearchPage from '@/pages/SearchPage'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/PICK---Prospecting-Information---Community-Kit">
        <div className="min-h-screen flex flex-col">
          <Toaster />
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<ItemBrowserPage />} />
              <Route path="/calculators" element={<CalculatorsPage />} />
              <Route path="/formulas" element={<FormulasPage />} />
              <Route path="/news" element={<NewsPage />} />
              <Route path="/meta" element={<MetaPage />} />
              <Route path="/search" element={<SearchPage />} />
            </Routes>
          </ErrorBoundary>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App

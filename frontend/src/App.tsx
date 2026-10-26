import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toast'
import { queryClient } from '@/lib/queryClient'

import ItemBrowserPage from '@/pages/ItemBrowserPage'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen flex flex-col">
        <Toaster />
        <ItemBrowserPage />
      </div>
    </QueryClientProvider>
  )
}

export default App

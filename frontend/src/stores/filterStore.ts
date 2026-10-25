import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface FilterState {
  itemType: string | null
  searchQuery: string
  setItemType: (type: string | null) => void
  setSearchQuery: (q: string) => void
}

export const useFilterStore = create<FilterState>()(
  persist(
    (set) => ({
      itemType: null,
      searchQuery: '',
      setItemType: (type) => set({ itemType: type }),
      setSearchQuery: (q) => set({ searchQuery: q }),
    }),
    { name: 'pick-filter-storage' }
  )
)

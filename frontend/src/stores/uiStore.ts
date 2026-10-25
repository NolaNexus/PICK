import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  activeCalculatorTab: string
  setActiveCalculatorTab: (tab: string) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  activeCalculatorTab: 'ev',
  setActiveCalculatorTab: (tab) => set({ activeCalculatorTab: tab }),
}))

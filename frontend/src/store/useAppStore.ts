import { create } from 'zustand'
import type { Usuario, Conversa } from '@/types'

interface AppStore {
  // Auth
  usuario: Usuario | null
  setUsuario: (u: Usuario | null) => void

  // Conversa ativa
  conversaAtiva: Conversa | null
  setConversaAtiva: (c: Conversa | null) => void

  // Sidebar
  sidebarAberta: boolean
  setSidebarAberta: (v: boolean) => void
  toggleSidebar: () => void

  // Streaming em progresso
  streamingAtivo: boolean
  setStreamingAtivo: (v: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  usuario: null,
  setUsuario: (usuario) => set({ usuario }),

  conversaAtiva: null,
  setConversaAtiva: (conversaAtiva) => set({ conversaAtiva }),

  sidebarAberta: true,
  setSidebarAberta: (sidebarAberta) => set({ sidebarAberta }),
  toggleSidebar: () => set((s) => ({ sidebarAberta: !s.sidebarAberta })),

  streamingAtivo: false,
  setStreamingAtivo: (streamingAtivo) => set({ streamingAtivo }),
}))

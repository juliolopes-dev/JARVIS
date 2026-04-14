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

  // Notificacoes nao lidas
  naoLidas: number
  setNaoLidas: (n: number) => void
}

export const useAppStore = create<AppStore>()((set) => ({
  usuario: null,
  setUsuario: (usuario) => set({ usuario }),

  conversaAtiva: null,
  setConversaAtiva: (conversaAtiva) => set({ conversaAtiva }),

  sidebarAberta: typeof window !== 'undefined' ? window.innerWidth >= 768 : true,
  setSidebarAberta: (sidebarAberta) => set({ sidebarAberta }),
  toggleSidebar: () => set((s) => ({ sidebarAberta: !s.sidebarAberta })),

  streamingAtivo: false,
  setStreamingAtivo: (streamingAtivo) => set({ streamingAtivo }),

  naoLidas: 0,
  setNaoLidas: (naoLidas) => set({ naoLidas }),
}))

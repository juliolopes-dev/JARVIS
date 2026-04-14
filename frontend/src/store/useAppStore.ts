import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Usuario, Conversa } from '@/types'

export type Tema = 'arc' | 'ironman'

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

  // Tema (persistido)
  tema: Tema
  setTema: (t: Tema) => void
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
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

      tema: 'arc',
      setTema: (tema) => {
        if (typeof document !== 'undefined') {
          document.documentElement.setAttribute('data-theme', tema)
        }
        set({ tema })
      },
    }),
    {
      name: 'jarvis-store',
      partialize: (s) => ({ tema: s.tema }),
      onRehydrateStorage: () => (state) => {
        if (state && typeof document !== 'undefined') {
          document.documentElement.setAttribute('data-theme', state.tema)
        }
      },
    }
  )
)

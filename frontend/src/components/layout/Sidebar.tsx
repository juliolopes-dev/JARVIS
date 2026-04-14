import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  MessageSquare,
  Brain,
  Bell,
  BellRing,
  CheckSquare,
  Settings,
  Clock,
  Plus,
  Trash2,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  BookOpen,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAppStore } from '@/store/useAppStore'
import { chatService } from '@/services/chatService'
import { authService } from '@/services/authService'
import { api } from '@/services/api'
import { formatarDataConversa } from '@/utils/formatDate'
import type { Conversa } from '@/types'
import { toast } from 'sonner'

export function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarAberta, toggleSidebar, setSidebarAberta, conversaAtiva, setConversaAtiva, usuario, naoLidas, setNaoLidas } = useAppStore()

  function navegarEFecharMobile(path: string) {
    if (window.innerWidth < 768) setSidebarAberta(false)
    navigate(path)
  }
  const [conversas, setConversas] = useState<Conversa[]>([])
  const [carregando, setCarregando] = useState(true)
  const [criando, setCriando] = useState(false)

  useEffect(() => {
    carregarConversas()
    carregarNaoLidas()
    // Atualiza badge a cada 60s
    const intervalo = setInterval(carregarNaoLidas, 60000)
    return () => clearInterval(intervalo)
  }, [])

  async function carregarNaoLidas() {
    try {
      const { data } = await api.get<{ total: number }>('/notificacoes/historico/nao-lidas')
      setNaoLidas(data.total)
    } catch {
      // silencioso
    }
  }

  async function carregarConversas() {
    try {
      const lista = await chatService.listarConversas()
      setConversas(lista)
    } catch {
      // silencioso
    } finally {
      setCarregando(false)
    }
  }

  async function novaConversa() {
    setCriando(true)
    try {
      const conversa = await chatService.criarConversa()
      setConversas((prev) => [conversa, ...prev])
      setConversaAtiva(conversa)
      navigate(`/chat/${conversa.id}`)
    } catch {
      toast.error('Erro ao criar conversa')
    } finally {
      setCriando(false)
    }
  }

  async function arquivarConversa(e: React.MouseEvent, id: string) {
    e.stopPropagation()
    try {
      await chatService.arquivarConversa(id)
      setConversas((prev) => prev.filter((c) => c.id !== id))
      if (conversaAtiva?.id === id) {
        setConversaAtiva(null)
        navigate('/chat')
      }
    } catch {
      toast.error('Erro ao arquivar conversa')
    }
  }

  const navItems = [
    { path: '/chat', label: 'Chat', icon: MessageSquare, badge: 0 },
    { path: '/tarefas', label: 'Tarefas', icon: CheckSquare, badge: 0 },
    { path: '/lembretes', label: 'Lembretes', icon: Clock, badge: 0 },
    { path: '/notificacoes', label: 'Notificações', icon: Bell, badge: naoLidas },
    { path: '/livros', label: 'Livros', icon: BookOpen, badge: 0 },
    { path: '/memoria', label: 'Memória', icon: Brain, badge: 0 },
    { path: '/config', label: 'Configurações', icon: Settings, badge: 0 },
  ]

  return (
    <aside
      className="w-[260px] flex flex-col border-r border-surface-border bg-surface h-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 h-14 border-b border-surface-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-accent flex items-center justify-center">
            <span className="text-white text-xs font-bold">J</span>
          </div>
          <span className="text-sm font-semibold text-text-primary">Jarvis</span>
        </div>
        <button
          onClick={toggleSidebar}
          className="text-text-muted hover:text-text-primary transition-colors cursor-pointer p-1 rounded hover:bg-surface-overlay"
        >
          <PanelLeftClose size={15} />
        </button>
      </div>

      {/* Nav principal — oculta no mobile (usa BottomNav) */}
      <nav className="hidden md:block px-2 pt-3 pb-2 shrink-0">
        {navItems.map(({ path, label, icon: Icon, badge }) => {
          const ativo = location.pathname.startsWith(path)
          return (
            <button
              key={path}
              onClick={() => navegarEFecharMobile(path)}
              className={cn(
                'w-full flex items-center gap-2.5 h-8 px-3 rounded text-sm font-medium transition-colors cursor-pointer',
                ativo
                  ? 'bg-surface-overlay text-text-primary'
                  : 'text-text-secondary hover:bg-white/[0.04] hover:text-text-primary'
              )}
            >
              <Icon size={15} className="shrink-0" />
              <span className="flex-1 text-left">{label}</span>
              {badge > 0 && (
                <span className="text-2xs bg-accent text-white px-1.5 py-0.5 rounded-full font-medium tabular-nums leading-none">
                  {badge}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Divisor */}
      <div className="mx-4 border-t border-surface-border mb-2 shrink-0" />

      {/* Nova conversa */}
      <div className="px-2 mb-2 shrink-0">
        <button
          onClick={novaConversa}
          disabled={criando}
          className={cn(
            'w-full flex items-center gap-2 h-8 px-3 rounded text-xs font-medium',
            'text-text-secondary hover:text-text-primary',
            'border border-dashed border-surface-border hover:border-surface-muted',
            'transition-colors cursor-pointer disabled:opacity-50'
          )}
        >
          <Plus size={13} />
          Nova conversa
        </button>
      </div>

      {/* Lista de conversas */}
      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {carregando ? (
          <div className="px-3 py-2 text-xs text-text-faint">Carregando...</div>
        ) : conversas.length === 0 ? (
          <div className="px-3 py-2 text-xs text-text-faint">Nenhuma conversa ainda</div>
        ) : (
          conversas.map((c) => (
            <button
              key={c.id}
              onClick={() => {
                setConversaAtiva(c)
                navegarEFecharMobile(`/chat/${c.id}`)
              }}
              className={cn(
                'w-full group flex items-center justify-between gap-1 h-8 px-3 rounded text-xs',
                'transition-colors cursor-pointer',
                conversaAtiva?.id === c.id
                  ? 'bg-surface-overlay text-text-primary'
                  : 'text-text-secondary hover:bg-white/[0.04] hover:text-text-primary'
              )}
            >
              <span className="truncate text-left flex-1">
                {c.titulo || 'Nova conversa'}
              </span>
              <span className="shrink-0 text-text-faint text-2xs">
                {formatarDataConversa(c.atualizado_em)}
              </span>
              <button
                onClick={(e) => arquivarConversa(e, c.id)}
                className="shrink-0 opacity-0 group-hover:opacity-100 p-0.5 rounded hover:text-red-400 transition-all cursor-pointer"
              >
                <Trash2 size={11} />
              </button>
            </button>
          ))
        )}
      </div>

      {/* Footer — usuário */}
      <div className="shrink-0 border-t border-surface-border px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 rounded-full bg-surface-border flex items-center justify-center shrink-0">
            <span className="text-text-secondary text-2xs font-semibold">
              {usuario?.nome?.charAt(0)?.toUpperCase() ?? 'J'}
            </span>
          </div>
          <span className="text-xs text-text-secondary truncate">{usuario?.nome ?? 'Julio'}</span>
        </div>
        <button
          onClick={() => {
            authService.logout()
            navigate('/login')
          }}
          className="text-text-faint hover:text-red-400 transition-colors cursor-pointer p-1 rounded hover:bg-red-500/10"
          title="Sair"
        >
          <LogOut size={13} />
        </button>
      </div>
    </aside>
  )
}

// Botão flutuante para reabrir sidebar quando fechada — só no desktop
export function SidebarToggle() {
  const { sidebarAberta, toggleSidebar } = useAppStore()
  if (sidebarAberta) return null
  return (
    <button
      onClick={toggleSidebar}
      className="hidden md:flex fixed top-4 left-4 z-50 p-1.5 rounded border border-surface-border bg-surface-raised text-text-muted hover:text-text-primary hover:bg-surface-overlay transition-colors cursor-pointer"
    >
      <PanelLeftOpen size={15} />
    </button>
  )
}

import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Sidebar, SidebarToggle } from './Sidebar'
import { MessageSquare, Bell, Brain, CheckSquare, Settings, BookOpen } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAppStore } from '@/store/useAppStore'

// Navbar inferior — só aparece no mobile
function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()
  const { setSidebarAberta, naoLidas } = useAppStore()

  const items = [
    { path: '/chat', icon: MessageSquare, label: 'Chat', badge: 0 },
    { path: '/tarefas', icon: CheckSquare, label: 'Tarefas', badge: 0 },
    { path: '/livros', icon: BookOpen, label: 'Livros', badge: 0 },
    { path: '/notificacoes', icon: Bell, label: 'Avisos', badge: naoLidas },
    { path: '/config', icon: Settings, label: 'Config', badge: 0 },
  ]

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-surface-border flex items-center">
      {items.map(({ path, icon: Icon, label, badge }) => {
        const ativo = location.pathname.startsWith(path)
        return (
          <button
            key={path}
            onClick={() => {
              if (path === '/chat') {
                // Chat abre a sidebar direto — é onde estão as conversas
                navigate(path)
                setSidebarAberta(true)
              } else {
                setSidebarAberta(false)
                navigate(path)
              }
            }}
            className={cn(
              'flex-1 flex flex-col items-center justify-center py-2 gap-0.5 cursor-pointer transition-colors relative',
              ativo ? 'text-accent' : 'text-text-faint'
            )}
          >
            <div className="relative">
              <Icon size={20} />
              {badge > 0 && (
                <span className="absolute -top-1 -right-1.5 min-w-[14px] h-3.5 px-0.5 bg-accent text-white text-2xs font-bold rounded-full flex items-center justify-center leading-none tabular-nums">
                  {badge > 9 ? '9+' : badge}
                </span>
              )}
            </div>
            <span className="text-2xs font-medium">{label}</span>
          </button>
        )
      })}
    </nav>
  )
}

export function AppLayout() {
  const { sidebarAberta, setSidebarAberta } = useAppStore()

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* ── Desktop: sidebar ocupa espaço real no flex ── */}
      <div className={cn(
        'hidden md:flex flex-shrink-0 transition-all duration-200',
        sidebarAberta ? 'w-[260px]' : 'w-0'
      )}>
        {sidebarAberta && <Sidebar />}
      </div>

      {/* ── Mobile: sidebar como drawer fixo ── */}
      {sidebarAberta && (
        <div
          className="md:hidden fixed inset-0 z-30 bg-black/50"
          onClick={() => setSidebarAberta(false)}
        />
      )}
      <div className={cn(
        'md:hidden fixed inset-y-0 left-0 z-40 transition-transform duration-200',
        sidebarAberta ? 'translate-x-0' : '-translate-x-full'
      )}>
        <Sidebar />
      </div>

      {/* ── Botão para reabrir sidebar (desktop) ── */}
      <SidebarToggle />

      {/* ── Conteúdo principal ── */}
      <main className="flex-1 min-w-0 overflow-hidden pb-14 md:pb-0">
        <Outlet />
      </main>

      {/* ── Navbar inferior mobile ── */}
      <BottomNav />
    </div>
  )
}

import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Sidebar, SidebarToggle } from './Sidebar'
import { MessageSquare, Bell, Brain, Settings } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAppStore } from '@/store/useAppStore'

// Navbar inferior — só aparece no mobile
function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()
  const { sidebarAberta, setSidebarAberta } = useAppStore()

  const items = [
    { path: '/chat', icon: MessageSquare, label: 'Chat' },
    { path: '/lembretes', icon: Bell, label: 'Lembretes' },
    { path: '/memoria', icon: Brain, label: 'Memória' },
    { path: '/config', icon: Settings, label: 'Config' },
  ]

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-surface-border flex items-center">
      {items.map(({ path, icon: Icon, label }) => {
        const ativo = location.pathname.startsWith(path)
        return (
          <button
            key={path}
            onClick={() => {
              setSidebarAberta(false)
              navigate(path)
            }}
            className={cn(
              'flex-1 flex flex-col items-center justify-center py-2 gap-0.5 cursor-pointer transition-colors',
              ativo ? 'text-accent' : 'text-text-faint'
            )}
          >
            <Icon size={20} />
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
    <div className="flex h-screen overflow-hidden">
      {/* Overlay mobile — fecha sidebar ao clicar fora */}
      {sidebarAberta && (
        <div
          className="md:hidden fixed inset-0 z-30 bg-black/50"
          onClick={() => setSidebarAberta(false)}
        />
      )}

      {/* Sidebar — drawer no mobile (fixed), normal no desktop (relative no flex) */}
      <div className={cn(
        // Mobile: fixed drawer
        'fixed inset-y-0 left-0 z-40 transition-transform duration-200',
        'md:relative md:z-auto md:translate-x-0 md:flex-shrink-0',
        sidebarAberta ? 'translate-x-0' : '-translate-x-full'
      )}>
        <Sidebar />
      </div>

      <SidebarToggle />

      {/* Conteúdo principal */}
      <main className="flex-1 min-w-0 overflow-hidden pb-14 md:pb-0">
        <Outlet />
      </main>

      {/* Navbar inferior mobile */}
      <BottomNav />
    </div>
  )
}

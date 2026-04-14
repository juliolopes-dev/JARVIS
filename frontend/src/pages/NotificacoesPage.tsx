import { useEffect, useState } from 'react'
import { Bell, CheckCheck, Sun, Clock } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/services/api'
import { cn } from '@/utils/cn'
import { useAppStore } from '@/store/useAppStore'

interface Notificacao {
  id: string
  tipo: string
  titulo: string
  corpo: string | null
  flg_lida: boolean
  dat_lida: string | null
  criado_em: string
}

function formatarData(iso: string) {
  const d = new Date(iso)
  const agora = new Date()
  const diffMs = agora.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffH = Math.floor(diffMin / 60)
  const diffD = Math.floor(diffH / 24)

  if (diffMin < 1) return 'Agora'
  if (diffMin < 60) return `${diffMin}min atrás`
  if (diffH < 24) return `${diffH}h atrás`
  if (diffD === 1) return 'Ontem'
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function TipoIcon({ tipo }: { tipo: string }) {
  if (tipo === 'briefing') return <Sun size={14} className="text-yellow-400" />
  if (tipo === 'lembrete') return <Clock size={14} className="text-accent" />
  return <Bell size={14} className="text-text-faint" />
}

export function NotificacoesPage() {
  const [notificacoes, setNotificacoes] = useState<Notificacao[]>([])
  const [carregando, setCarregando] = useState(true)
  const [expandida, setExpandida] = useState<string | null>(null)
  const [marcandoTodas, setMarcandoTodas] = useState(false)
  const { naoLidas, setNaoLidas } = useAppStore()

  useEffect(() => {
    carregar()
  }, [])

  async function carregar() {
    try {
      const { data } = await api.get<Notificacao[]>('/notificacoes/historico')
      setNotificacoes(data)
      // Atualiza badge com contagem real após carregar
      const naoLidasCount = data.filter((n) => !n.flg_lida).length
      setNaoLidas(naoLidasCount)
    } catch {
      toast.error('Erro ao carregar notificações')
    } finally {
      setCarregando(false)
    }
  }

  async function marcarLida(id: string) {
    try {
      await api.patch(`/notificacoes/historico/${id}/lida`)
      setNotificacoes((prev) =>
        prev.map((n) => (n.id === id ? { ...n, flg_lida: true } : n))
      )
      const eraLida = notificacoes.find((n) => n.id === id)?.flg_lida ?? true
      if (!eraLida) setNaoLidas(Math.max(0, naoLidas - 1))
    } catch {
      // silencioso
    }
  }

  async function marcarTodasLidas() {
    setMarcandoTodas(true)
    try {
      await api.post('/notificacoes/historico/marcar-todas-lidas')
      setNotificacoes((prev) => prev.map((n) => ({ ...n, flg_lida: true })))
      setNaoLidas(0)
      toast.success('Todas marcadas como lidas')
    } catch {
      toast.error('Erro ao marcar notificações')
    } finally {
      setMarcandoTodas(false)
    }
  }

  function toggleExpandir(id: string, flg_lida: boolean) {
    setExpandida((prev) => (prev === id ? null : id))
    if (!flg_lida) marcarLida(id)
  }

  const totalNaoLidas = notificacoes.filter((n) => !n.flg_lida).length

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 h-14 border-b border-surface-border shrink-0">
        <div className="flex items-center gap-2">
          <Bell size={15} className="text-text-muted" />
          <span className="text-sm font-semibold text-text-primary">Notificações</span>
          {totalNaoLidas > 0 && (
            <span className="text-xs bg-accent text-white px-1.5 py-0.5 rounded-full font-medium tabular-nums">
              {totalNaoLidas}
            </span>
          )}
        </div>
        {totalNaoLidas > 0 && (
          <button
            onClick={marcarTodasLidas}
            disabled={marcandoTodas}
            className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors cursor-pointer disabled:opacity-50"
          >
            <CheckCheck size={13} />
            Marcar todas lidas
          </button>
        )}
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {carregando ? (
          <p className="px-6 py-4 text-sm text-text-faint">Carregando...</p>
        ) : notificacoes.length === 0 ? (
          <div className="text-center py-16">
            <Bell size={32} className="text-text-faint mx-auto mb-3" />
            <p className="text-sm text-text-secondary">Nenhuma notificação ainda</p>
            <p className="text-xs text-text-faint mt-1">
              Lembretes e briefings aparecerão aqui
            </p>
          </div>
        ) : (
          <div className="divide-y divide-surface-border">
            {notificacoes.map((n) => (
              <div
                key={n.id}
                onClick={() => toggleExpandir(n.id, n.flg_lida)}
                className={cn(
                  'px-6 py-3 cursor-pointer transition-colors',
                  !n.flg_lida
                    ? 'bg-accent/5 hover:bg-accent/10'
                    : 'hover:bg-surface-overlay'
                )}
              >
                <div className="flex items-start gap-3">
                  {/* Ícone + indicador não lida */}
                  <div className="relative shrink-0 mt-0.5">
                    <TipoIcon tipo={n.tipo} />
                    {!n.flg_lida && (
                      <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-accent" />
                    )}
                  </div>

                  {/* Conteúdo */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className={cn(
                        'text-sm truncate',
                        n.flg_lida ? 'text-text-secondary' : 'text-text-primary font-medium'
                      )}>
                        {n.titulo}
                      </span>
                      <span className="text-2xs text-text-faint shrink-0 tabular-nums">
                        {formatarData(n.criado_em)}
                      </span>
                    </div>

                    {/* Corpo — expandido ao clicar */}
                    {n.corpo && expandida === n.id && (
                      <p className="text-xs text-text-secondary mt-2 leading-relaxed whitespace-pre-line">
                        {n.corpo}
                      </p>
                    )}
                    {n.corpo && expandida !== n.id && (
                      <p className="text-xs text-text-faint mt-0.5 truncate">
                        {n.corpo}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

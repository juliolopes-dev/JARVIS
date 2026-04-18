import { useEffect, useState } from 'react'
import { Bell, Plus, Trash2, X, Repeat, Play, Pause, Zap } from 'lucide-react'
import { toast } from 'sonner'
import { lembretesService, type Lembrete } from '@/services/lembretesService'
import {
  tarefasAgendadasService,
  cronParaTexto,
  type TarefaAgendada,
} from '@/services/tarefasAgendadasService'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/utils/cn'

function formatarDataLembrete(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusLabel(sts: string) {
  if (sts === 'pendente') return { label: 'Pendente', variant: 'accent' as const }
  if (sts === 'disparado') return { label: 'Disparado', variant: 'success' as const }
  return { label: 'Cancelado', variant: 'default' as const }
}

export function LembretesPage() {
  const [aba, setAba] = useState<'pontuais' | 'recorrentes'>('pontuais')
  const [lembretes, setLembretes] = useState<Lembrete[]>([])
  const [carregando, setCarregando] = useState(true)
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState({ titulo: '', descricao: '', dat_lembrete: '' })
  const [salvando, setSalvando] = useState(false)
  useEffect(() => {
    carregarLembretes()
  }, [])

  async function carregarLembretes() {
    try {
      const lista = await lembretesService.listar()
      setLembretes(lista)
    } catch {
      toast.error('Erro ao carregar lembretes')
    } finally {
      setCarregando(false)
    }
  }

  async function criarLembrete() {
    if (!form.titulo.trim() || !form.dat_lembrete) {
      toast.error('Preencha o título e a data/hora')
      return
    }
    setSalvando(true)
    try {
      // Preservar horario local com offset -03:00 (nao usar toISOString que converte para UTC)
      const dat = form.dat_lembrete + ':00-03:00'
      const lembrete = await lembretesService.criar({
        titulo: form.titulo.trim(),
        descricao: form.descricao.trim() || undefined,
        dat_lembrete: dat,
      })
      setLembretes((prev) => [lembrete, ...prev])
      setModal(false)
      setForm({ titulo: '', descricao: '', dat_lembrete: '' })
      toast.success('Lembrete criado!')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Erro ao criar lembrete')
    } finally {
      setSalvando(false)
    }
  }

  async function cancelarLembrete(id: string) {
    try {
      await lembretesService.cancelar(id)
      setLembretes((prev) => prev.filter((l) => l.id !== id))
      toast.success('Lembrete cancelado')
    } catch {
      toast.error('Erro ao cancelar lembrete')
    }
  }

  const pendentes = lembretes.filter((l) => l.sts_lembrete === 'pendente')
  const historico = lembretes.filter((l) => l.sts_lembrete !== 'pendente')

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 h-14 border-b border-surface-border shrink-0">
        <div className="flex items-center gap-2">
          <Bell size={16} className="text-accent" />
          <h1 className="text-sm font-semibold text-text-primary">Agendamentos</h1>
          {aba === 'pontuais' && pendentes.length > 0 && (
            <span className="text-xs bg-accent text-white px-1.5 py-0.5 rounded-full font-medium">
              {pendentes.length}
            </span>
          )}
        </div>
        {aba === 'pontuais' && (
          <Button size="sm" onClick={() => setModal(true)}>
            <Plus size={13} className="mr-1" />
            Novo
          </Button>
        )}
      </div>

      {/* Abas */}
      <div className="flex gap-1 px-6 border-b border-surface-border shrink-0">
        <button
          onClick={() => setAba('pontuais')}
          className={cn(
            'flex items-center gap-1.5 px-3 h-9 text-xs font-medium border-b-2 transition-colors cursor-pointer',
            aba === 'pontuais'
              ? 'border-accent text-text-primary'
              : 'border-transparent text-text-faint hover:text-text-secondary'
          )}
        >
          <Bell size={12} />
          Pontuais
        </button>
        <button
          onClick={() => setAba('recorrentes')}
          className={cn(
            'flex items-center gap-1.5 px-3 h-9 text-xs font-medium border-b-2 transition-colors cursor-pointer',
            aba === 'recorrentes'
              ? 'border-accent text-text-primary'
              : 'border-transparent text-text-faint hover:text-text-secondary'
          )}
        >
          <Repeat size={12} />
          Recorrentes
        </button>
      </div>

      {/* Conteúdo */}
      {aba === 'pontuais' ? (
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {carregando ? (
            <p className="text-sm text-text-faint">Carregando...</p>
          ) : lembretes.length === 0 ? (
            <div className="text-center py-12">
              <Bell size={32} className="text-text-faint mx-auto mb-3" />
              <p className="text-sm text-text-secondary">Nenhum lembrete ainda</p>
              <p className="text-xs text-text-faint mt-1">
                Crie um aqui ou diga ao Jarvis no chat: "me lembra amanhã às 9h de..."
              </p>
            </div>
          ) : (
            <>
              {pendentes.length > 0 && (
                <section>
                  <p className="text-xs font-medium text-text-faint uppercase tracking-wider mb-2">
                    Pendentes
                  </p>
                  <div className="space-y-2">
                    {pendentes.map((l) => (
                      <LembreteCard key={l.id} lembrete={l} onCancelar={cancelarLembrete} />
                    ))}
                  </div>
                </section>
              )}
              {historico.length > 0 && (
                <section>
                  <p className="text-xs font-medium text-text-faint uppercase tracking-wider mb-2">
                    Histórico
                  </p>
                  <div className="space-y-2">
                    {historico.map((l) => (
                      <LembreteCard key={l.id} lembrete={l} onCancelar={cancelarLembrete} />
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      ) : (
        <RecorrentesTab />
      )}

      {/* Modal criar lembrete */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-surface border border-surface-border rounded-lg p-5 w-full max-w-sm mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text-primary">Novo lembrete</h2>
              <button
                onClick={() => setModal(false)}
                className="text-text-faint hover:text-text-primary cursor-pointer"
              >
                <X size={15} />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary block mb-1">Título *</label>
                <Input
                  value={form.titulo}
                  onChange={(e) => setForm((f) => ({ ...f, titulo: e.target.value }))}
                  placeholder="Ex: Ligar pro médico"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary block mb-1">Descrição (opcional)</label>
                <Input
                  value={form.descricao}
                  onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
                  placeholder="Detalhes adicionais..."
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary block mb-1">Data e hora *</label>
                <input
                  type="datetime-local"
                  value={form.dat_lembrete}
                  onChange={(e) => setForm((f) => ({ ...f, dat_lembrete: e.target.value }))}
                  className="w-full h-9 px-3 rounded border border-surface-border bg-surface-raised text-text-primary text-sm focus:outline-none focus:border-accent transition-colors"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <Button variant="ghost" className="flex-1" onClick={() => setModal(false)}>
                Cancelar
              </Button>
              <Button className="flex-1" onClick={criarLembrete} disabled={salvando}>
                {salvando ? 'Salvando...' : 'Criar'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function LembreteCard({
  lembrete,
  onCancelar,
}: {
  lembrete: Lembrete
  onCancelar: (id: string) => void
}) {
  const { label, variant } = statusLabel(lembrete.sts_lembrete)

  return (
    <div className="flex items-start justify-between gap-3 p-3 rounded border border-surface-border bg-surface-raised group">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-medium text-text-primary truncate">{lembrete.titulo}</span>
          <Badge variant={variant}>{label}</Badge>
        </div>
        {lembrete.descricao && (
          <p className="text-xs text-text-secondary truncate">{lembrete.descricao}</p>
        )}
        <p className="text-xs text-text-faint mt-0.5">{formatarDataLembrete(lembrete.dat_lembrete)}</p>
      </div>
      {lembrete.sts_lembrete === 'pendente' && (
        <button
          onClick={() => onCancelar(lembrete.id)}
          className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded text-text-faint hover:text-red-400 transition-all cursor-pointer"
          title="Cancelar lembrete"
        >
          <Trash2 size={13} />
        </button>
      )}
    </div>
  )
}

// ─── Aba Recorrentes ─────────────────────────────────────────────────────────

function RecorrentesTab() {
  const [tarefas, setTarefas] = useState<TarefaAgendada[]>([])
  const [carregando, setCarregando] = useState(true)
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState({ descricao: '', cron_expressao: '0 8 * * *', texto_push: '' })
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    carregar()
  }, [])

  async function carregar() {
    try {
      const lista = await tarefasAgendadasService.listar()
      setTarefas(lista)
    } catch {
      toast.error('Erro ao carregar tarefas recorrentes')
    } finally {
      setCarregando(false)
    }
  }

  async function criar() {
    if (!form.descricao.trim() || !form.cron_expressao.trim()) {
      toast.error('Preencha descrição e cron')
      return
    }
    setSalvando(true)
    try {
      const tarefa = await tarefasAgendadasService.criar({
        descricao: form.descricao.trim(),
        cron_expressao: form.cron_expressao.trim(),
        parametros: {
          texto_push: form.texto_push.trim() || form.descricao.trim(),
          titulo_push: '🔔 ' + form.descricao.trim().slice(0, 40),
          origem: 'manual',
        },
      })
      setTarefas((p) => [tarefa, ...p])
      setModal(false)
      setForm({ descricao: '', cron_expressao: '0 8 * * *', texto_push: '' })
      toast.success('Tarefa recorrente criada!')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Erro ao criar tarefa')
    } finally {
      setSalvando(false)
    }
  }

  async function togglePausa(t: TarefaAgendada) {
    try {
      const novo = t.sts_tarefa === 'ativa' ? 'pausada' : 'ativa'
      const atualizada = await tarefasAgendadasService.atualizar(t.id, { sts_tarefa: novo })
      setTarefas((p) => p.map((x) => (x.id === t.id ? atualizada : x)))
      toast.success(novo === 'ativa' ? 'Tarefa ativada' : 'Tarefa pausada')
    } catch {
      toast.error('Erro ao alterar status')
    }
  }

  async function deletar(id: string) {
    if (!confirm('Deletar esta tarefa recorrente?')) return
    try {
      await tarefasAgendadasService.deletar(id)
      setTarefas((p) => p.filter((x) => x.id !== id))
      toast.success('Tarefa deletada')
    } catch {
      toast.error('Erro ao deletar')
    }
  }

  async function executarAgora(id: string) {
    try {
      await tarefasAgendadasService.executarAgora(id)
      toast.success('Executada — verifique a notificação')
    } catch {
      toast.error('Erro ao executar')
    }
  }

  return (
    <>
      <div className="flex items-center justify-between px-6 h-11 border-b border-surface-border shrink-0">
        <p className="text-xs text-text-faint">
          {tarefas.length} tarefa{tarefas.length !== 1 ? 's' : ''} agendada{tarefas.length !== 1 ? 's' : ''}
        </p>
        <Button size="sm" onClick={() => setModal(true)}>
          <Plus size={13} className="mr-1" />
          Nova
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
        {carregando ? (
          <p className="text-sm text-text-faint">Carregando...</p>
        ) : tarefas.length === 0 ? (
          <div className="text-center py-12">
            <Repeat size={32} className="text-text-faint mx-auto mb-3" />
            <p className="text-sm text-text-secondary">Nenhuma tarefa recorrente</p>
            <p className="text-xs text-text-faint mt-1">
              Diga ao Jarvis: "todo dia às 8h me manda bom dia"
            </p>
          </div>
        ) : (
          tarefas.map((t) => (
            <TarefaRecorrenteCard
              key={t.id}
              tarefa={t}
              onTogglePausa={() => togglePausa(t)}
              onDeletar={() => deletar(t.id)}
              onExecutar={() => executarAgora(t.id)}
            />
          ))
        )}
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-surface border border-surface-border rounded-lg p-5 w-full max-w-sm mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text-primary">Nova tarefa recorrente</h2>
              <button
                onClick={() => setModal(false)}
                className="text-text-faint hover:text-text-primary cursor-pointer"
              >
                <X size={15} />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary block mb-1">Descrição *</label>
                <Input
                  value={form.descricao}
                  onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
                  placeholder="Ex: Bom dia com resumo"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary block mb-1">
                  Cron (min hora dia mês dia_semana) *
                </label>
                <Input
                  value={form.cron_expressao}
                  onChange={(e) => setForm((f) => ({ ...f, cron_expressao: e.target.value }))}
                  placeholder="0 8 * * *"
                />
                <p className="text-xs text-text-faint mt-1">
                  {cronParaTexto(form.cron_expressao)}
                </p>
              </div>
              <div>
                <label className="text-xs text-text-secondary block mb-1">
                  Texto da notificação (opcional)
                </label>
                <Input
                  value={form.texto_push}
                  onChange={(e) => setForm((f) => ({ ...f, texto_push: e.target.value }))}
                  placeholder="Se vazio, usa a descrição"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <Button variant="ghost" className="flex-1" onClick={() => setModal(false)}>
                Cancelar
              </Button>
              <Button className="flex-1" onClick={criar} disabled={salvando}>
                {salvando ? 'Salvando...' : 'Criar'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function TarefaRecorrenteCard({
  tarefa,
  onTogglePausa,
  onDeletar,
  onExecutar,
}: {
  tarefa: TarefaAgendada
  onTogglePausa: () => void
  onDeletar: () => void
  onExecutar: () => void
}) {
  const ativa = tarefa.sts_tarefa === 'ativa'
  const proxima = tarefa.dat_proxima_execucao
    ? new Date(tarefa.dat_proxima_execucao).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null

  return (
    <div
      className={cn(
        'flex items-start justify-between gap-3 p-3 rounded border bg-surface-raised group',
        ativa ? 'border-surface-border' : 'border-surface-border opacity-60'
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-text-primary truncate">{tarefa.descricao}</span>
          <Badge variant={ativa ? 'accent' : 'default'}>{ativa ? 'Ativa' : 'Pausada'}</Badge>
        </div>
        <p className="text-xs text-text-secondary">{cronParaTexto(tarefa.cron_expressao ?? '')}</p>
        {proxima && ativa && (
          <p className="text-xs text-text-faint mt-0.5">Próxima: {proxima}</p>
        )}
      </div>
      <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onExecutar}
          className="p-1.5 rounded text-text-faint hover:text-accent hover:bg-surface-overlay transition-colors cursor-pointer"
          title="Executar agora"
        >
          <Zap size={13} />
        </button>
        <button
          onClick={onTogglePausa}
          className="p-1.5 rounded text-text-faint hover:text-text-primary hover:bg-surface-overlay transition-colors cursor-pointer"
          title={ativa ? 'Pausar' : 'Ativar'}
        >
          {ativa ? <Pause size={13} /> : <Play size={13} />}
        </button>
        <button
          onClick={onDeletar}
          className="p-1.5 rounded text-text-faint hover:text-red-400 hover:bg-surface-overlay transition-colors cursor-pointer"
          title="Deletar"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  )
}

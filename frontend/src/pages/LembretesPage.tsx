import { useEffect, useState } from 'react'
import { Bell, Plus, Trash2, X } from 'lucide-react'
import { toast } from 'sonner'
import { lembretesService, type Lembrete } from '@/services/lembretesService'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'

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
          <h1 className="text-sm font-semibold text-text-primary">Lembretes</h1>
          {pendentes.length > 0 && (
            <span className="text-xs bg-accent text-white px-1.5 py-0.5 rounded-full font-medium">
              {pendentes.length}
            </span>
          )}
        </div>
        <Button size="sm" onClick={() => setModal(true)}>
          <Plus size={13} className="mr-1" />
          Novo
        </Button>
      </div>

      {/* Conteúdo */}
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
            {/* Pendentes */}
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

            {/* Histórico */}
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

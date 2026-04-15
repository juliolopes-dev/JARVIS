import { useEffect, useState, useRef } from 'react'
import {
  CheckSquare,
  Plus,
  Trash2,
  X,
  ChevronRight,
  Circle,
  CheckCircle2,
  AlertCircle,
  ArrowUp,
  Minus,
  Pencil,
  Calendar,
  Tag,
  AlignLeft,
  ArrowLeft,
} from 'lucide-react'
import { toast } from 'sonner'
import { checklistService, type Lista, type Tarefa } from '@/services/checklistService'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { cn } from '@/utils/cn'

// ─── Constantes ───────────────────────────────────────────────────────────────

const PRIORIDADES = [
  { valor: 'baixa', label: 'Baixa', cor: 'text-text-faint' },
  { valor: 'media', label: 'Média', cor: 'text-blue-400' },
  { valor: 'alta', label: 'Alta', cor: 'text-orange-400' },
  { valor: 'urgente', label: 'Urgente', cor: 'text-red-400' },
]

function PrioridadeIcon({ prioridade, size = 13 }: { prioridade: string; size?: number }) {
  if (prioridade === 'urgente') return <AlertCircle size={size} className="text-red-400" />
  if (prioridade === 'alta') return <ArrowUp size={size} className="text-orange-400" />
  if (prioridade === 'baixa') return <Minus size={size} className="text-text-faint" />
  return <Minus size={size} className="text-blue-400" />
}

function formatarVencimento(iso: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  const hoje = new Date()
  hoje.setHours(0, 0, 0, 0)
  const amanha = new Date(hoje)
  amanha.setDate(amanha.getDate() + 1)
  const data = new Date(d)
  data.setHours(0, 0, 0, 0)

  if (data.getTime() === hoje.getTime()) return { texto: 'Hoje', atrasado: false }
  if (data.getTime() === amanha.getTime()) return { texto: 'Amanhã', atrasado: false }
  if (data < hoje) {
    return {
      texto: d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }),
      atrasado: true,
    }
  }
  return {
    texto: d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }),
    atrasado: false,
  }
}

function isoParaDate(iso: string | null): string {
  if (!iso) return ''
  return iso.slice(0, 10)
}

// ─── Tarefa Card ─────────────────────────────────────────────────────────────

function TarefaItem({
  tarefa,
  selecionada,
  onConcluir,
  onDeletar,
  onClick,
}: {
  tarefa: Tarefa
  selecionada: boolean
  onConcluir: (id: string) => void
  onDeletar: (id: string) => void
  onClick: (tarefa: Tarefa) => void
}) {
  const venc = formatarVencimento(tarefa.dat_vencimento)

  return (
    <div
      className={cn(
        'group flex items-center gap-2.5 px-3 py-2.5 rounded border transition-colors cursor-pointer',
        tarefa.flg_concluida
          ? 'border-surface-border/50 bg-transparent opacity-60'
          : selecionada
          ? 'border-accent/40 bg-accent/5'
          : 'border-surface-border bg-surface-raised hover:border-surface-muted'
      )}
      onClick={() => onClick(tarefa)}
    >
      {/* Checkbox */}
      <button
        onClick={(e) => { e.stopPropagation(); onConcluir(tarefa.id) }}
        className="shrink-0 text-text-faint hover:text-accent transition-colors cursor-pointer"
        title={tarefa.flg_concluida ? 'Desmarcar' : 'Concluir'}
      >
        {tarefa.flg_concluida
          ? <CheckCircle2 size={16} className="text-accent" />
          : <Circle size={16} />
        }
      </button>

      {/* Conteúdo */}
      <div className="flex-1 min-w-0">
        <span className={cn(
          'text-sm text-text-primary truncate block',
          tarefa.flg_concluida && 'line-through text-text-faint'
        )}>
          {tarefa.titulo}
        </span>
        <div className="flex items-center gap-2 mt-0.5">
          <PrioridadeIcon prioridade={tarefa.prioridade} size={11} />
          <span className="text-xs text-text-faint">
            {PRIORIDADES.find(p => p.valor === tarefa.prioridade)?.label}
          </span>
          {venc && (
            <span className={cn('text-xs', venc.atrasado ? 'text-red-400' : 'text-text-faint')}>
              · {venc.texto}
            </span>
          )}
        </div>
      </div>

      {/* Deletar — hover */}
      <button
        onClick={(e) => { e.stopPropagation(); onDeletar(tarefa.id) }}
        className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded text-text-faint hover:text-red-400 transition-all cursor-pointer"
        title="Deletar"
      >
        <Trash2 size={12} />
      </button>
    </div>
  )
}

// ─── Painel de detalhes ───────────────────────────────────────────────────────

function PainelDetalhes({
  tarefa,
  listas,
  onFechar,
  onEditar,
  onConcluir,
  onDeletar,
  mobile = false,
}: {
  tarefa: Tarefa
  listas: Lista[]
  onFechar: () => void
  onEditar: (tarefa: Tarefa) => void
  onConcluir: (id: string) => void
  onDeletar: (id: string) => void
  mobile?: boolean
}) {
  const venc = formatarVencimento(tarefa.dat_vencimento)
  const lista = listas.find(l => l.id === tarefa.id_lista)
  const prio = PRIORIDADES.find(p => p.valor === tarefa.prioridade)

  if (mobile) {
    return (
      <>
        {/* Overlay */}
        <div
          className="fixed inset-0 z-40 bg-black/50"
          onClick={onFechar}
        />
        {/* Bottom sheet */}
        <div className="fixed bottom-0 left-0 right-0 z-50 bg-surface border-t border-surface-border rounded-t-xl flex flex-col max-h-[75vh]">
          {/* Handle */}
          <div className="flex justify-center pt-3 pb-1 shrink-0">
            <div className="w-8 h-1 rounded-full bg-surface-muted" />
          </div>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border shrink-0">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Detalhes</span>
            <button onClick={onFechar} className="p-1 rounded text-text-faint hover:text-text-primary cursor-pointer">
              <X size={14} />
            </button>
          </div>
          {/* Conteúdo */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            <div className="flex items-start gap-2">
              <button onClick={() => onConcluir(tarefa.id)} className="shrink-0 mt-0.5 text-text-faint hover:text-accent transition-colors cursor-pointer">
                {tarefa.flg_concluida ? <CheckCircle2 size={18} className="text-accent" /> : <Circle size={18} />}
              </button>
              <h2 className={cn('text-sm font-semibold text-text-primary leading-snug', tarefa.flg_concluida && 'line-through text-text-faint')}>
                {tarefa.titulo}
              </h2>
            </div>
            {tarefa.descricao && (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <AlignLeft size={12} className="text-text-faint" />
                  <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Descrição</span>
                </div>
                <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">{tarefa.descricao}</p>
              </div>
            )}
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <PrioridadeIcon prioridade={tarefa.prioridade} size={12} />
                <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Prioridade</span>
              </div>
              <span className={cn('text-sm font-medium', prio?.cor ?? 'text-text-secondary')}>{prio?.label ?? tarefa.prioridade}</span>
            </div>
            {lista && (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Tag size={12} className="text-text-faint" />
                  <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Lista</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: lista.cor }} />
                  <span className="text-sm text-text-secondary">{lista.nome}</span>
                </div>
              </div>
            )}
            {venc && (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Calendar size={12} className="text-text-faint" />
                  <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Vencimento</span>
                </div>
                <span className={cn('text-sm font-medium', venc.atrasado ? 'text-red-400' : 'text-text-secondary')}>
                  {venc.atrasado && '⚠ '}{venc.texto}{venc.atrasado && ' — atrasada'}
                </span>
              </div>
            )}
          </div>
          {/* Ações */}
          <div className="shrink-0 border-t border-surface-border p-4 flex gap-2 pb-8">
            <Button size="sm" className="flex-1" onClick={() => { onEditar(tarefa); onFechar() }}>
              <Pencil size={12} className="mr-1.5" />Editar
            </Button>
            <button
              onClick={() => { onDeletar(tarefa.id); onFechar() }}
              className="flex items-center gap-1.5 h-8 px-3 rounded text-xs font-medium border border-surface-border text-text-faint hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10 transition-colors cursor-pointer"
            >
              <Trash2 size={12} />Deletar
            </button>
          </div>
        </div>
      </>
    )
  }

  return (
    <div className="w-[280px] shrink-0 border-l border-surface-border flex flex-col bg-surface">
      {/* Header */}
      <div className="flex items-center justify-between px-4 h-14 border-b border-surface-border shrink-0">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          Detalhes
        </span>
        <button
          onClick={onFechar}
          className="p-1 rounded text-text-faint hover:text-text-primary hover:bg-surface-overlay transition-colors cursor-pointer"
        >
          <X size={14} />
        </button>
      </div>

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Título + status */}
        <div className="flex items-start gap-2">
          <button
            onClick={() => onConcluir(tarefa.id)}
            className="shrink-0 mt-0.5 text-text-faint hover:text-accent transition-colors cursor-pointer"
          >
            {tarefa.flg_concluida
              ? <CheckCircle2 size={18} className="text-accent" />
              : <Circle size={18} />
            }
          </button>
          <h2 className={cn(
            'text-sm font-semibold text-text-primary leading-snug',
            tarefa.flg_concluida && 'line-through text-text-faint'
          )}>
            {tarefa.titulo}
          </h2>
        </div>

        {/* Descrição */}
        {tarefa.descricao && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <AlignLeft size={12} className="text-text-faint" />
              <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Descrição</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
              {tarefa.descricao}
            </p>
          </div>
        )}

        {/* Prioridade */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <PrioridadeIcon prioridade={tarefa.prioridade} size={12} />
            <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Prioridade</span>
          </div>
          <span className={cn('text-sm font-medium', prio?.cor ?? 'text-text-secondary')}>
            {prio?.label ?? tarefa.prioridade}
          </span>
        </div>

        {/* Lista */}
        {lista && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Tag size={12} className="text-text-faint" />
              <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Lista</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: lista.cor }} />
              <span className="text-sm text-text-secondary">{lista.nome}</span>
            </div>
          </div>
        )}

        {/* Vencimento */}
        {venc && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Calendar size={12} className="text-text-faint" />
              <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Vencimento</span>
            </div>
            <span className={cn('text-sm font-medium', venc.atrasado ? 'text-red-400' : 'text-text-secondary')}>
              {venc.atrasado && '⚠ '}
              {venc.texto}
              {venc.atrasado && ' — atrasada'}
            </span>
          </div>
        )}

        {/* Status */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <CheckSquare size={12} className="text-text-faint" />
            <span className="text-2xs text-text-faint uppercase tracking-wider font-medium">Status</span>
          </div>
          <span className={cn('text-sm font-medium', tarefa.flg_concluida ? 'text-green-400' : 'text-text-secondary')}>
            {tarefa.flg_concluida ? 'Concluída' : 'Pendente'}
          </span>
        </div>
      </div>

      {/* Ações */}
      <div className="shrink-0 border-t border-surface-border p-4 flex gap-2">
        <Button
          size="sm"
          className="flex-1"
          onClick={() => onEditar(tarefa)}
        >
          <Pencil size={12} className="mr-1.5" />
          Editar
        </Button>
        <button
          onClick={() => { onDeletar(tarefa.id); onFechar() }}
          className="flex items-center gap-1.5 h-8 px-3 rounded text-xs font-medium border border-surface-border text-text-faint hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10 transition-colors cursor-pointer"
          title="Deletar tarefa"
        >
          <Trash2 size={12} />
          Deletar
        </button>
      </div>
    </div>
  )
}

// ─── Modal tarefa (criar e editar) ───────────────────────────────────────────

function ModalTarefa({
  listas,
  idListaInicial,
  tarefaEditando,
  onSalvar,
  onFechar,
}: {
  listas: Lista[]
  idListaInicial: string | null
  tarefaEditando: Tarefa | null
  onSalvar: (dados: { titulo: string; descricao: string; prioridade: string; id_lista: string | null; dat_vencimento: string }) => Promise<void>
  onFechar: () => void
}) {
  const editando = tarefaEditando !== null
  const [form, setForm] = useState({
    titulo: tarefaEditando?.titulo ?? '',
    descricao: tarefaEditando?.descricao ?? '',
    prioridade: tarefaEditando?.prioridade ?? 'media',
    id_lista: tarefaEditando?.id_lista ?? idListaInicial ?? (listas[0]?.id ?? ''),
    dat_vencimento: isoParaDate(tarefaEditando?.dat_vencimento ?? null),
  })
  const [salvando, setSalvando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  async function handleSalvar() {
    if (!form.titulo.trim()) { toast.error('Título obrigatório'); return }
    setSalvando(true)
    try {
      await onSalvar({
        titulo: form.titulo.trim(),
        descricao: form.descricao.trim(),
        prioridade: form.prioridade,
        id_lista: form.id_lista || null,
        dat_vencimento: form.dat_vencimento,
      })
      onFechar()
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-surface border border-surface-border rounded-lg p-5 w-full max-w-sm mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">
            {editando ? 'Editar tarefa' : 'Nova tarefa'}
          </h2>
          <button onClick={onFechar} className="text-text-faint hover:text-text-primary cursor-pointer">
            <X size={15} />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-text-secondary block mb-1">Título *</label>
            <Input
              ref={inputRef}
              value={form.titulo}
              onChange={(e) => setForm(f => ({ ...f, titulo: e.target.value }))}
              placeholder="Ex: Comprar leite"
              onKeyDown={(e) => e.key === 'Enter' && handleSalvar()}
            />
          </div>

          <div>
            <label className="text-xs text-text-secondary block mb-1">Descrição (opcional)</label>
            <textarea
              value={form.descricao}
              onChange={(e) => {
                setForm(f => ({ ...f, descricao: e.target.value }))
                e.target.style.height = 'auto'
                e.target.style.height = e.target.scrollHeight + 'px'
              }}
              placeholder="Detalhes..."
              rows={2}
              className="w-full px-3 py-2 rounded border border-surface-border bg-surface-raised text-text-primary text-sm placeholder:text-text-faint focus:outline-none focus:border-accent transition-colors resize-none overflow-hidden min-h-[36px]"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-text-secondary block mb-1">Prioridade</label>
              <select
                value={form.prioridade}
                onChange={(e) => setForm(f => ({ ...f, prioridade: e.target.value as Tarefa['prioridade'] }))}
                className="w-full h-9 px-2 rounded border border-surface-border bg-surface-raised text-text-primary text-sm focus:outline-none focus:border-accent transition-colors cursor-pointer"
              >
                {PRIORIDADES.map(p => <option key={p.valor} value={p.valor}>{p.label}</option>)}
              </select>
            </div>

            <div>
              <label className="text-xs text-text-secondary block mb-1">Lista</label>
              <select
                value={form.id_lista}
                onChange={(e) => setForm(f => ({ ...f, id_lista: e.target.value }))}
                className="w-full h-9 px-2 rounded border border-surface-border bg-surface-raised text-text-primary text-sm focus:outline-none focus:border-accent transition-colors cursor-pointer"
              >
                {listas.map(l => <option key={l.id} value={l.id}>{l.nome}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs text-text-secondary block mb-1">Vencimento (opcional)</label>
            <input
              type="date"
              value={form.dat_vencimento}
              onChange={(e) => setForm(f => ({ ...f, dat_vencimento: e.target.value }))}
              className="w-full h-9 px-3 rounded border border-surface-border bg-surface-raised text-text-primary text-sm focus:outline-none focus:border-accent transition-colors"
            />
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button variant="ghost" className="flex-1" onClick={onFechar}>Cancelar</Button>
          <Button className="flex-1" onClick={handleSalvar} disabled={salvando}>
            {salvando ? 'Salvando...' : editando ? 'Salvar' : 'Criar'}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Modal lista (criar e editar) ─────────────────────────────────────────────

function ModalLista({
  listaEditando,
  onSalvar,
  onFechar,
}: {
  listaEditando: Lista | null
  onSalvar: (nome: string, cor: string) => Promise<void>
  onFechar: () => void
}) {
  const CORES = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']
  const editando = listaEditando !== null
  const [nome, setNome] = useState(listaEditando?.nome ?? '')
  const [cor, setCor] = useState(listaEditando?.cor ?? '#3b82f6')
  const [salvando, setSalvando] = useState(false)

  async function handleSalvar() {
    if (!nome.trim()) { toast.error('Nome obrigatório'); return }
    setSalvando(true)
    try {
      await onSalvar(nome.trim(), cor)
      onFechar()
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-surface border border-surface-border rounded-lg p-5 w-full max-w-xs mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">
            {editando ? 'Editar lista' : 'Nova lista'}
          </h2>
          <button onClick={onFechar} className="text-text-faint hover:text-text-primary cursor-pointer">
            <X size={15} />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-text-secondary block mb-1">Nome *</label>
            <Input
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Ex: Compras"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleSalvar()}
            />
          </div>

          <div>
            <label className="text-xs text-text-secondary block mb-2">Cor</label>
            <div className="flex gap-2 flex-wrap">
              {CORES.map(c => (
                <button
                  key={c}
                  onClick={() => setCor(c)}
                  className={cn(
                    'w-6 h-6 rounded-full transition-all cursor-pointer',
                    cor === c ? 'ring-2 ring-white ring-offset-2 ring-offset-surface' : ''
                  )}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button variant="ghost" className="flex-1" onClick={onFechar}>Cancelar</Button>
          <Button className="flex-1" onClick={handleSalvar} disabled={salvando}>
            {salvando ? 'Salvando...' : editando ? 'Salvar' : 'Criar'}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function TarefasPage() {
  const [listas, setListas] = useState<Lista[]>([])
  const [tarefas, setTarefas] = useState<Tarefa[]>([])
  const [listaSelecionada, setListaSelecionada] = useState<string | null>(null)
  const [carregandoListas, setCarregandoListas] = useState(true)
  const [carregandoTarefas, setCarregandoTarefas] = useState(false)

  // Mobile: controla qual "tela" está visível
  const [vistaAtiva, setVistaAtiva] = useState<'listas' | 'tarefas'>('listas')

  // Painel de detalhes
  const [tarefaDetalhes, setTarefaDetalhes] = useState<Tarefa | null>(null)

  // Modais
  const [tarefaEditando, setTarefaEditando] = useState<Tarefa | null>(null)
  const [modalTarefa, setModalTarefa] = useState(false)
  const [listaEditando, setListaEditando] = useState<Lista | null>(null)
  const [modalLista, setModalLista] = useState(false)

  useEffect(() => { carregarListas() }, [])

  useEffect(() => {
    if (listaSelecionada !== undefined) carregarTarefas()
  }, [listaSelecionada])

  async function carregarListas() {
    try {
      const dados = await checklistService.listarListas()
      setListas(dados)
      if (dados.length > 0 && listaSelecionada === null) setListaSelecionada(dados[0].id)
    } catch {
      toast.error('Erro ao carregar listas')
    } finally {
      setCarregandoListas(false)
    }
  }

  async function carregarTarefas() {
    setCarregandoTarefas(true)
    try {
      const dados = await checklistService.listarTarefas(listaSelecionada ?? undefined)
      setTarefas(dados)
    } catch {
      toast.error('Erro ao carregar tarefas')
    } finally {
      setCarregandoTarefas(false)
    }
  }

  // ── Lista ─────────────────────────────────────────────────────────────────

  function abrirNovaLista() { setListaEditando(null); setModalLista(true) }

  function abrirEditarLista(lista: Lista, e: React.MouseEvent) {
    e.stopPropagation()
    setListaEditando(lista)
    setModalLista(true)
  }

  async function salvarLista(nome: string, cor: string) {
    if (listaEditando) {
      const atualizada = await checklistService.atualizarLista(listaEditando.id, { nome, cor })
      setListas(prev => prev.map(l => l.id === listaEditando.id ? { ...l, ...atualizada } : l))
      toast.success('Lista atualizada!')
    } else {
      const lista = await checklistService.criarLista({ nome, cor })
      setListas(prev => [...prev, lista])
      setListaSelecionada(lista.id)
      toast.success('Lista criada!')
    }
  }

  async function deletarLista(id: string) {
    if (!confirm('Deletar lista e todas as tarefas?')) return
    try {
      await checklistService.deletarLista(id)
      const novasListas = listas.filter(l => l.id !== id)
      setListas(novasListas)
      if (listaSelecionada === id) setListaSelecionada(novasListas[0]?.id ?? null)
      toast.success('Lista deletada')
    } catch {
      toast.error('Erro ao deletar lista')
    }
  }

  // ── Tarefa ────────────────────────────────────────────────────────────────

  function abrirNovaTarefa() { setTarefaEditando(null); setModalTarefa(true) }

  function abrirEditarTarefa(tarefa: Tarefa) {
    setTarefaEditando(tarefa)
    setModalTarefa(true)
  }

  function abrirDetalhes(tarefa: Tarefa) {
    // Toggle: clica na mesma → fecha
    setTarefaDetalhes(prev => prev?.id === tarefa.id ? null : tarefa)
  }

  async function salvarTarefa(dados: {
    titulo: string; descricao: string; prioridade: string
    id_lista: string | null; dat_vencimento: string
  }) {
    if (tarefaEditando) {
      try {
        const payload: Parameters<typeof checklistService.atualizarTarefa>[1] = {
          titulo: dados.titulo,
          prioridade: dados.prioridade,
          id_lista: dados.id_lista ?? undefined,
          dat_vencimento: dados.dat_vencimento ? dados.dat_vencimento + 'T00:00:00-03:00' : null,
        }
        if (dados.descricao) payload.descricao = dados.descricao
        const atualizada = await checklistService.atualizarTarefa(tarefaEditando.id, payload)
        setTarefas(prev => prev.map(t => t.id === tarefaEditando.id ? atualizada : t))
        // Atualiza o painel de detalhes se estiver aberto para essa tarefa
        if (tarefaDetalhes?.id === tarefaEditando.id) setTarefaDetalhes(atualizada)
        // Se mudou de lista, remove da view atual
        if (atualizada.id_lista !== listaSelecionada) {
          setTarefas(prev => prev.filter(t => t.id !== tarefaEditando.id))
          setTarefaDetalhes(null)
        }
        toast.success('Tarefa atualizada!')
      } catch {
        toast.error('Erro ao atualizar tarefa')
      }
    } else {
      try {
        const payload: Parameters<typeof checklistService.criarTarefa>[0] = {
          titulo: dados.titulo,
          prioridade: dados.prioridade,
          id_lista: dados.id_lista ?? listaSelecionada ?? undefined,
        }
        if (dados.descricao) payload.descricao = dados.descricao
        if (dados.dat_vencimento) payload.dat_vencimento = dados.dat_vencimento + 'T00:00:00-03:00'
        const tarefa = await checklistService.criarTarefa(payload)
        setTarefas(prev => [tarefa, ...prev])
        setListas(prev => prev.map(l =>
          l.id === (dados.id_lista ?? listaSelecionada)
            ? { ...l, total_tarefas: l.total_tarefas + 1 }
            : l
        ))
        toast.success('Tarefa criada!')
      } catch {
        toast.error('Erro ao criar tarefa')
      }
    }
  }

  async function concluirTarefa(id: string) {
    try {
      const atualizada = await checklistService.concluirTarefa(id)
      setTarefas(prev => prev.map(t => t.id === id ? atualizada : t))
      if (tarefaDetalhes?.id === id) setTarefaDetalhes(atualizada)
      setListas(prev => prev.map(l => {
        if (l.id !== listaSelecionada) return l
        const delta = atualizada.flg_concluida ? 1 : -1
        return { ...l, total_concluidas: l.total_concluidas + delta }
      }))
    } catch {
      toast.error('Erro ao atualizar tarefa')
    }
  }

  async function deletarTarefa(id: string) {
    try {
      await checklistService.deletarTarefa(id)
      setTarefas(prev => prev.filter(t => t.id !== id))
      if (tarefaDetalhes?.id === id) setTarefaDetalhes(null)
      setListas(prev => prev.map(l => {
        if (l.id !== listaSelecionada) return l
        const tarefa = tarefas.find(t => t.id === id)
        return {
          ...l,
          total_tarefas: l.total_tarefas - 1,
          total_concluidas: tarefa?.flg_concluida ? l.total_concluidas - 1 : l.total_concluidas,
        }
      }))
    } catch {
      toast.error('Erro ao deletar tarefa')
    }
  }

  const tarefasPendentes = tarefas.filter(t => !t.flg_concluida)
  const tarefasConcluidas = tarefas.filter(t => t.flg_concluida)
  const listaSel = listas.find(l => l.id === listaSelecionada)

  return (
    <div className="flex h-full">

      {/* ── Coluna de listas — desktop sempre visível, mobile só na vista 'listas' ── */}
      <div className={cn(
        'shrink-0 border-r border-surface-border flex flex-col bg-surface',
        'md:w-[200px] md:flex',                          // desktop: sempre visível
        vistaAtiva === 'listas' ? 'flex w-full' : 'hidden md:flex'  // mobile: tela cheia ou oculta
      )}>
        <div className="flex items-center justify-between px-3 h-14 border-b border-surface-border shrink-0">
          <div className="flex items-center gap-2">
            <CheckSquare size={14} className="text-accent" />
            <span className="text-xs font-semibold text-text-primary">Listas</span>
          </div>
          <button
            onClick={abrirNovaLista}
            className="p-1 rounded text-text-faint hover:text-text-primary hover:bg-surface-overlay transition-colors cursor-pointer"
            title="Nova lista"
          >
            <Plus size={14} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-1">
          {carregandoListas ? (
            <p className="px-3 py-2 text-xs text-text-faint">Carregando...</p>
          ) : listas.length === 0 ? (
            <p className="px-3 py-2 text-xs text-text-faint">Nenhuma lista</p>
          ) : listas.map(lista => (
            <button
              key={lista.id}
              onClick={() => { setListaSelecionada(lista.id); setTarefaDetalhes(null); setVistaAtiva('tarefas') }}
              className={cn(
                'w-full group flex items-center justify-between gap-1 px-3 py-2.5 md:py-2 text-sm transition-colors cursor-pointer',
                listaSelecionada === lista.id
                  ? 'bg-surface-overlay text-text-primary'
                  : 'text-text-secondary hover:bg-white/[0.04] hover:text-text-primary'
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: lista.cor }} />
                <span className="truncate text-xs">{lista.nome}</span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {lista.total_tarefas > 0 && (
                  <span className="text-2xs text-text-faint tabular-nums md:group-hover:hidden">
                    {lista.total_concluidas}/{lista.total_tarefas}
                  </span>
                )}
                <button
                  onClick={(e) => abrirEditarLista(lista, e)}
                  className="hidden md:group-hover:flex p-0.5 rounded text-text-faint hover:text-text-primary transition-colors cursor-pointer"
                  title="Editar lista"
                >
                  <Pencil size={10} />
                </button>
                <ChevronRight size={12} className="text-text-faint md:hidden" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Coluna de tarefas — desktop sempre visível, mobile só na vista 'tarefas' ── */}
      <div className={cn(
        'flex-1 min-w-0 flex flex-col',
        vistaAtiva === 'tarefas' ? 'flex' : 'hidden md:flex'
      )}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 md:px-6 h-14 border-b border-surface-border shrink-0">
          <div className="flex items-center gap-2">
            {/* Botão voltar — só mobile */}
            <button
              onClick={() => { setVistaAtiva('listas'); setTarefaDetalhes(null) }}
              className="md:hidden p-1 -ml-1 rounded text-text-faint hover:text-text-primary transition-colors cursor-pointer"
            >
              <ArrowLeft size={16} />
            </button>
            {listaSel && (
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: listaSel.cor }} />
            )}
            <h1 className="text-sm font-semibold text-text-primary">
              {listaSel?.nome ?? 'Tarefas'}
            </h1>
            {tarefasPendentes.length > 0 && (
              <span className="text-xs bg-surface-overlay text-text-secondary px-1.5 py-0.5 rounded font-medium tabular-nums">
                {tarefasPendentes.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {listaSel && (
              <button
                onClick={() => deletarLista(listaSel.id)}
                className="p-1.5 rounded text-text-faint hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                title="Deletar lista"
              >
                <Trash2 size={13} />
              </button>
            )}
            <Button size="sm" onClick={() => listas.length === 0 ? abrirNovaLista() : abrirNovaTarefa()}>
              <Plus size={13} className="mr-1" />
              {listas.length === 0 ? 'Nova lista' : 'Nova tarefa'}
            </Button>
          </div>
        </div>

        {/* Lista de tarefas */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4">
          {!listaSelecionada ? (
            <div className="text-center py-16">
              <CheckSquare size={32} className="text-text-faint mx-auto mb-3" />
              <p className="text-sm text-text-secondary">Crie uma lista para começar</p>
              <button onClick={abrirNovaLista} className="mt-3 text-xs text-accent hover:underline cursor-pointer">
                + Nova lista
              </button>
            </div>
          ) : carregandoTarefas ? (
            <p className="text-sm text-text-faint">Carregando...</p>
          ) : tarefas.length === 0 ? (
            <div className="text-center py-16">
              <CheckSquare size={32} className="text-text-faint mx-auto mb-3" />
              <p className="text-sm text-text-secondary">Nenhuma tarefa nesta lista</p>
              <p className="text-xs text-text-faint mt-1">
                Crie aqui ou diga ao Jarvis: "adiciona X na lista {listaSel?.nome}"
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {tarefasPendentes.length > 0 && (
                <section>
                  <div className="space-y-1.5">
                    {tarefasPendentes.map(t => (
                      <TarefaItem
                        key={t.id}
                        tarefa={t}
                        selecionada={tarefaDetalhes?.id === t.id}
                        onConcluir={concluirTarefa}
                        onDeletar={deletarTarefa}
                        onClick={abrirDetalhes}
                      />
                    ))}
                  </div>
                </section>
              )}
              {tarefasConcluidas.length > 0 && (
                <section>
                  <p className="text-xs font-medium text-text-faint uppercase tracking-wider mb-2">
                    Concluídas ({tarefasConcluidas.length})
                  </p>
                  <div className="space-y-1.5">
                    {tarefasConcluidas.map(t => (
                      <TarefaItem
                        key={t.id}
                        tarefa={t}
                        selecionada={tarefaDetalhes?.id === t.id}
                        onConcluir={concluirTarefa}
                        onDeletar={deletarTarefa}
                        onClick={abrirDetalhes}
                      />
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Painel de detalhes — desktop: coluna lateral | mobile: bottom sheet ── */}
      {tarefaDetalhes && (
        <>
          {/* Desktop */}
          <div className="hidden md:block">
            <PainelDetalhes
              tarefa={tarefaDetalhes}
              listas={listas}
              onFechar={() => setTarefaDetalhes(null)}
              onEditar={abrirEditarTarefa}
              onConcluir={concluirTarefa}
              onDeletar={deletarTarefa}
            />
          </div>
          {/* Mobile */}
          <div className="md:hidden">
            <PainelDetalhes
              tarefa={tarefaDetalhes}
              listas={listas}
              onFechar={() => setTarefaDetalhes(null)}
              onEditar={abrirEditarTarefa}
              onConcluir={concluirTarefa}
              onDeletar={deletarTarefa}
              mobile
            />
          </div>
        </>
      )}

      {/* Modais */}
      {modalTarefa && (
        <ModalTarefa
          listas={listas}
          idListaInicial={listaSelecionada}
          tarefaEditando={tarefaEditando}
          onSalvar={salvarTarefa}
          onFechar={() => { setModalTarefa(false); setTarefaEditando(null) }}
        />
      )}
      {modalLista && (
        <ModalLista
          listaEditando={listaEditando}
          onSalvar={salvarLista}
          onFechar={() => { setModalLista(false); setListaEditando(null) }}
        />
      )}
    </div>
  )
}

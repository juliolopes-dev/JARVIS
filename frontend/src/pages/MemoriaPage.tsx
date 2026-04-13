import { useEffect, useState } from 'react'
import { Brain, Users, Trash2, Plus, X } from 'lucide-react'
import { toast } from 'sonner'
import { memoriaService } from '@/services/memoriaService'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { formatarDataRelativa } from '@/utils/formatDate'
import { cn } from '@/utils/cn'
import type { Memoria, Pessoa } from '@/types'

type Aba = 'memorias' | 'pessoas'

export function MemoriaPage() {
  const [aba, setAba] = useState<Aba>('memorias')
  const [memorias, setMemorias] = useState<Memoria[]>([])
  const [pessoas, setPessoas] = useState<Pessoa[]>([])
  const [carregando, setCarregando] = useState(true)
  const [modalPessoa, setModalPessoa] = useState(false)
  const [pessoaEditando, setPessoaEditando] = useState<Pessoa | null>(null)
  const [formPessoa, setFormPessoa] = useState({ nome: '', relacao: '', notas: '' })
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    if (aba === 'memorias') carregarMemorias()
    else carregarPessoas()
  }, [aba])

  async function carregarMemorias() {
    setCarregando(true)
    try {
      const lista = await memoriaService.listarMemorias()
      setMemorias(lista)
    } catch {
      toast.error('Erro ao carregar memórias')
    } finally {
      setCarregando(false)
    }
  }

  async function carregarPessoas() {
    setCarregando(true)
    try {
      const lista = await memoriaService.listarPessoas()
      setPessoas(lista)
    } catch {
      toast.error('Erro ao carregar pessoas')
    } finally {
      setCarregando(false)
    }
  }

  async function deletarMemoria(id: string) {
    try {
      await memoriaService.desativarMemoria(id)
      setMemorias((prev) => prev.filter((m) => m.id !== id))
      toast.success('Memória removida')
    } catch {
      toast.error('Erro ao remover memória')
    }
  }

  function abrirModalNovaPessoa() {
    setPessoaEditando(null)
    setFormPessoa({ nome: '', relacao: '', notas: '' })
    setModalPessoa(true)
  }

  function abrirModalEditarPessoa(pessoa: Pessoa) {
    setPessoaEditando(pessoa)
    setFormPessoa({
      nome: pessoa.nome,
      relacao: pessoa.relacao ?? '',
      notas: pessoa.notas ?? '',
    })
    setModalPessoa(true)
  }

  async function salvarPessoa() {
    if (!formPessoa.nome.trim()) return
    setSalvando(true)
    try {
      if (pessoaEditando) {
        const atualizada = await memoriaService.atualizarPessoa(pessoaEditando.id, formPessoa)
        setPessoas((prev) => prev.map((p) => (p.id === atualizada.id ? atualizada : p)))
        toast.success('Pessoa atualizada')
      } else {
        const nova = await memoriaService.criarPessoa(formPessoa)
        setPessoas((prev) => [nova, ...prev])
        toast.success('Pessoa adicionada')
      }
      setModalPessoa(false)
    } catch {
      toast.error('Erro ao salvar pessoa')
    } finally {
      setSalvando(false)
    }
  }

  async function deletarPessoa(id: string) {
    try {
      await memoriaService.desativarPessoa(id)
      setPessoas((prev) => prev.filter((p) => p.id !== id))
      toast.success('Pessoa removida')
    } catch {
      toast.error('Erro ao remover pessoa')
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-6 h-14 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <Brain size={15} className="text-text-muted" />
          <span className="text-sm font-medium text-text-primary">Memória</span>
        </div>

        {aba === 'pessoas' && (
          <Button
            size="sm"
            icon={<Plus size={13} />}
            onClick={abrirModalNovaPessoa}
          >
            Nova pessoa
          </Button>
        )}
      </div>

      {/* Abas */}
      <div className="shrink-0 flex border-b border-surface-border px-6">
        {(['memorias', 'pessoas'] as Aba[]).map((a) => (
          <button
            key={a}
            onClick={() => setAba(a)}
            className={cn(
              'flex items-center gap-1.5 h-10 px-1 mr-4 text-sm border-b-2 transition-colors cursor-pointer',
              aba === a
                ? 'border-accent text-text-primary font-medium'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            )}
          >
            {a === 'memorias' ? (
              <>
                <Brain size={13} />
                Fatos
              </>
            ) : (
              <>
                <Users size={13} />
                Pessoas
              </>
            )}
          </button>
        ))}
      </div>

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto p-6">
        {carregando ? (
          <div className="text-sm text-text-muted">Carregando...</div>
        ) : aba === 'memorias' ? (
          <MemoriasLista memorias={memorias} onDeletar={deletarMemoria} />
        ) : (
          <PessoasLista
            pessoas={pessoas}
            onDeletar={deletarPessoa}
            onEditar={abrirModalEditarPessoa}
          />
        )}
      </div>

      {/* Modal de pessoa */}
      {modalPessoa && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div
            className="w-full max-w-md rounded-xl border border-surface-border bg-surface-raised"
            style={{ boxShadow: '0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)' }}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
              <h3 className="text-sm font-semibold">
                {pessoaEditando ? 'Editar pessoa' : 'Nova pessoa'}
              </h3>
              <button
                onClick={() => setModalPessoa(false)}
                className="text-text-muted hover:text-text-primary transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <Input
                label="Nome"
                value={formPessoa.nome}
                onChange={(e) => setFormPessoa((p) => ({ ...p, nome: e.target.value }))}
                placeholder="Nome da pessoa"
                required
              />
              <Input
                label="Relação"
                value={formPessoa.relacao}
                onChange={(e) => setFormPessoa((p) => ({ ...p, relacao: e.target.value }))}
                placeholder="Amigo, colega, familiar..."
              />
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-text-secondary">Notas</label>
                <textarea
                  value={formPessoa.notas}
                  onChange={(e) => setFormPessoa((p) => ({ ...p, notas: e.target.value }))}
                  placeholder="Informações relevantes sobre essa pessoa..."
                  rows={3}
                  className="w-full rounded px-3 py-2.5 bg-surface-raised border border-surface-border text-sm text-text-primary placeholder:text-text-faint resize-none focus:outline-none focus:border-accent focus:shadow-glow transition-all"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 px-5 py-4 border-t border-surface-border">
              <Button variant="ghost" onClick={() => setModalPessoa(false)}>
                Cancelar
              </Button>
              <Button loading={salvando} onClick={salvarPessoa}>
                Salvar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MemoriasLista({
  memorias,
  onDeletar,
}: {
  memorias: Memoria[]
  onDeletar: (id: string) => void
}) {
  if (memorias.length === 0) {
    return (
      <div className="text-sm text-text-muted">
        Nenhuma memória ainda. Converse com o Jarvis e ele aprenderá sobre você automaticamente.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {memorias.map((m) => (
        <div
          key={m.id}
          className="group flex items-start gap-3 px-4 py-3 rounded-lg border border-surface-border bg-surface-raised hover:border-surface-muted transition-colors"
        >
          <div className="flex-1 min-w-0">
            <p className="text-sm text-text-primary leading-relaxed">{m.conteudo}</p>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="default">{m.categoria}</Badge>
              <span className="text-2xs text-text-faint">
                {formatarDataRelativa(m.criado_em)}
              </span>
            </div>
          </div>
          <button
            onClick={() => onDeletar(m.id)}
            className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded text-text-faint hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}

function PessoasLista({
  pessoas,
  onDeletar,
  onEditar,
}: {
  pessoas: Pessoa[]
  onDeletar: (id: string) => void
  onEditar: (p: Pessoa) => void
}) {
  if (pessoas.length === 0) {
    return (
      <div className="text-sm text-text-muted">
        Nenhuma pessoa cadastrada ainda.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {pessoas.map((p) => (
        <div
          key={p.id}
          className="group flex items-center gap-4 px-4 py-3 rounded-lg border border-surface-border bg-surface-raised hover:border-surface-muted transition-colors cursor-pointer"
          onClick={() => onEditar(p)}
        >
          <div className="w-8 h-8 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
            <span className="text-accent text-xs font-semibold">
              {p.nome.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary">{p.nome}</p>
            {p.relacao && (
              <p className="text-xs text-text-muted">{p.relacao}</p>
            )}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDeletar(p.id)
            }}
            className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded text-text-faint hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}

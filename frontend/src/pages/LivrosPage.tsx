import { useState, useEffect, useRef } from 'react'
import {
  BookOpen, Upload, ChevronLeft, ChevronRight, Trash2,
  GraduationCap, RotateCcw, X, CheckCircle2, BookMarked,
} from 'lucide-react'
import { toast } from 'sonner'
import { livrosService, type Livro, type LeituraResponse } from '@/services/livrosService'
import { cn } from '@/utils/cn'

// ─── Upload modal ─────────────────────────────────────────────────────────────

function ModalUpload({ onClose, onUpload }: { onClose: () => void; onUpload: (l: Livro) => void }) {
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [titulo, setTitulo] = useState('')
  const [autor, setAutor] = useState('')
  const [palavrasPorChunk, setPalavrasPorChunk] = useState(300)
  const [enviando, setEnviando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f && f.name.endsWith('.pdf')) {
      setArquivo(f)
      if (!titulo) setTitulo(f.name.replace(/\.pdf$/i, ''))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!arquivo || !titulo.trim()) return
    setEnviando(true)
    try {
      const livro = await livrosService.upload(arquivo, titulo.trim(), autor.trim(), palavrasPorChunk)
      toast.success(`"${livro.titulo}" processado — ${livro.total_chunks} trechos`)
      onUpload(livro)
    } catch {
      toast.error('Erro ao processar PDF')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div className="w-full max-w-md bg-surface-raised rounded-xl border border-surface-border shadow-float">
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
          <span className="text-sm font-semibold text-text-primary">Adicionar livro</span>
          <button onClick={onClose} className="text-text-faint hover:text-text-primary cursor-pointer transition-colors">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Área de drop */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => inputRef.current?.click()}
            className={cn(
              'border-2 border-dashed rounded-lg p-6 flex flex-col items-center gap-2 cursor-pointer transition-colors',
              arquivo
                ? 'border-accent/50 bg-accent/5'
                : 'border-surface-border hover:border-accent/30 hover:bg-surface-overlay'
            )}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) {
                  setArquivo(f)
                  if (!titulo) setTitulo(f.name.replace(/\.pdf$/i, ''))
                }
              }}
            />
            <Upload size={20} className={arquivo ? 'text-accent' : 'text-text-faint'} />
            {arquivo ? (
              <span className="text-sm text-accent font-medium truncate max-w-[240px]">{arquivo.name}</span>
            ) : (
              <span className="text-sm text-text-faint">Arraste um PDF ou clique para selecionar</span>
            )}
          </div>

          {/* Título */}
          <div>
            <label className="text-xs text-text-muted block mb-1">Título *</label>
            <input
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Nome do livro"
              required
              className="w-full h-9 px-3 rounded border border-surface-border bg-surface text-text-primary text-sm placeholder:text-text-faint focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Autor */}
          <div>
            <label className="text-xs text-text-muted block mb-1">Autor</label>
            <input
              value={autor}
              onChange={(e) => setAutor(e.target.value)}
              placeholder="Opcional"
              className="w-full h-9 px-3 rounded border border-surface-border bg-surface text-text-primary text-sm placeholder:text-text-faint focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Tamanho do trecho */}
          <div>
            <label className="text-xs text-text-muted block mb-1">
              Palavras por trecho — <span className="text-text-secondary font-mono">{palavrasPorChunk}</span>
              <span className="text-text-faint ml-1">
                (~{Math.round(palavrasPorChunk / 200)} min de leitura)
              </span>
            </label>
            <input
              type="range"
              min={100}
              max={800}
              step={50}
              value={palavrasPorChunk}
              onChange={(e) => setPalavrasPorChunk(Number(e.target.value))}
              className="w-full accent-accent"
            />
            <div className="flex justify-between text-2xs text-text-faint mt-1">
              <span>100 — curto</span>
              <span>800 — longo</span>
            </div>
          </div>

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 h-9 rounded border border-surface-border text-sm text-text-secondary hover:bg-surface-overlay transition-colors cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!arquivo || !titulo.trim() || enviando}
              className="flex-1 h-9 rounded bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {enviando ? 'Processando...' : 'Adicionar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Card de livro ─────────────────────────────────────────────────────────────

function CardLivro({
  livro,
  onLer,
  onDeletar,
}: {
  livro: Livro
  onLer: () => void
  onDeletar: () => void
}) {
  const progresso = livro.progresso
  const porcentagem = progresso
    ? Math.round(((progresso.chunk_atual - 1) / livro.total_chunks) * 100)
    : 0
  const concluido = progresso?.flg_concluido ?? false

  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised p-4 flex flex-col gap-3 hover:border-accent/30 transition-colors">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-md bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
          {concluido
            ? <CheckCircle2 size={16} className="text-accent" />
            : <BookOpen size={16} className="text-accent" />
          }
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary leading-tight truncate">{livro.titulo}</p>
          {livro.autor && (
            <p className="text-xs text-text-faint mt-0.5 truncate">{livro.autor}</p>
          )}
          <p className="text-2xs text-text-faint mt-1 font-mono">
            {livro.total_chunks} trechos · {livro.total_paginas} pág.
          </p>
        </div>
        <button
          onClick={onDeletar}
          className="text-text-faint hover:text-red-400 transition-colors cursor-pointer p-1 shrink-0"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Barra de progresso */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-2xs text-text-faint">
            {concluido ? 'Concluído' : `Trecho ${progresso?.chunk_atual ?? 1} de ${livro.total_chunks}`}
          </span>
          <span className="text-2xs text-text-faint font-mono">{concluido ? 100 : porcentagem}%</span>
        </div>
        <div className="h-1 bg-surface-border rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all"
            style={{ width: `${concluido ? 100 : porcentagem}%` }}
          />
        </div>
      </div>

      <button
        onClick={onLer}
        disabled={concluido}
        className={cn(
          'w-full h-8 rounded text-xs font-medium transition-colors cursor-pointer',
          concluido
            ? 'bg-surface-overlay text-text-faint cursor-not-allowed'
            : 'bg-accent/10 hover:bg-accent/20 text-accent border border-accent/20'
        )}
      >
        {concluido ? 'Leitura concluída' : porcentagem === 0 ? 'Começar a ler' : 'Continuar leitura'}
      </button>
    </div>
  )
}

// ─── Leitor ───────────────────────────────────────────────────────────────────

function Leitor({
  livro,
  onFechar,
  onProgressoAtualizado,
}: {
  livro: Livro
  onFechar: () => void
  onProgressoAtualizado: (l: Livro) => void
}) {
  const [leitura, setLeitura] = useState<LeituraResponse | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [modoEstudo, setModoEstudo] = useState(livro.progresso?.flg_modo_estudo ?? false)
  const [tamanhoChunk, setTamanhoChunk] = useState(livro.progresso?.tamanho_chunk ?? 300)
  const [mostrarConfig, setMostrarConfig] = useState(false)
  const topoRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    carregarProximo()
  }, [])

  async function carregarProximo() {
    setCarregando(true)
    try {
      const r = await livrosService.lerProximo(livro.id)
      setLeitura(r)
      topoRef.current?.scrollIntoView({ behavior: 'smooth' })
    } catch {
      toast.error('Erro ao carregar trecho')
    } finally {
      setCarregando(false)
    }
  }

  async function carregarAnterior() {
    setCarregando(true)
    try {
      const r = await livrosService.lerAnterior(livro.id)
      setLeitura(r)
      topoRef.current?.scrollIntoView({ behavior: 'smooth' })
    } catch {
      toast.error('Erro ao carregar trecho anterior')
    } finally {
      setCarregando(false)
    }
  }

  async function salvarConfig() {
    try {
      await livrosService.atualizarProgresso(livro.id, {
        flg_modo_estudo: modoEstudo,
        tamanho_chunk: tamanhoChunk,
      })
      toast.success('Configurações salvas')
      setMostrarConfig(false)
    } catch {
      toast.error('Erro ao salvar configurações')
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-surface flex flex-col">
      {/* Header */}
      <div ref={topoRef} className="shrink-0 flex items-center justify-between px-4 h-14 border-b border-surface-border">
        <button onClick={onFechar} className="flex items-center gap-2 text-text-secondary hover:text-text-primary cursor-pointer transition-colors">
          <ChevronLeft size={16} />
          <span className="text-sm">Biblioteca</span>
        </button>
        <div className="flex-1 mx-4 text-center">
          <p className="text-xs font-medium text-text-primary truncate">{livro.titulo}</p>
          {leitura && (
            <p className="text-2xs text-text-faint font-mono">
              {leitura.chunk_atual}/{leitura.total_chunks} · {leitura.porcentagem}%
            </p>
          )}
        </div>
        <button
          onClick={() => setMostrarConfig((v) => !v)}
          className="text-text-faint hover:text-text-primary cursor-pointer transition-colors p-1"
        >
          <BookMarked size={16} />
        </button>
      </div>

      {/* Barra de progresso fina */}
      {leitura && (
        <div className="h-0.5 bg-surface-border shrink-0">
          <div
            className="h-full bg-accent transition-all duration-500"
            style={{ width: `${leitura.porcentagem}%` }}
          />
        </div>
      )}

      {/* Config inline */}
      {mostrarConfig && (
        <div className="shrink-0 border-b border-surface-border bg-surface-raised px-4 py-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">Modo estudo (perguntas ao fim do capítulo)</span>
            <button
              onClick={() => setModoEstudo((v) => !v)}
              className={cn(
                'relative inline-flex items-center w-9 h-5 rounded-full transition-colors cursor-pointer shrink-0',
                modoEstudo ? 'bg-accent' : 'bg-surface-border'
              )}
            >
              <span className={cn(
                'inline-block w-3.5 h-3.5 rounded-full bg-white shadow transition-transform duration-200',
                modoEstudo ? 'translate-x-4' : 'translate-x-0.5'
              )} />
            </button>
          </div>
          <div>
            <label className="text-xs text-text-muted block mb-1">
              Palavras por trecho — <span className="font-mono text-text-secondary">{tamanhoChunk}</span>
            </label>
            <input
              type="range" min={100} max={800} step={50}
              value={tamanhoChunk}
              onChange={(e) => setTamanhoChunk(Number(e.target.value))}
              className="w-full accent-accent"
            />
          </div>
          <button
            onClick={salvarConfig}
            className="h-7 px-3 rounded bg-accent/10 hover:bg-accent/20 text-accent text-xs font-medium border border-accent/20 cursor-pointer transition-colors"
          >
            Salvar
          </button>
        </div>
      )}

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto">
        {carregando ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-text-faint text-sm">Carregando trecho...</div>
          </div>
        ) : leitura ? (
          <div className="max-w-2xl mx-auto px-5 py-8">
            {/* Capítulo */}
            {leitura.chunk.capitulo && (
              <p className="text-xs font-semibold text-accent uppercase tracking-wider mb-4">
                {leitura.chunk.capitulo}
              </p>
            )}

            {/* Texto principal */}
            <div className="prose-jarvis leading-relaxed whitespace-pre-wrap text-text-primary text-base">
              {leitura.chunk.conteudo}
            </div>

            <p className="text-2xs text-text-faint font-mono mt-4">
              {leitura.chunk.total_palavras} palavras
            </p>

            {/* Resumo do capítulo */}
            {leitura.resumo_capitulo && (
              <div className="mt-6 p-4 rounded-lg border border-accent/20 bg-accent/5">
                <p className="text-xs font-semibold text-accent mb-2 flex items-center gap-1.5">
                  <RotateCcw size={12} /> Resumo do capítulo
                </p>
                <p className="text-sm text-text-secondary leading-relaxed">{leitura.resumo_capitulo}</p>
              </div>
            )}

            {/* Perguntas de estudo */}
            {leitura.perguntas_estudo && leitura.perguntas_estudo.length > 0 && (
              <div className="mt-4 p-4 rounded-lg border border-surface-border bg-surface-raised">
                <p className="text-xs font-semibold text-text-secondary mb-3 flex items-center gap-1.5">
                  <GraduationCap size={12} /> Perguntas de fixação
                </p>
                <ul className="space-y-2">
                  {leitura.perguntas_estudo.map((q, i) => (
                    <li key={i} className="text-sm text-text-secondary">{q}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Livro concluído */}
            {leitura.livro_concluido && (
              <div className="mt-6 p-4 rounded-lg border border-green-500/20 bg-green-500/5 text-center">
                <CheckCircle2 size={24} className="text-green-400 mx-auto mb-2" />
                <p className="text-sm font-semibold text-green-400">Livro concluído!</p>
                <p className="text-xs text-text-faint mt-1">O Jarvis salvou este livro na sua memória.</p>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Navegação */}
      {leitura && !leitura.livro_concluido && (
        <div className="shrink-0 flex gap-3 px-4 py-3 border-t border-surface-border">
          <button
            onClick={carregarAnterior}
            disabled={carregando || leitura.chunk_atual <= 1}
            className="flex items-center gap-2 h-10 px-4 rounded border border-surface-border text-sm text-text-secondary hover:text-text-primary hover:bg-surface-overlay transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} /> Anterior
          </button>
          <button
            onClick={carregarProximo}
            disabled={carregando}
            className="flex-1 flex items-center justify-center gap-2 h-10 rounded bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
          >
            Próximo trecho <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export function LivrosPage() {
  const [livros, setLivros] = useState<Livro[]>([])
  const [carregando, setCarregando] = useState(true)
  const [modalAberto, setModalAberto] = useState(false)
  const [livroLendo, setLivroLendo] = useState<Livro | null>(null)

  useEffect(() => {
    carregarLivros()
  }, [])

  async function carregarLivros() {
    try {
      const lista = await livrosService.listar()
      setLivros(lista)
    } catch {
      toast.error('Erro ao carregar biblioteca')
    } finally {
      setCarregando(false)
    }
  }

  async function handleDeletar(id: string, titulo: string) {
    if (!confirm(`Remover "${titulo}" da biblioteca?`)) return
    try {
      await livrosService.deletar(id)
      setLivros((prev) => prev.filter((l) => l.id !== id))
      toast.success('Livro removido')
    } catch {
      toast.error('Erro ao remover livro')
    }
  }

  function handleLivroAdicionado(livro: Livro) {
    setLivros((prev) => [livro, ...prev])
    setModalAberto(false)
  }

  if (livroLendo) {
    return (
      <Leitor
        livro={livroLendo}
        onFechar={() => {
          setLivroLendo(null)
          carregarLivros() // recarrega para atualizar progresso
        }}
        onProgressoAtualizado={(l) => {
          setLivros((prev) => prev.map((x) => (x.id === l.id ? l : x)))
        }}
      />
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-6 h-14 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <BookOpen size={15} className="text-text-muted" />
          <span className="text-sm font-medium text-text-primary">Biblioteca</span>
        </div>
        <button
          onClick={() => setModalAberto(true)}
          className="flex items-center gap-1.5 h-7 px-3 rounded bg-accent/10 hover:bg-accent/20 text-accent text-xs font-medium border border-accent/20 cursor-pointer transition-colors"
        >
          <Upload size={12} /> Adicionar PDF
        </button>
      </div>

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto p-6">
        {carregando ? (
          <div className="flex items-center justify-center h-32">
            <span className="text-text-faint text-sm">Carregando...</span>
          </div>
        ) : livros.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3 text-center">
            <BookOpen size={32} className="text-text-faint" />
            <p className="text-sm text-text-secondary font-medium">Biblioteca vazia</p>
            <p className="text-xs text-text-faint max-w-xs">
              Adicione um PDF e o Jarvis vai dividir em trechos para você ler no seu ritmo.
            </p>
            <button
              onClick={() => setModalAberto(true)}
              className="mt-2 h-8 px-4 rounded bg-accent/10 hover:bg-accent/20 text-accent text-sm border border-accent/20 cursor-pointer transition-colors"
            >
              Adicionar primeiro livro
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
            {livros.map((livro) => (
              <CardLivro
                key={livro.id}
                livro={livro}
                onLer={() => setLivroLendo(livro)}
                onDeletar={() => handleDeletar(livro.id, livro.titulo)}
              />
            ))}
          </div>
        )}
      </div>

      {modalAberto && (
        <ModalUpload
          onClose={() => setModalAberto(false)}
          onUpload={handleLivroAdicionado}
        />
      )}
    </div>
  )
}

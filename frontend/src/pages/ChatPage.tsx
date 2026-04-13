import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import { toast } from 'sonner'
import { MensagemItem } from '@/components/chat/MensagemItem'
import { ChatInput } from '@/components/chat/ChatInput'
import { chatService } from '@/services/chatService'
import { useAppStore } from '@/store/useAppStore'
import type { Mensagem } from '@/types'

const PLACEHOLDER_STREAMING: Mensagem = {
  id: '__streaming__',
  papel: 'assistant',
  conteudo: '',
  modelo_usado: null,
  tokens_entrada: null,
  tokens_saida: null,
  criado_em: new Date().toISOString(),
}

export function ChatPage() {
  const { idConversa } = useParams<{ idConversa: string }>()
  const navigate = useNavigate()
  const { conversaAtiva, setConversaAtiva, setStreamingAtivo } = useAppStore()
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [carregando, setCarregando] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (idConversa) {
      carregarMensagens(idConversa)
    }
  }, [idConversa])

  // Auto-scroll ao chegar nova mensagem ou chunk
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensagens])

  async function carregarMensagens(id: string) {
    setCarregando(true)
    try {
      const lista = await chatService.listarMensagens(id)
      setMensagens(lista)
    } catch {
      toast.error('Erro ao carregar mensagens')
    } finally {
      setCarregando(false)
    }
  }

  const enviarMensagem = useCallback(
    async (conteudo: string) => {
      if (!idConversa || streaming) return

      // 1. Adicionar mensagem do usuário imediatamente
      const msgUsuario: Mensagem = {
        id: crypto.randomUUID(),
        papel: 'user',
        conteudo,
        modelo_usado: null,
        tokens_entrada: null,
        tokens_saida: null,
        criado_em: new Date().toISOString(),
      }
      setMensagens((prev) => [...prev, msgUsuario, { ...PLACEHOLDER_STREAMING }])
      setStreaming(true)
      setStreamingAtivo(true)

      // 2. Consumir SSE
      await chatService.enviarMensagemStream(
        idConversa,
        conteudo,
        // onChunk — acumula texto no placeholder
        (chunk) => {
          setMensagens((prev) =>
            prev.map((m) =>
              m.id === '__streaming__' ? { ...m, conteudo: m.conteudo + chunk } : m
            )
          )
        },
        // onDone — recarrega mensagens do banco (com tokens e modelo preenchidos)
        async () => {
          setStreaming(false)
          setStreamingAtivo(false)
          const lista = await chatService.listarMensagens(idConversa)
          setMensagens(lista)
          // Atualiza título da conversa na sidebar se for a primeira mensagem
          if (mensagens.length === 0) {
            const conversas = await chatService.listarConversas()
            const atualizada = conversas.find((c) => c.id === idConversa)
            if (atualizada) setConversaAtiva(atualizada)
          }
        },
        // onError
        (erro) => {
          setStreaming(false)
          setStreamingAtivo(false)
          setMensagens((prev) => prev.filter((m) => m.id !== '__streaming__'))
          toast.error(erro)
        }
      )
    },
    [idConversa, streaming, mensagens.length, setConversaAtiva, setStreamingAtivo]
  )

  // Estado inicial — sem conversa selecionada
  if (!idConversa) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center px-4">
        <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
          <span className="text-accent text-xl font-bold">J</span>
        </div>
        <h2 className="text-lg font-semibold text-text-primary mb-2">Olá, sou o Jarvis</h2>
        <p className="text-sm text-text-muted max-w-xs">
          Selecione uma conversa na sidebar ou crie uma nova para começar.
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header mínimo */}
      <div className="shrink-0 flex items-center px-4 md:px-6 h-14 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <MessageSquare size={15} className="text-text-muted" />
          <span className="text-sm font-medium text-text-primary">
            {conversaAtiva?.titulo || 'Nova conversa'}
          </span>
        </div>
      </div>

      {/* Mensagens */}
      <div className="flex-1 overflow-y-auto px-3 md:px-6 py-4 md:py-6 space-y-4 md:space-y-6">
        {carregando ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm text-text-muted">Carregando...</span>
          </div>
        ) : mensagens.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm text-text-muted">Envie uma mensagem para começar</span>
          </div>
        ) : (
          mensagens.map((msg) => (
            <MensagemItem
              key={msg.id}
              mensagem={msg}
              streaming={msg.id === '__streaming__' && streaming}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-surface-border">
        <ChatInput onEnviar={enviarMensagem} desabilitado={streaming} />
      </div>
    </div>
  )
}

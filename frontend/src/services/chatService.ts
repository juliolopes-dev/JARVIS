import { api } from './api'
import type { Conversa, Mensagem } from '@/types'

export const chatService = {
  async criarConversa(titulo?: string): Promise<Conversa> {
    const res = await api.post<Conversa>('/chat/conversas', { titulo })
    return res.data
  },

  async listarConversas(pagina = 1): Promise<Conversa[]> {
    const res = await api.get<Conversa[]>('/chat/conversas', {
      params: { pagina, por_pagina: 30 },
    })
    return res.data
  },

  async listarMensagens(idConversa: string, pagina = 1): Promise<Mensagem[]> {
    const res = await api.get<Mensagem[]>(`/chat/conversas/${idConversa}/mensagens`, {
      params: { pagina, por_pagina: 50 },
    })
    return res.data
  },

  async arquivarConversa(idConversa: string): Promise<void> {
    await api.delete(`/chat/conversas/${idConversa}`)
  },

  /**
   * Envia mensagem e retorna um ReadableStream SSE.
   * O consumidor itera os chunks e atualiza o estado em tempo real.
   */
  async enviarMensagemStream(
    idConversa: string,
    conteudo: string,
    onChunk: (texto: string) => void,
    onDone: () => void,
    onError: (erro: string) => void
  ): Promise<void> {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`/api/chat/conversas/${idConversa}/mensagens`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ conteudo }),
    })

    if (!response.ok) {
      const erro = await response.json().catch(() => ({ error: 'Erro desconhecido' }))
      onError(erro.error || 'Erro ao enviar mensagem')
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      onError('Streaming não suportado')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dado = line.slice(6)
          if (dado === '[DONE]') {
            onDone()
            return
          }
          onChunk(dado)
        }
      }
    }

    onDone()
  },
}

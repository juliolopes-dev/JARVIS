import { api } from './api'

export interface Progresso {
  chunk_atual: number
  tamanho_chunk: number
  flg_modo_estudo: boolean
  flg_concluido: boolean
  dat_ultimo_acesso: string | null
  dat_conclusao: string | null
}

export interface Livro {
  id: string
  titulo: string
  autor: string | null
  total_paginas: number
  total_chunks: number
  dat_upload: string
  progresso: Progresso | null
}

export interface Chunk {
  id: string
  numero: number
  capitulo: string | null
  conteudo: string
  total_palavras: number
}

export interface LeituraResponse {
  livro_id: string
  titulo_livro: string
  chunk: Chunk
  chunk_atual: number
  total_chunks: number
  porcentagem: number
  capitulo_concluido: boolean
  livro_concluido: boolean
  resumo_capitulo: string | null
  perguntas_estudo: string[] | null
}

export const livrosService = {
  async listar(): Promise<Livro[]> {
    const { data } = await api.get('/livros/')
    return data
  },

  async upload(
    arquivo: File,
    titulo: string,
    autor: string,
    palavrasPorChunk: number,
  ): Promise<Livro> {
    const form = new FormData()
    form.append('arquivo', arquivo)
    form.append('titulo', titulo)
    if (autor) form.append('autor', autor)
    form.append('palavras_por_chunk', String(palavrasPorChunk))
    const { data } = await api.post('/livros/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async deletar(id: string): Promise<void> {
    await api.delete(`/livros/${id}`)
  },

  async lerProximo(id: string): Promise<LeituraResponse> {
    const { data } = await api.get(`/livros/${id}/ler/proximo`)
    return data
  },

  async lerAnterior(id: string): Promise<LeituraResponse> {
    const { data } = await api.get(`/livros/${id}/ler/anterior`)
    return data
  },

  async atualizarProgresso(
    id: string,
    dados: { tamanho_chunk?: number; flg_modo_estudo?: boolean },
  ): Promise<Progresso> {
    const { data } = await api.patch(`/livros/${id}/progresso`, dados)
    return data
  },
}

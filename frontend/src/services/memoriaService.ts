import { api } from './api'
import type { Memoria, Pessoa } from '@/types'

export const memoriaService = {
  async listarMemorias(categoria?: string, pagina = 1): Promise<Memoria[]> {
    const res = await api.get<Memoria[]>('/memoria', {
      params: { categoria, pagina, por_pagina: 30 },
    })
    return res.data
  },

  async desativarMemoria(id: string): Promise<void> {
    await api.delete(`/memoria/${id}`)
  },

  async listarPessoas(): Promise<Pessoa[]> {
    const res = await api.get<Pessoa[]>('/memoria/pessoas')
    return res.data
  },

  async criarPessoa(dados: { nome: string; relacao?: string; notas?: string }): Promise<Pessoa> {
    const res = await api.post<Pessoa>('/memoria/pessoas', dados)
    return res.data
  },

  async atualizarPessoa(
    id: string,
    dados: { nome?: string; relacao?: string; notas?: string }
  ): Promise<Pessoa> {
    const res = await api.put<Pessoa>(`/memoria/pessoas/${id}`, dados)
    return res.data
  },

  async desativarPessoa(id: string): Promise<void> {
    await api.delete(`/memoria/pessoas/${id}`)
  },
}

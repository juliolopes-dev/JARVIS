import { api } from './api'

export interface Lista {
  id: string
  nome: string
  cor: string
  icone: string
  ordem: number
  criado_em: string
  total_tarefas: number
  total_concluidas: number
}

export interface ListaCreate {
  nome: string
  cor?: string
  icone?: string
}

export interface Tarefa {
  id: string
  id_lista: string | null
  titulo: string
  descricao: string | null
  prioridade: 'baixa' | 'media' | 'alta' | 'urgente'
  dat_vencimento: string | null
  flg_concluida: boolean
  dat_concluida: string | null
  ordem: number
  criado_em: string
  atualizado_em: string
}

export interface TarefaCreate {
  titulo: string
  descricao?: string
  id_lista?: string
  prioridade?: string
  dat_vencimento?: string
}

export interface TarefaUpdate {
  titulo?: string
  descricao?: string
  id_lista?: string
  prioridade?: string
  dat_vencimento?: string | null
}

export const checklistService = {
  // Listas
  async listarListas(): Promise<Lista[]> {
    const { data } = await api.get('/checklist/listas')
    return data
  },

  async criarLista(dados: ListaCreate): Promise<Lista> {
    const { data } = await api.post('/checklist/listas', dados)
    return data
  },

  async atualizarLista(id: string, dados: Partial<ListaCreate>): Promise<Lista> {
    const { data } = await api.put(`/checklist/listas/${id}`, dados)
    return data
  },

  async deletarLista(id: string): Promise<void> {
    await api.delete(`/checklist/listas/${id}`)
  },

  // Tarefas
  async listarTarefas(idLista?: string, concluidas?: boolean): Promise<Tarefa[]> {
    const { data } = await api.get('/checklist/tarefas', {
      params: {
        id_lista: idLista,
        concluidas,
      },
    })
    return data
  },

  async criarTarefa(dados: TarefaCreate): Promise<Tarefa> {
    const { data } = await api.post('/checklist/tarefas', dados)
    return data
  },

  async concluirTarefa(id: string): Promise<Tarefa> {
    const { data } = await api.patch(`/checklist/tarefas/${id}/concluir`)
    return data
  },

  async atualizarTarefa(id: string, dados: TarefaUpdate): Promise<Tarefa> {
    const { data } = await api.put(`/checklist/tarefas/${id}`, dados)
    return data
  },

  async deletarTarefa(id: string): Promise<void> {
    await api.delete(`/checklist/tarefas/${id}`)
  },
}

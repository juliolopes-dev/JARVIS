import { api } from './api'

export interface TarefaAgendada {
  id: string
  descricao: string
  tipo: string
  cron_expressao: string | null
  parametros: Record<string, unknown> | null
  sts_tarefa: 'ativa' | 'pausada'
  dat_ultima_execucao: string | null
  dat_proxima_execucao: string | null
  criado_em: string
}

export interface TarefaAgendadaCreate {
  descricao: string
  cron_expressao: string
  parametros?: Record<string, unknown>
}

export interface TarefaAgendadaUpdate {
  descricao?: string
  cron_expressao?: string
  parametros?: Record<string, unknown>
  sts_tarefa?: 'ativa' | 'pausada'
}

export const tarefasAgendadasService = {
  async listar(): Promise<TarefaAgendada[]> {
    const { data } = await api.get('/tarefas-agendadas/')
    return data
  },

  async criar(dados: TarefaAgendadaCreate): Promise<TarefaAgendada> {
    const { data } = await api.post('/tarefas-agendadas/', dados)
    return data
  },

  async atualizar(id: string, dados: TarefaAgendadaUpdate): Promise<TarefaAgendada> {
    const { data } = await api.put(`/tarefas-agendadas/${id}`, dados)
    return data
  },

  async deletar(id: string): Promise<void> {
    await api.delete(`/tarefas-agendadas/${id}`)
  },

  async executarAgora(id: string): Promise<void> {
    await api.post(`/tarefas-agendadas/${id}/executar`)
  },
}

// ─── Helpers de cron → texto legivel ─────────────────────────────────────────

const DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

export function cronParaTexto(cron: string): string {
  const partes = cron.trim().split(/\s+/)
  if (partes.length !== 5) return cron

  const [minuto, hora, diaMes, mes, diaSemana] = partes
  const horario = `${hora.padStart(2, '0')}:${minuto.padStart(2, '0')}`

  // Todo dia
  if (diaMes === '*' && mes === '*' && diaSemana === '*') {
    if (hora === '*' && minuto === '0') return 'Toda hora exata'
    if (hora === '*') return `Todo minuto ${minuto}`
    return `Todo dia às ${horario}`
  }

  // Dia X do mês
  if (diaMes !== '*' && mes === '*' && diaSemana === '*') {
    return `Dia ${diaMes} de todo mês às ${horario}`
  }

  // Dia(s) da semana
  if (diaSemana !== '*' && diaMes === '*' && mes === '*') {
    const dias = diaSemana
      .split(',')
      .map((d) => DIAS_SEMANA[parseInt(d, 10)] ?? d)
      .join(', ')
    return `${dias} às ${horario}`
  }

  return cron
}

import { api } from './api'

export type PeriodoCusto = 'mes_atual' | 'mes_anterior' | 'ultimos_7_dias' | 'ultimos_30_dias'

export interface CustoPorModelo {
  modelo: string
  tokens_in: number
  tokens_out: number
  custo_usd: number
  custo_brl: number
  segundos_audio?: number
}

export interface CustoPorDia {
  dia: string
  custo_usd: number
  custo_brl: number
}

export interface ResumoCustos {
  periodo: PeriodoCusto
  dat_inicio: string
  dat_fim: string
  total_usd: number
  total_brl: number
  cotacao_usd_brl: number
  por_modelo: CustoPorModelo[]
  por_dia: CustoPorDia[]
}

export const custosService = {
  async obterResumo(periodo: PeriodoCusto = 'mes_atual'): Promise<ResumoCustos> {
    const res = await api.get<ResumoCustos>('/custos/resumo', { params: { periodo } })
    return res.data
  },
}

import { api } from './api'

export interface Configuracao {
  id: string
  modelo_preferido: string
  tema: string
  flg_briefing_diario: boolean
  horario_briefing: string // "HH:MM"
  flg_notificacoes: boolean
  criado_em: string
  atualizado_em: string
}

export interface ConfiguracaoUpdate {
  modelo_preferido?: string
  tema?: string
  flg_briefing_diario?: boolean
  horario_briefing?: string
  flg_notificacoes?: boolean
}

export const configService = {
  async obter(): Promise<Configuracao> {
    const { data } = await api.get('/config')
    return data
  },

  async atualizar(dados: ConfiguracaoUpdate): Promise<Configuracao> {
    const { data } = await api.put('/config', dados)
    return data
  },
}

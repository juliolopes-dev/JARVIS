import { api } from './api'

export interface Lembrete {
  id: string
  titulo: string
  descricao: string | null
  dat_lembrete: string
  sts_lembrete: 'pendente' | 'disparado' | 'cancelado'
  criado_em: string
}

export interface LembreteCreate {
  titulo: string
  descricao?: string
  dat_lembrete: string // ISO 8601
}

export const lembretesService = {
  async listar(apenasPendentes = false): Promise<Lembrete[]> {
    const { data } = await api.get('/lembretes', {
      params: { apenas_pendentes: apenasPendentes },
    })
    return data
  },

  async criar(dados: LembreteCreate): Promise<Lembrete> {
    const { data } = await api.post('/lembretes', dados)
    return data
  },

  async cancelar(id: string): Promise<void> {
    await api.delete(`/lembretes/${id}`)
  },

  // Web Push
  async obterVapidKey(): Promise<string> {
    const { data } = await api.get('/notificacoes/vapid-public-key')
    return data.public_key
  },

  async registrarSubscricao(subscription: PushSubscription, dispositivo?: string): Promise<void> {
    const json = subscription.toJSON()
    await api.post('/notificacoes/subscribe', {
      endpoint: json.endpoint,
      chave_p256dh: json.keys?.p256dh,
      chave_auth: json.keys?.auth,
      dispositivo,
    })
  },

  async removerSubscricao(endpoint: string): Promise<void> {
    await api.post('/notificacoes/unsubscribe', { endpoint })
  },
}

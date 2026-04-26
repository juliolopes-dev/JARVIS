import { api } from './api'
import type { WhatsAppQrCode, WhatsAppStatus } from '@/types'

export const whatsappService = {
  async status(): Promise<WhatsAppStatus> {
    const res = await api.get<WhatsAppStatus>('/whatsapp/status')
    return res.data
  },

  async qrcode(): Promise<WhatsAppQrCode> {
    const res = await api.get<WhatsAppQrCode>('/whatsapp/qrcode')
    return res.data
  },

  async reconectar(): Promise<{ sucesso: boolean; state: string; mensagem: string }> {
    const res = await api.post<{ sucesso: boolean; state: string; mensagem: string }>(
      '/whatsapp/reconectar',
    )
    return res.data
  },
}

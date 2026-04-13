import { api } from './api'
import type { TokenResponse, Usuario } from '@/types'

export const authService = {
  async login(email: string, senha: string): Promise<TokenResponse> {
    const res = await api.post<TokenResponse>('/auth/login', { email, senha })
    return res.data
  },

  async me(): Promise<Usuario> {
    const res = await api.get<Usuario>('/auth/me')
    return res.data
  },

  async alterarSenha(senhaAtual: string, novaSenha: string): Promise<void> {
    await api.put('/auth/senha', { senha_atual: senhaAtual, nova_senha: novaSenha })
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  isAutenticado(): boolean {
    return !!localStorage.getItem('access_token')
  },
}

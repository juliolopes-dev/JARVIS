export interface Conversa {
  id: string
  titulo: string | null
  flg_ativa: boolean
  criado_em: string
  atualizado_em: string
}

export interface Mensagem {
  id: string
  papel: 'user' | 'assistant' | 'system'
  conteudo: string
  modelo_usado: string | null
  tokens_entrada: number | null
  tokens_saida: number | null
  criado_em: string
}

export interface Memoria {
  id: string
  conteudo: string
  categoria: string
  criado_em: string
  atualizado_em: string
}

export interface Pessoa {
  id: string
  cod_pessoa: number
  nome: string
  relacao: string | null
  notas: string | null
  numero_whatsapp: string | null
  flg_monitorar_whatsapp: boolean
  flg_ativo: boolean
  criado_em: string
}

export interface WhatsAppStatus {
  enabled: boolean
  instancia: string
  conectado: boolean
  state: string
  profile_name: string | null
  profile_picture_url: string | null
  mensagens_hoje: number
  ultima_mensagem_em: string | null
  contatos_monitorados: number
}

export interface WhatsAppQrCode {
  qrcode_base64: string | null
  code: string | null
  state: string
}

export interface Evento {
  id: string
  dat_ocorreu: string
  resumo: string
  categoria: string
  lojas: string[] | null
  pessoas_envolvidas: string[] | null
  metadados: Record<string, unknown> | null
  flg_ativo: boolean
  criado_em: string
}

export interface Usuario {
  id: string
  cod_usuario: number
  nome: string
  email: string
  flg_ativo: boolean
  criado_em: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

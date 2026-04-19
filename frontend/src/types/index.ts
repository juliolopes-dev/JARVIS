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
  flg_ativo: boolean
  criado_em: string
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

import ReactMarkdown from 'react-markdown'
import { cn } from '@/utils/cn'
import { formatarDataMensagem } from '@/utils/formatDate'
import type { Mensagem } from '@/types'

interface MensagemItemProps {
  mensagem: Mensagem
  streaming?: boolean
}

export function MensagemItem({ mensagem, streaming = false }: MensagemItemProps) {
  const isUser = mensagem.papel === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%]">
          <div
            className="px-4 py-3 rounded-[10px_10px_4px_10px] text-md text-text-primary"
            style={{
              background: 'var(--color-accent-faint)',
              border: '1px solid rgba(var(--color-accent-rgb), 0.25)',
            }}
          >
            <p className="whitespace-pre-wrap leading-relaxed">{mensagem.conteudo}</p>
          </div>
          <div className="flex justify-end mt-1">
            <span className="text-2xs text-text-faint">
              {formatarDataMensagem(mensagem.criado_em)}
            </span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      {/* Avatar Jarvis */}
      <div className="w-7 h-7 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-accent text-2xs font-bold">J</span>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium text-text-secondary">Jarvis</span>
          {mensagem.modelo_usado && (
            <span className="text-2xs text-text-faint font-mono">{mensagem.modelo_usado}</span>
          )}
        </div>

        <div
          className={cn(
            'prose-jarvis',
            streaming && 'streaming-cursor'
          )}
        >
          {mensagem.conteudo ? (
            <ReactMarkdown>{mensagem.conteudo}</ReactMarkdown>
          ) : (
            <span className="text-text-muted text-sm italic">Pensando...</span>
          )}
        </div>

        {!streaming && (
          <div className="flex items-center gap-3 mt-2">
            <span className="text-2xs text-text-faint">
              {formatarDataMensagem(mensagem.criado_em)}
            </span>
            {mensagem.tokens_entrada != null && mensagem.tokens_saida != null && (
              <span className="text-2xs text-text-faint font-mono">
                {mensagem.tokens_entrada + mensagem.tokens_saida} tokens
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

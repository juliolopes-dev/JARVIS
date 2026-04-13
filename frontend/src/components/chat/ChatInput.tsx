import { useState, useRef, useEffect } from 'react'
import { ArrowUp } from 'lucide-react'
import { cn } from '@/utils/cn'

interface ChatInputProps {
  onEnviar: (conteudo: string) => void
  desabilitado?: boolean
  placeholder?: string
}

export function ChatInput({ onEnviar, desabilitado = false, placeholder }: ChatInputProps) {
  const [texto, setTexto] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize do textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`
  }, [texto])

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar()
    }
  }

  function enviar() {
    const trimmed = texto.trim()
    if (!trimmed || desabilitado) return
    onEnviar(trimmed)
    setTexto('')
  }

  const podeEnviar = texto.trim().length > 0 && !desabilitado

  return (
    <div className="relative flex items-end gap-2 px-4 py-4">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? 'Mensagem para o Jarvis...'}
          disabled={desabilitado}
          rows={1}
          className={cn(
            'w-full rounded-lg px-4 py-3 pr-12 resize-none',
            'bg-surface-raised border border-surface-border',
            'text-md text-text-primary placeholder:text-text-faint',
            'transition-all duration-150 leading-relaxed',
            'focus:outline-none focus:border-accent focus:shadow-glow',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'max-h-[200px] overflow-y-auto'
          )}
        />
        <button
          onClick={enviar}
          disabled={!podeEnviar}
          className={cn(
            'absolute right-3 bottom-3 w-7 h-7 rounded flex items-center justify-center',
            'transition-all duration-150 cursor-pointer',
            podeEnviar
              ? 'bg-accent hover:bg-accent-hover text-white'
              : 'bg-surface-border text-text-faint cursor-not-allowed'
          )}
        >
          <ArrowUp size={14} />
        </button>
      </div>
    </div>
  )
}

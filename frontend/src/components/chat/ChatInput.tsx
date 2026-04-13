import { useState, useRef, useEffect, useCallback } from 'react'
import { ArrowUp, Mic, Square } from 'lucide-react'
import { cn } from '@/utils/cn'
import { chatService } from '@/services/chatService'
import { toast } from 'sonner'

interface ChatInputProps {
  onEnviar: (conteudo: string) => void
  desabilitado?: boolean
  placeholder?: string
}

export function ChatInput({ onEnviar, desabilitado = false, placeholder }: ChatInputProps) {
  const [texto, setTexto] = useState('')
  const [gravando, setGravando] = useState(false)
  const [transcrevendo, setTranscrevendo] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

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

  const iniciarGravacao = useCallback(async () => {
    if (gravando || desabilitado || transcrevendo) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunksRef.current = []

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4'

      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: mimeType })
        if (blob.size < 1000) return // gravação muito curta, ignora
        await transcreverEEnviar(blob, mimeType)
      }

      recorder.start()
      setGravando(true)
    } catch {
      toast.error('Microfone não disponível')
    }
  }, [gravando, desabilitado, transcrevendo])

  const pararGravacao = useCallback(() => {
    if (!gravando || !mediaRecorderRef.current) return
    mediaRecorderRef.current.stop()
    setGravando(false)
  }, [gravando])

  async function transcreverEEnviar(blob: Blob, mimeType: string) {
    setTranscrevendo(true)
    try {
      const ext = mimeType.includes('mp4') ? 'mp4' : 'webm'
      const texto = await chatService.transcreverAudio(blob, `audio.${ext}`)
      if (texto) {
        onEnviar(texto)
      } else {
        toast.error('Não consegui entender o áudio')
      }
    } catch {
      toast.error('Erro ao transcrever áudio')
    } finally {
      setTranscrevendo(false)
    }
  }

  const podeEnviar = texto.trim().length > 0 && !desabilitado
  const ocupado = desabilitado || transcrevendo

  return (
    <div className="relative flex items-end gap-2 px-4 py-4">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            gravando
              ? 'Gravando... solte para enviar'
              : transcrevendo
                ? 'Transcrevendo...'
                : (placeholder ?? 'Mensagem para o Jarvis...')
          }
          disabled={ocupado || gravando}
          rows={1}
          className={cn(
            'w-full rounded-lg px-4 py-3 pr-24 resize-none',
            'bg-surface-raised border border-surface-border',
            'text-md text-text-primary placeholder:text-text-faint',
            'transition-all duration-150 leading-relaxed',
            'focus:outline-none focus:border-accent focus:shadow-glow',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'max-h-[200px] overflow-y-auto',
            gravando && 'border-red-500/50 placeholder:text-red-400/70'
          )}
        />

        {/* Botões dentro do textarea */}
        <div className="absolute right-3 bottom-3 flex items-center gap-1.5">
          {/* Botão microfone */}
          <button
            onMouseDown={iniciarGravacao}
            onMouseUp={pararGravacao}
            onTouchStart={(e) => { e.preventDefault(); iniciarGravacao() }}
            onTouchEnd={(e) => { e.preventDefault(); pararGravacao() }}
            disabled={ocupado}
            title={gravando ? 'Solte para enviar' : 'Segurar para gravar'}
            className={cn(
              'w-7 h-7 rounded flex items-center justify-center transition-all duration-150 cursor-pointer select-none',
              gravando
                ? 'bg-red-500 text-white animate-pulse'
                : ocupado
                  ? 'text-text-faint cursor-not-allowed'
                  : 'text-text-muted hover:text-text-primary hover:bg-surface-overlay'
            )}
          >
            {gravando ? <Square size={12} fill="white" /> : <Mic size={14} />}
          </button>

          {/* Botão enviar */}
          <button
            onClick={enviar}
            disabled={!podeEnviar}
            className={cn(
              'w-7 h-7 rounded flex items-center justify-center',
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
    </div>
  )
}

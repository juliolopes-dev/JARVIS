import { useEffect, useRef, useState } from 'react'
import { MessageCircle, RefreshCw, QrCode, Users, Activity, Clock } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { Badge } from '@/components/ui/Badge'
import { whatsappService } from '@/services/whatsappService'
import type { WhatsAppQrCode, WhatsAppStatus } from '@/types'
import { formatarDataRelativa } from '@/utils/formatDate'

export function WhatsAppPage() {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null)
  const [qrcode, setQrcode] = useState<WhatsAppQrCode | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [reconectando, setReconectando] = useState(false)
  const [mostrarQr, setMostrarQr] = useState(false)
  const intervaloRef = useRef<number | null>(null)

  useEffect(() => {
    carregarStatus()
    intervaloRef.current = window.setInterval(carregarStatus, 30_000)
    return () => {
      if (intervaloRef.current) window.clearInterval(intervaloRef.current)
    }
  }, [])

  // Quando entra em close/connecting → busca QR automaticamente
  useEffect(() => {
    if (status && status.enabled && status.state !== 'open' && mostrarQr) {
      buscarQrcode()
    }
  }, [status?.state, mostrarQr])

  async function carregarStatus() {
    try {
      const dados = await whatsappService.status()
      setStatus(dados)
    } catch {
      // silencioso (pode ser falha temporária da Evolution)
    } finally {
      setCarregando(false)
    }
  }

  async function buscarQrcode() {
    try {
      const dados = await whatsappService.qrcode()
      setQrcode(dados)
    } catch {
      toast.error('Não foi possível obter o QR Code')
    }
  }

  async function reconectar() {
    setReconectando(true)
    try {
      const r = await whatsappService.reconectar()
      if (r.sucesso) {
        toast.success('Reconexão solicitada')
        setMostrarQr(true)
        await buscarQrcode()
        await carregarStatus()
      } else {
        toast.error(r.mensagem || 'Falha ao reconectar')
      }
    } catch {
      toast.error('Erro ao reconectar')
    } finally {
      setReconectando(false)
    }
  }

  if (carregando) {
    return (
      <div className="h-full flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-6 h-14 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <MessageCircle size={15} className="text-text-muted" />
          <span className="text-sm font-medium text-text-primary">WhatsApp</span>
          {status && (
            <Badge variant={status.conectado ? 'default' : 'default'}>
              {labelEstado(status.state)}
            </Badge>
          )}
        </div>
        <Button
          size="sm"
          variant="ghost"
          icon={<RefreshCw size={13} />}
          onClick={carregarStatus}
        >
          Atualizar
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {!status?.enabled && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3">
            <div className="text-sm text-amber-400 font-medium mb-1">
              Integração desabilitada
            </div>
            <div className="text-xs text-text-muted">
              Defina <code className="text-2xs px-1.5 py-0.5 rounded bg-surface-overlay">WHATSAPP_ENABLED=true</code>{' '}
              nas variáveis do backend e reinicie o servidor.
            </div>
          </div>
        )}

        {status?.enabled && !status.conectado && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3">
            <div className="text-sm text-red-400 font-medium mb-2">
              Sessão desconectada
            </div>
            <div className="text-xs text-text-muted mb-3">
              Estado atual: <span className="font-mono">{status.state}</span>. Clique em
              reconectar para gerar um novo QR Code.
            </div>
            <Button
              size="sm"
              icon={<QrCode size={13} />}
              loading={reconectando}
              onClick={reconectar}
            >
              Reconectar e gerar QR
            </Button>
          </div>
        )}

        {/* Estatisticas */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <CardStat
            icon={<Activity size={14} />}
            label="Mensagens hoje"
            valor={status?.mensagens_hoje ?? 0}
          />
          <CardStat
            icon={<Users size={14} />}
            label="Contatos monitorados"
            valor={status?.contatos_monitorados ?? 0}
          />
          <CardStat
            icon={<Clock size={14} />}
            label="Última mensagem"
            valor={
              status?.ultima_mensagem_em
                ? formatarDataRelativa(status.ultima_mensagem_em)
                : '—'
            }
          />
        </div>

        {/* Info da instancia */}
        {status?.enabled && (
          <div className="rounded-lg border border-surface-border bg-surface-raised">
            <div className="px-4 py-3 border-b border-surface-border">
              <div className="text-xs font-medium text-text-secondary">Instância Evolution</div>
            </div>
            <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <Linha label="Nome">{status.instancia || '—'}</Linha>
              <Linha label="Estado">
                <span className="font-mono">{status.state}</span>
              </Linha>
              <Linha label="Perfil">{status.profile_name || '—'}</Linha>
              <Linha label="Conectado">
                {status.conectado ? '✓ sim' : '✗ não'}
              </Linha>
            </div>
          </div>
        )}

        {/* QR Code */}
        {mostrarQr && qrcode?.qrcode_base64 && status?.state !== 'open' && (
          <div className="rounded-lg border border-surface-border bg-surface-raised p-6 flex flex-col items-center gap-4">
            <div className="text-sm font-medium text-text-primary">
              Escaneie no WhatsApp
            </div>
            <img
              src={
                qrcode.qrcode_base64.startsWith('data:')
                  ? qrcode.qrcode_base64
                  : `data:image/png;base64,${qrcode.qrcode_base64}`
              }
              alt="QR Code WhatsApp"
              className="w-64 h-64 rounded border border-surface-border bg-white p-2"
            />
            {qrcode.code && (
              <div className="text-2xs text-text-faint font-mono">
                código: {qrcode.code}
              </div>
            )}
            <Button size="sm" variant="ghost" onClick={buscarQrcode}>
              Atualizar QR
            </Button>
          </div>
        )}

        {/* Como funciona */}
        <div className="rounded-lg border border-surface-border bg-surface-raised p-4 space-y-2">
          <div className="text-xs font-medium text-text-secondary">Como funciona</div>
          <ul className="text-xs text-text-muted space-y-1.5 list-disc pl-4">
            <li>O Jarvis observa apenas mensagens de contatos marcados com <strong>Monitorar WhatsApp</strong> em <a href="/memoria" className="text-accent hover:underline cursor-pointer">Memória → Pessoas</a></li>
            <li>Mensagens de outros números são ignoradas silenciosamente</li>
            <li>Áudios são transcritos automaticamente (Whisper)</li>
            <li>Lembretes, eventos e fatos são extraídos e salvos</li>
            <li>Mensagens urgentes disparam notificação push</li>
            <li><strong>O Jarvis nunca responde no WhatsApp</strong> — apenas observa</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

function CardStat({
  icon,
  label,
  valor,
}: {
  icon: React.ReactNode
  label: string
  valor: number | string
}) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised p-4">
      <div className="flex items-center gap-2 text-text-muted">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold text-text-primary tabular-nums">
        {valor}
      </div>
    </div>
  )
}

function Linha({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-primary">{children}</span>
    </div>
  )
}

function labelEstado(state: string): string {
  switch (state) {
    case 'open':
      return '● conectado'
    case 'connecting':
      return '○ conectando'
    case 'close':
      return '✕ desconectado'
    default:
      return state || 'desconhecido'
  }
}

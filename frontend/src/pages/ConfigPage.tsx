import { useEffect, useState } from 'react'
import { Settings, Lock, Sun, Bell, BellOff, BellRing } from 'lucide-react'
import { toast } from 'sonner'
import { authService } from '@/services/authService'
import { configService, type Configuracao } from '@/services/configService'
import { useAppStore } from '@/store/useAppStore'
import { usePushNotification } from '@/hooks/usePushNotification'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/cn'

export function ConfigPage() {
  const { usuario } = useAppStore()

  // Senha
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmarSenha, setConfirmarSenha] = useState('')
  const [erroSenha, setErroSenha] = useState<string | null>(null)
  const [loadingSenha, setLoadingSenha] = useState(false)

  // Push
  const { status: pushStatus, ativar, desativar } = usePushNotification()

  async function togglePush() {
    if (pushStatus === 'ativo') {
      await desativar()
      toast.success('Notificações desativadas')
    } else {
      const ok = await ativar()
      if (ok) toast.success('Notificações ativadas!')
      else toast.error('Permissão negada. Ative nas configurações do browser.')
    }
  }

  // Configurações gerais
  const [config, setConfig] = useState<Configuracao | null>(null)
  const [horarioBriefing, setHorarioBriefing] = useState('08:00')
  const [flgBriefing, setFlgBriefing] = useState(true)
  const [salvandoConfig, setSalvandoConfig] = useState(false)

  useEffect(() => {
    carregarConfig()
  }, [])

  async function carregarConfig() {
    try {
      const c = await configService.obter()
      setConfig(c)
      setHorarioBriefing(c.horario_briefing)
      setFlgBriefing(c.flg_briefing_diario)
    } catch {
      // silencioso — config tem defaults
    }
  }

  async function handleAlterarSenha(e: React.FormEvent) {
    e.preventDefault()
    setErroSenha(null)
    if (novaSenha !== confirmarSenha) {
      setErroSenha('As senhas não coincidem')
      return
    }
    if (novaSenha.length < 8) {
      setErroSenha('A nova senha deve ter pelo menos 8 caracteres')
      return
    }
    setLoadingSenha(true)
    try {
      await authService.alterarSenha(senhaAtual, novaSenha)
      toast.success('Senha alterada com sucesso')
      setSenhaAtual('')
      setNovaSenha('')
      setConfirmarSenha('')
    } catch {
      setErroSenha('Senha atual incorreta')
    } finally {
      setLoadingSenha(false)
    }
  }

  async function handleSalvarBriefing() {
    setSalvandoConfig(true)
    try {
      const c = await configService.atualizar({
        flg_briefing_diario: flgBriefing,
        horario_briefing: horarioBriefing,
      })
      setConfig(c)
      toast.success(
        flgBriefing
          ? `Briefing ativado para as ${horarioBriefing}`
          : 'Briefing desativado'
      )
    } catch {
      toast.error('Erro ao salvar configuração')
    } finally {
      setSalvandoConfig(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 flex items-center px-6 h-14 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <Settings size={15} className="text-text-muted" />
          <span className="text-sm font-medium text-text-primary">Configurações</span>
        </div>
      </div>

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-lg space-y-8">

          {/* Perfil */}
          <section>
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4">
              Perfil
            </h2>
            <div className="rounded-lg border border-surface-border bg-surface-raised p-4 space-y-3">
              <Row label="Nome" value={usuario?.nome ?? '—'} />
              <Row label="Email" value={usuario?.email ?? '—'} mono />
              <Row label="ID" value={`#${usuario?.cod_usuario ?? '—'}`} mono />
            </div>
          </section>

          {/* Notificações Push */}
          {pushStatus !== 'nao-suportado' && (
            <section>
              <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4">
                Notificações
              </h2>
              <div className="rounded-lg border border-surface-border bg-surface-raised p-4">
                <div className="flex items-start gap-3">
                  <Bell size={15} className="text-accent mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-text-primary">Notificações push</p>
                    <p className="text-xs text-text-faint mt-0.5">
                      Receba lembretes e o briefing diário mesmo com o app em segundo plano.
                    </p>
                  </div>
                </div>
                <div className="mt-4">
                  <button
                    onClick={togglePush}
                    disabled={pushStatus === 'carregando' || pushStatus === 'bloqueado'}
                    className={cn(
                      'flex items-center gap-2 h-9 px-4 rounded text-sm font-medium border transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
                      pushStatus === 'ativo'
                        ? 'border-green-500/30 text-green-400 bg-green-500/10 hover:bg-green-500/20'
                        : pushStatus === 'bloqueado'
                        ? 'border-red-500/30 text-red-400 bg-red-500/10 cursor-not-allowed'
                        : 'border-accent/30 text-accent bg-accent/10 hover:bg-accent/20'
                    )}
                  >
                    {pushStatus === 'ativo' ? (
                      <><BellRing size={14} /> Push ativo — toque para desativar</>
                    ) : pushStatus === 'bloqueado' ? (
                      <><BellOff size={14} /> Bloqueado — ative nas configurações do browser</>
                    ) : pushStatus === 'carregando' ? (
                      <><Bell size={14} /> Verificando...</>
                    ) : (
                      <><Bell size={14} /> Ativar notificações push</>
                    )}
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* Briefing Diário */}
          <section>
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4">
              Briefing Diário
            </h2>
            <div className="rounded-lg border border-surface-border bg-surface-raised p-4 space-y-4">
              <div className="flex items-start gap-3">
                <Sun size={15} className="text-accent mt-0.5 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-text-primary">Resumo do dia</p>
                  <p className="text-xs text-text-faint mt-0.5">
                    Todo dia no horário configurado, o Jarvis envia uma notificação push com seus lembretes e tarefas do dia.
                  </p>
                </div>
              </div>

              {/* Toggle ativo/inativo */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Ativar briefing</span>
                <button
                  onClick={() => setFlgBriefing((v) => !v)}
                  className={cn(
                    'relative inline-flex items-center w-11 h-6 rounded-full transition-colors cursor-pointer shrink-0',
                    flgBriefing ? 'bg-accent' : 'bg-surface-border'
                  )}
                >
                  <span
                    className={cn(
                      'inline-block w-4 h-4 rounded-full bg-white shadow transition-transform duration-200',
                      flgBriefing ? 'translate-x-6' : 'translate-x-1'
                    )}
                  />
                </button>
              </div>

              {/* Horário */}
              {flgBriefing && (
                <div>
                  <label className="text-xs text-text-secondary block mb-1">Horário</label>
                  <input
                    type="time"
                    value={horarioBriefing}
                    onChange={(e) => setHorarioBriefing(e.target.value)}
                    className="h-9 px-3 rounded border border-surface-border bg-surface text-text-primary text-sm focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
              )}

              <div className="pt-1">
                <Button
                  size="sm"
                  onClick={handleSalvarBriefing}
                  disabled={salvandoConfig}
                >
                  {salvandoConfig ? 'Salvando...' : 'Salvar'}
                </Button>
              </div>
            </div>
          </section>

          {/* Segurança */}
          <section>
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4">
              Segurança
            </h2>
            <div className="rounded-lg border border-surface-border bg-surface-raised p-4">
              <div className="flex items-center gap-2 mb-4">
                <Lock size={14} className="text-text-muted" />
                <span className="text-sm font-medium text-text-primary">Alterar senha</span>
              </div>
              <form onSubmit={handleAlterarSenha} className="space-y-3">
                <Input
                  label="Senha atual"
                  type="password"
                  value={senhaAtual}
                  onChange={(e) => setSenhaAtual(e.target.value)}
                  placeholder="••••••••"
                  required
                />
                <Input
                  label="Nova senha"
                  type="password"
                  value={novaSenha}
                  onChange={(e) => setNovaSenha(e.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  required
                />
                <Input
                  label="Confirmar nova senha"
                  type="password"
                  value={confirmarSenha}
                  onChange={(e) => setConfirmarSenha(e.target.value)}
                  placeholder="••••••••"
                  required
                />
                {erroSenha && (
                  <p className="text-xs text-red-400">{erroSenha}</p>
                )}
                <div className="pt-1">
                  <Button type="submit" disabled={loadingSenha} size="sm">
                    {loadingSenha ? 'Salvando...' : 'Salvar senha'}
                  </Button>
                </div>
              </form>
            </div>
          </section>

          {/* Sistema */}
          <section>
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4">
              Sistema
            </h2>
            <div className="rounded-lg border border-surface-border bg-surface-raised p-4">
              <Row label="Versão" value="0.1.0" mono />
              {config && (
                <div className="mt-2">
                  <Row label="Modelo principal" value={config.modelo_preferido} mono />
                </div>
              )}
              <div className="mt-3 pt-3 border-t border-surface-border">
                <p className="text-xs text-text-faint">
                  Jarvis — Assistente pessoal de IA. Modelos: Claude (cérebro) + GPT-4o (fallback).
                </p>
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-text-muted">{label}</span>
      <span className={`text-sm text-text-primary ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  )
}

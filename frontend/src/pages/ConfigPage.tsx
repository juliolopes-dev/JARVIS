import { useState } from 'react'
import { Settings, Lock } from 'lucide-react'
import { toast } from 'sonner'
import { authService } from '@/services/authService'
import { useAppStore } from '@/store/useAppStore'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

export function ConfigPage() {
  const { usuario } = useAppStore()
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmarSenha, setConfirmarSenha] = useState('')
  const [erraSenha, setErroSenha] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

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

    setLoading(true)
    try {
      await authService.alterarSenha(senhaAtual, novaSenha)
      toast.success('Senha alterada com sucesso')
      setSenhaAtual('')
      setNovaSenha('')
      setConfirmarSenha('')
    } catch {
      setErroSenha('Senha atual incorreta')
    } finally {
      setLoading(false)
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
                {erraSenha && (
                  <p className="text-xs text-red-400">{erraSenha}</p>
                )}
                <div className="pt-1">
                  <Button type="submit" loading={loading} size="sm">
                    Salvar senha
                  </Button>
                </div>
              </form>
            </div>
          </section>

          {/* Versão */}
          <section>
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4">
              Sistema
            </h2>
            <div className="rounded-lg border border-surface-border bg-surface-raised p-4">
              <Row label="Versão" value="0.1.0" mono />
              <div className="mt-3 pt-3 border-t border-surface-border">
                <p className="text-xs text-text-faint">
                  Jarvis — Assistente pessoal de IA. Modelos: Claude (cérebro) + GPT-4o mini (fallback).
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

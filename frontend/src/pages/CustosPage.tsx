import { useEffect, useState } from 'react'
import { DollarSign, TrendingUp, AlertCircle, Menu } from 'lucide-react'
import { custosService, type PeriodoCusto, type ResumoCustos } from '@/services/custosService'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/utils/cn'

const PERIODOS: { valor: PeriodoCusto; label: string }[] = [
  { valor: 'mes_atual', label: 'Mês atual' },
  { valor: 'mes_anterior', label: 'Mês anterior' },
  { valor: 'ultimos_7_dias', label: 'Últimos 7 dias' },
  { valor: 'ultimos_30_dias', label: 'Últimos 30 dias' },
]

function formatarUSD(valor: number): string {
  return `$${valor.toFixed(2)}`
}

function formatarBRL(valor: number): string {
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  })
}

function formatarDia(iso: string): string {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

export function CustosPage() {
  const { setSidebarAberta } = useAppStore()
  const [periodo, setPeriodo] = useState<PeriodoCusto>('mes_atual')
  const [resumo, setResumo] = useState<ResumoCustos | null>(null)
  const [mesAnterior, setMesAnterior] = useState<ResumoCustos | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodo])

  async function carregar() {
    setCarregando(true)
    setErro(null)
    try {
      const [atual, anterior] = await Promise.all([
        custosService.obterResumo(periodo),
        periodo === 'mes_atual'
          ? custosService.obterResumo('mes_anterior').catch(() => null)
          : Promise.resolve(null),
      ])
      setResumo(atual)
      setMesAnterior(anterior)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Erro ao carregar custos'
      setErro(msg)
    } finally {
      setCarregando(false)
    }
  }

  // Calcular escala do gráfico de barras
  const maxDia = resumo?.por_dia.reduce((acc, d) => Math.max(acc, d.custo_usd), 0) || 1

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-2 px-4 md:px-6 h-14 border-b border-surface-border">
        <button
          onClick={() => setSidebarAberta(true)}
          className="md:hidden p-1.5 rounded text-text-muted hover:text-text-primary hover:bg-surface-overlay transition-colors cursor-pointer shrink-0"
        >
          <Menu size={18} />
        </button>
        <DollarSign size={15} className="text-text-muted shrink-0" />
        <span className="text-sm font-medium text-text-primary">Custos de API</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {/* Seletor de período */}
        <div className="flex flex-wrap gap-2">
          {PERIODOS.map((p) => (
            <button
              key={p.valor}
              onClick={() => setPeriodo(p.valor)}
              className={cn(
                'px-3 py-1.5 text-xs rounded border transition-colors cursor-pointer',
                periodo === p.valor
                  ? 'border-text-primary text-text-primary'
                  : 'border-surface-border text-text-muted hover:text-text-primary hover:bg-surface-overlay'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>

        {erro && (
          <div className="rounded border border-red-500/30 bg-red-500/5 p-4 flex gap-3">
            <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-sm text-red-400 font-medium">Erro ao consultar custos</p>
              <p className="text-xs text-text-muted mt-1 break-words">{erro}</p>
              <p className="text-xs text-text-muted mt-2">
                Verifique se <code className="font-mono">OPENAI_ADMIN_KEY</code> está
                configurada nas variáveis de ambiente.
              </p>
            </div>
          </div>
        )}

        {carregando && !resumo && (
          <div className="text-sm text-text-muted">Carregando...</div>
        )}

        {resumo && (
          <>
            {/* Card total */}
            <div className="rounded-lg border border-surface-border p-5 md:p-6">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs uppercase tracking-wide text-text-muted">
                  Total do período
                </span>
              </div>
              <div className="flex items-baseline gap-3 flex-wrap">
                <span className="text-3xl md:text-4xl font-semibold font-mono text-text-primary">
                  {formatarUSD(resumo.total_usd)}
                </span>
                <span className="text-lg font-mono text-text-secondary">
                  ≈ {formatarBRL(resumo.total_brl)}
                </span>
              </div>
              <p className="text-xs text-text-faint mt-2 font-mono">
                Cotação usada: {formatarBRL(resumo.cotacao_usd_brl)}/USD
              </p>

              {mesAnterior && periodo === 'mes_atual' && (
                <div className="mt-4 pt-4 border-t border-surface-border flex items-center gap-2 text-xs">
                  <TrendingUp size={14} className="text-text-muted" />
                  <span className="text-text-muted">
                    Mês anterior: <span className="font-mono text-text-secondary">
                      {formatarUSD(mesAnterior.total_usd)}
                    </span>{' '}
                    ({formatarBRL(mesAnterior.total_brl)})
                  </span>
                </div>
              )}
            </div>

            {/* Gráfico de barras por dia */}
            {resumo.por_dia.length > 0 && (
              <div className="rounded-lg border border-surface-border p-5">
                <h3 className="text-sm font-medium text-text-primary mb-4">
                  Gasto por dia
                </h3>
                <div className="flex items-end gap-1 h-32">
                  {resumo.por_dia.map((d) => {
                    const altura = (d.custo_usd / maxDia) * 100
                    return (
                      <div
                        key={d.dia}
                        className="flex-1 flex flex-col items-center gap-1 group min-w-0"
                        title={`${d.dia}: ${formatarUSD(d.custo_usd)} (${formatarBRL(d.custo_brl)})`}
                      >
                        <div
                          className="w-full bg-accent/20 border-t-2 border-accent rounded-t transition-all group-hover:bg-accent/30"
                          style={{ height: `${Math.max(altura, 2)}%` }}
                        />
                      </div>
                    )
                  })}
                </div>
                <div className="flex items-end gap-1 mt-1">
                  {resumo.por_dia.map((d, i) => (
                    <div
                      key={d.dia}
                      className="flex-1 text-center text-2xs text-text-faint font-mono min-w-0 truncate"
                    >
                      {/* Mostra só alguns rótulos pra não sobrecarregar */}
                      {resumo.por_dia.length <= 10 || i % Math.ceil(resumo.por_dia.length / 10) === 0
                        ? formatarDia(d.dia)
                        : ''}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tabela por modelo */}
            <div className="rounded-lg border border-surface-border overflow-hidden">
              <div className="px-5 py-3 border-b border-surface-border">
                <h3 className="text-sm font-medium text-text-primary">Gasto por modelo</h3>
              </div>
              {resumo.por_modelo.length === 0 ? (
                <div className="p-5 text-sm text-text-muted">
                  Nenhum consumo no período.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-text-muted border-b border-surface-border">
                        <th className="text-left font-medium px-4 py-2">Modelo</th>
                        <th className="text-right font-medium px-4 py-2">Tokens entrada</th>
                        <th className="text-right font-medium px-4 py-2">Tokens saída</th>
                        <th className="text-right font-medium px-4 py-2">Custo USD</th>
                        <th className="text-right font-medium px-4 py-2">Custo BRL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resumo.por_modelo.map((m) => (
                        <tr
                          key={m.modelo}
                          className="border-b border-surface-border last:border-b-0"
                        >
                          <td className="px-4 py-2.5 font-mono text-xs text-text-primary">
                            {m.modelo}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-xs text-text-secondary tabular-nums">
                            {m.tokens_in.toLocaleString('pt-BR')}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-xs text-text-secondary tabular-nums">
                            {m.tokens_out.toLocaleString('pt-BR')}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-xs text-text-primary tabular-nums">
                            {formatarUSD(m.custo_usd)}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-xs text-text-secondary tabular-nums">
                            {formatarBRL(m.custo_brl)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <p className="text-2xs text-text-faint">
              Dados consultados em tempo real na API de Usage da OpenAI. Cache de 15 minutos
              para evitar rate limit.
            </p>
          </>
        )}
      </div>
    </div>
  )
}

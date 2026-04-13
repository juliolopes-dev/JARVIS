import { format, formatDistanceToNow, isToday, isYesterday, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

/**
 * Formata timestamp do backend (UTC ISO 8601) para exibição em America/Sao_Paulo.
 * O banco retorna UTC — subtraímos 3h ao interpretar.
 */
function parseBrDate(isoString: string): Date {
  // parseISO já lida com o offset Z/+00:00
  return parseISO(isoString)
}

export function formatarDataConversa(isoString: string): string {
  const date = parseBrDate(isoString)
  if (isToday(date)) return format(date, 'HH:mm')
  if (isYesterday(date)) return 'Ontem'
  return format(date, 'dd/MM/yyyy', { locale: ptBR })
}

export function formatarDataMensagem(isoString: string): string {
  const date = parseBrDate(isoString)
  return format(date, 'HH:mm', { locale: ptBR })
}

export function formatarDataRelativa(isoString: string): string {
  const date = parseBrDate(isoString)
  return formatDistanceToNow(date, { addSuffix: true, locale: ptBR })
}

export function formatarDataCompleta(isoString: string): string {
  const date = parseBrDate(isoString)
  return format(date, "dd 'de' MMMM 'de' yyyy 'às' HH:mm", { locale: ptBR })
}

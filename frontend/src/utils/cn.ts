/**
 * Utilitário para combinar classes CSS de forma condicional.
 * Substitui clsx/classnames sem dependência extra.
 */
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}

import { cn } from '@/utils/cn'

type BadgeVariant = 'default' | 'accent' | 'success' | 'warning' | 'error'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  className?: string
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-surface-overlay text-text-secondary border border-surface-border',
  accent: 'bg-accent-faint text-accent border border-accent/30',
  success: 'bg-green-500/10 text-green-400 border border-green-500/30',
  warning: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
  error: 'bg-red-500/10 text-red-400 border border-red-500/30',
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center h-5 px-1.5 rounded text-2xs font-medium',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  )
}

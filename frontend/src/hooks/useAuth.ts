import { useEffect, useState } from 'react'
import { authService } from '@/services/authService'
import { useAppStore } from '@/store/useAppStore'

export function useAuth() {
  const { usuario, setUsuario } = useAppStore()
  const [verificando, setVerificando] = useState(true)

  useEffect(() => {
    async function verificar() {
      if (!authService.isAutenticado()) {
        setVerificando(false)
        return
      }
      try {
        const u = await authService.me()
        setUsuario(u)
      } catch {
        authService.logout()
      } finally {
        setVerificando(false)
      }
    }
    verificar()
  }, [setUsuario])

  return { usuario, verificando, autenticado: !!usuario }
}

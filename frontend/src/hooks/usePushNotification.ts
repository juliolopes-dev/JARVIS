import { useState, useEffect } from 'react'
import { lembretesService } from '@/services/lembretesService'

type PushStatus = 'nao-suportado' | 'bloqueado' | 'inativo' | 'ativo' | 'carregando'

export function usePushNotification() {
  const [status, setStatus] = useState<PushStatus>('carregando')

  useEffect(() => {
    verificarStatus()
  }, [])

  async function verificarStatus() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      setStatus('nao-suportado')
      return
    }
    const permissao = Notification.permission
    if (permissao === 'denied') {
      setStatus('bloqueado')
      return
    }

    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    setStatus(sub ? 'ativo' : 'inativo')
  }

  async function ativar(): Promise<boolean> {
    try {
      setStatus('carregando')
      const reg = await navigator.serviceWorker.ready

      // Pedir permissao
      const permissao = await Notification.requestPermission()
      if (permissao !== 'granted') {
        setStatus('bloqueado')
        return false
      }

      // Buscar chave VAPID do backend
      const vapidPublicKey = await lembretesService.obterVapidKey()

      // Converter base64url para Uint8Array
      const appServerKey = urlBase64ToUint8Array(vapidPublicKey)

      // Subscrever no push manager
      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: appServerKey,
      })

      // Registrar no backend
      const dispositivo = navigator.userAgent.includes('Mobile') ? 'mobile' : 'desktop'
      await lembretesService.registrarSubscricao(subscription, dispositivo)

      setStatus('ativo')
      return true
    } catch {
      setStatus('inativo')
      return false
    }
  }

  async function desativar(): Promise<void> {
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    if (sub) {
      await lembretesService.removerSubscricao(sub.endpoint)
      await sub.unsubscribe()
    }
    setStatus('inativo')
  }

  return { status, ativar, desativar }
}

// Converte base64url para Uint8Array (necessario para applicationServerKey)
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

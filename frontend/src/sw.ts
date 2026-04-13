/// <reference lib="webworker" />
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'

declare let self: ServiceWorkerGlobalScope

cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)

// ─── Push Notifications ───────────────────────────────────────────────────────

self.addEventListener('push', (event) => {
  if (!event.data) return

  const payload = event.data.json()
  const title = payload.title || 'Jarvis'
  const options: NotificationOptions = {
    body: payload.body || '',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    tag: payload.id_lembrete || 'jarvis',
    data: { url: payload.url || '/lembretes' },
    requireInteraction: true,
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

// ─── Clique na notificação → abre o Jarvis ────────────────────────────────────

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const url = event.notification.data?.url || '/lembretes'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Se já tem uma janela aberta, focar nela e navegar
      for (const client of clientList) {
        if ('focus' in client) {
          client.focus()
          client.postMessage({ type: 'NAVIGATE', url })
          return
        }
      }
      // Senão, abrir nova janela
      if (self.clients.openWindow) {
        return self.clients.openWindow(url)
      }
    })
  )
})

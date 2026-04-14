import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

// Aplicar tema salvo antes do React renderizar (evita flash)
try {
  const raw = localStorage.getItem('jarvis-store')
  const tema = raw ? JSON.parse(raw)?.state?.tema : 'arc'
  document.documentElement.setAttribute('data-theme', tema === 'ironman' ? 'ironman' : 'arc')
} catch {
  document.documentElement.setAttribute('data-theme', 'arc')
}

// Handler de mensagens do Service Worker (navegacao via notificacao push)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    if (event.data?.type === 'NAVIGATE') {
      window.location.href = event.data.url
    }
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)

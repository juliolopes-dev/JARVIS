import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuth } from '@/hooks/useAuth'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { ChatPage } from '@/pages/ChatPage'
import { LembretesPage } from '@/pages/LembretesPage'
import { MemoriaPage } from '@/pages/MemoriaPage'
import { ConfigPage } from '@/pages/ConfigPage'
import { Spinner } from '@/components/ui/Spinner'

function RotaPrivada({ children }: { children: React.ReactNode }) {
  const { autenticado, verificando } = useAuth()

  if (verificando) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  return autenticado ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#111113',
            border: '1px solid #27272a',
            color: '#fafafa',
            fontSize: '13px',
          },
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RotaPrivada>
              <AppLayout />
            </RotaPrivada>
          }
        >
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="chat/:idConversa" element={<ChatPage />} />
          <Route path="lembretes" element={<LembretesPage />} />
          <Route path="memoria" element={<MemoriaPage />} />
          <Route path="config" element={<ConfigPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

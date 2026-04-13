import { Outlet } from 'react-router-dom'
import { Sidebar, SidebarToggle } from './Sidebar'

export function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <SidebarToggle />
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}

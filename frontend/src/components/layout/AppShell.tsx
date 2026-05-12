import { Outlet } from 'react-router-dom'
import Header from './Header'
import StageNav from './StageNav'
import './AppShell.css'

export default function AppShell() {
  return (
    <div className="app-shell">
      <Header />
      <div className="app-body">
        <StageNav />
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}


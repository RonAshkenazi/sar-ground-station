import { NavLink } from 'react-router-dom'
import './StageNav.css'

const STAGES = [
  { path: '/session', label: 'Session Start' },
  { path: '/overview', label: 'Overview' },
  { path: '/calibration', label: 'Calibration' },
  { path: '/enrichment', label: 'Enrichment & Re-ID' },
  { path: '/localization', label: 'Localization' },
  { path: '/analysis', label: 'Result Analysis' },
]

export default function StageNav() {
  return (
    <nav className="stage-nav" aria-label="Pipeline stages">
      {STAGES.map((stage) => (
        <NavLink
          key={stage.path}
          to={stage.path}
          className={({ isActive }) => `stage-nav-item${isActive ? ' active' : ''}`}
        >
          {stage.label}
        </NavLink>
      ))}
    </nav>
  )
}


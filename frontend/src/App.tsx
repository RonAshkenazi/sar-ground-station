import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import AirUnitPage from './pages/AirUnitPage'
import CalibrationPage from './pages/CalibrationPage'
import EmulatorPage from './pages/EmulatorPage'
import LocalizationPage from './pages/LocalizationPage'
import OverviewPage from './pages/OverviewPage'
import ReIdEnrichmentPage from './pages/ReIdEnrichmentPage'
import ResultAnalysisPage from './pages/ResultAnalysisPage'
import SessionStartPage from './pages/SessionStartPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/session" replace />} />
          <Route path="/session" element={<SessionStartPage />} />
          <Route path="/airunit" element={<AirUnitPage />} />
          <Route path="/emulator" element={<EmulatorPage />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/calibration" element={<CalibrationPage />} />
          <Route path="/enrichment" element={<ReIdEnrichmentPage />} />
          <Route path="/localization" element={<LocalizationPage />} />
          <Route path="/analysis" element={<ResultAnalysisPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

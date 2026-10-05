import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Profiling from './pages/Profiling'
import QualityPillars from './pages/QualityPillars'
import IssueExplorer from './pages/IssueExplorer'
import ImpactAnalysis from './pages/ImpactAnalysis'
import Remediation from './pages/Remediation'
import DatasetComparison from './pages/DatasetComparison'
import Governance from './pages/Governance'
import Reports from './pages/Reports'
import Intro from './pages/Intro'
import SharedReport from './pages/SharedReport'

function introSeen() {
  try { return localStorage.getItem('dqi_intro_seen') === '1' } catch { return true }
}

/** First visit goes through the cinematic intro; afterwards the dashboard loads directly. */
function IntroGate({ children }) {
  return introSeen() ? children : <Navigate to="/intro" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="intro" element={<Intro />} />
        <Route path="share/:id" element={<SharedReport />} />
        <Route element={<Layout />}>
          <Route index element={<IntroGate><Dashboard /></IntroGate>} />
          <Route path="profiling" element={<Profiling />} />
          <Route path="pillars" element={<QualityPillars />} />
          <Route path="issues" element={<IssueExplorer />} />
          <Route path="impact" element={<ImpactAnalysis />} />
          <Route path="remediation" element={<Remediation />} />
          <Route path="comparison" element={<DatasetComparison />} />
          <Route path="governance" element={<Governance />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

import { useCallback, useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useTheme } from '../context/ThemeContext'
import { useSocket } from '../context/SocketContext'
import { useData } from '../context/DataContext'
import { click as playClick } from '../utils/sound'
import CommandPalette from './CommandPalette'
import Settings from './Settings'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '🧭' },
  { to: '/profiling', label: 'Profiling', icon: '🔍' },
  { to: '/pillars', label: 'Quality Pillars', icon: '📐' },
  { to: '/issues', label: 'Issue Explorer', icon: '🗂️' },
  { to: '/impact', label: 'Impact Analysis', icon: '🎯' },
  { to: '/remediation', label: 'Remediation', icon: '🛠️' },
  { to: '/comparison', label: 'Dataset Comparison', icon: '📊' },
  { to: '/governance', label: 'Governance', icon: '🛡️' },
  { to: '/reports', label: 'Reports & Assistant', icon: '📄' },
]

export default function Layout() {
  const { dark, toggle: toggleTheme } = useTheme()
  const { connected } = useSocket()
  const { datasets, active, setActive, loadSample } = useData()
  const location = useLocation()
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const openPalette = useCallback(() => setPaletteOpen(true), [])

  const commands = useMemo(() => [
    ...NAV.map((n) => ({ id: `nav-${n.to}`, label: `Go to ${n.label}`, icon: n.icon, to: n.to, hint: 'page', keywords: n.label.toLowerCase() })),
    { id: 'theme', label: dark ? 'Switch to light mode' : 'Switch to dark mode', icon: '🌓', hint: 'theme', action: toggleTheme, keywords: 'theme dark light' },
    { id: 'sample', label: 'Load sample retail dataset', icon: '🧪', hint: 'data', action: () => loadSample(), keywords: 'sample demo' },
    { id: 'assistant', label: 'Ask the assistant', icon: '💬', hint: 'page', to: '/reports', keywords: 'assistant ask question' },
  ], [dark, toggleTheme, loadSample])

  return (
    <div className="flex h-screen bg-page text-text">
      <aside className="w-60 flex-shrink-0 bg-sidebar border-r border-border flex flex-col">
        <div className="flex items-center gap-2.5 px-4 py-4">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center text-lg shadow-lg"
            style={{ background: 'linear-gradient(135deg, var(--color-series-1), var(--color-series-3))' }}
          >📊</div>
          <div>
            <div className="font-extrabold leading-tight">DQI</div>
            <div className="text-xs text-text-secondary leading-tight">Data Quality Intelligence</div>
          </div>
        </div>

        <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={playClick}
              className={({ isActive }) =>
                `dqi-tappable flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  isActive ? 'text-white' : 'text-text hover:bg-border'
                }`
              }
              style={({ isActive }) => (isActive ? { backgroundColor: 'var(--color-series-1)' } : undefined)}
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-good' : 'bg-critical dqi-pulse'}`} />
            {connected ? 'Live connection active' : 'Reconnecting…'}
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b border-border px-6 py-3 flex items-center justify-between gap-3 bg-surface">
          <div className="text-sm text-text-secondary">
            {datasets.length === 0 ? 'No dataset loaded' : `${datasets.length} dataset(s) in this session`}
          </div>
          <div className="flex items-center gap-2">
            {datasets.length > 0 && (
              <select
                value={active || ''}
                onChange={(e) => setActive(e.target.value)}
                className="bg-surface border border-border rounded-lg px-3 py-1.5 text-sm"
              >
                {datasets.map((d) => (
                  <option key={d.filename} value={d.filename}>{d.filename}</option>
                ))}
              </select>
            )}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={openPalette}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-text-secondary hover:bg-surface-raised"
            >
              Search <kbd className="px-1.5 py-0.5 rounded bg-border text-[10px]">⌘K</kbd>
            </motion.button>
            <Settings />
          </div>
        </header>
        <div className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} commands={commands} />
    </div>
  )
}

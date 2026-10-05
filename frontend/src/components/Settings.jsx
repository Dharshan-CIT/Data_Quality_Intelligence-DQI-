import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { click as playClick, toggle as playToggle, isSoundEnabled, setSoundEnabled } from '../utils/sound'

function Switch({ on }) {
  return (
    <span className="w-9 h-5 rounded-full relative transition-colors"
          style={{ backgroundColor: on ? 'var(--color-series-1)' : 'var(--baseline)' }}>
      <motion.span
        className="absolute top-0.5 w-4 h-4 rounded-full bg-white"
        animate={{ x: on ? 18 : 2 }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      />
    </span>
  )
}

export default function Settings() {
  const { dark, toggle: toggleTheme } = useTheme()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [soundOn, setSoundOn] = useState(isSoundEnabled())
  const ref = useRef(null)

  useEffect(() => {
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  return (
    <div ref={ref} className="relative">
      <motion.button
        whileTap={{ scale: 0.92 }}
        onClick={() => { playClick(); setOpen((o) => !o) }}
        className="w-9 h-9 rounded-lg bg-surface border border-border flex items-center justify-center text-base hover:bg-surface-raised"
        aria-label="Settings"
      >⚙️</motion.button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }} transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-64 bg-surface border border-border rounded-xl shadow-xl p-2 z-40"
          >
            <div className="px-2 py-1.5 text-[11px] uppercase tracking-wide text-text-secondary">Appearance</div>
            <motion.button whileTap={{ scale: 0.98 }}
              onClick={() => { playToggle(); toggleTheme() }}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm hover:bg-surface-raised">
              <span>{dark ? '🌙 Dark mode' : '☀️ Light mode'}</span><Switch on={dark} />
            </motion.button>
            <div className="px-2 py-1.5 mt-1 text-[11px] uppercase tracking-wide text-text-secondary">Feedback</div>
            <motion.button whileTap={{ scale: 0.98 }}
              onClick={() => {
                const next = !soundOn
                setSoundEnabled(next); setSoundOn(next)
                if (next) playClick()
              }}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm hover:bg-surface-raised">
              <span>{soundOn ? '🔊 Click sounds' : '🔇 Click sounds'}</span><Switch on={soundOn} />
            </motion.button>
            <div className="px-2 py-1.5 mt-1 text-[11px] uppercase tracking-wide text-text-secondary">Intro</div>
            <motion.button whileTap={{ scale: 0.98 }}
              onClick={() => {
                playClick()
                try { localStorage.removeItem('dqi_intro_seen') } catch { /* storage blocked: the splash still opens */ }
                setOpen(false)
                navigate('/intro')
              }}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm hover:bg-surface-raised">
              <span>✨ Show intro again</span>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { click as playClick, confirm as playConfirm } from '../utils/sound'

const PILLARS = ['completeness', 'uniqueness', 'validity', 'consistency', 'timeliness',
                 'accuracy', 'integrity', 'conformity', 'freshness', 'traceability']

const ORBS = [
  { size: 420, x: '8%', y: '12%', color: '#6366f1', d: 14 },
  { size: 360, x: '70%', y: '8%', color: '#14b8a6', d: 18 },
  { size: 300, x: '60%', y: '62%', color: '#f59e0b', d: 16 },
  { size: 260, x: '14%', y: '70%', color: '#ec4899', d: 20 },
]

export function markIntroSeen() {
  try { localStorage.setItem('dqi_intro_seen', '1') } catch { /* private mode: the intro simply shows again */ }
}

export default function Intro() {
  const navigate = useNavigate()
  const [lit, setLit] = useState(0)

  // Lights up the pillar chips one by one, then loops.
  useEffect(() => {
    const t = setInterval(() => setLit((n) => (n + 1) % PILLARS.length), 420)
    return () => clearInterval(t)
  }, [])

  const enter = () => {
    playConfirm()
    markIntroSeen()
    navigate('/')
  }

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Enter' || e.key === ' ') enter() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <div className="relative min-h-screen w-full overflow-hidden flex items-center justify-center"
         style={{ background: 'radial-gradient(ellipse at 50% 20%, #111827 0%, #05060a 70%)', color: '#f8fafc' }}>
      {ORBS.map((o, i) => (
        <motion.div key={i} aria-hidden className="absolute rounded-full blur-3xl opacity-40 pointer-events-none"
                    style={{ width: o.size, height: o.size, left: o.x, top: o.y, background: o.color }}
                    animate={{ x: [0, 40, -30, 0], y: [0, -30, 25, 0], scale: [1, 1.08, 0.95, 1] }}
                    transition={{ duration: o.d, repeat: Infinity, ease: 'easeInOut' }} />
      ))}

      {/* drifting grid for depth */}
      <div aria-hidden className="absolute inset-0 opacity-[0.07] pointer-events-none"
           style={{ backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)', backgroundSize: '56px 56px' }} />

      <div className="relative z-10 text-center px-6 max-w-3xl">
        <motion.div initial={{ opacity: 0, letterSpacing: '0.6em' }} animate={{ opacity: 1, letterSpacing: '0.28em' }}
                    transition={{ duration: 1.2, ease: 'easeOut' }}
                    className="text-xs font-semibold uppercase text-indigo-300 mb-6">
          Data Quality Intelligence
        </motion.div>

        <motion.h1 initial={{ opacity: 0, y: 28, filter: 'blur(12px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                   transition={{ delay: 0.3, duration: 0.9, ease: 'easeOut' }}
                   className="text-5xl md:text-7xl font-black leading-[1.05] tracking-tight">
          Fix the data that{' '}
          <span className="bg-gradient-to-r from-indigo-400 via-teal-300 to-amber-300 bg-clip-text text-transparent">costs you most</span>
        </motion.h1>

        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0, duration: 0.8 }}
                  className="mt-6 text-lg text-slate-300">
          Ten quality pillars, a live health index, and impact-aware ranking. Every number is computed from your data, and every explanation says whether it was detected or inferred.
        </motion.p>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5, duration: 0.8 }}
                    className="mt-8 flex flex-wrap justify-center gap-2">
          {PILLARS.map((p, i) => (
            <span key={p}
                  className="px-3 py-1 rounded-full text-xs font-semibold border transition-all duration-300 capitalize"
                  style={{
                    borderColor: lit === i ? '#a5b4fc' : 'rgba(148,163,184,0.25)',
                    background: lit === i ? 'rgba(99,102,241,0.35)' : 'transparent',
                    color: lit === i ? '#ffffff' : '#94a3b8',
                    transform: lit === i ? 'translateY(-2px)' : 'none',
                  }}>
              {p}
            </span>
          ))}
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 2.0, duration: 0.6 }}
                    className="mt-12 flex flex-col items-center gap-3">
          <button type="button" onClick={() => { playClick(); enter() }}
                  className="dqi-tappable group relative px-8 py-3.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-indigo-100 transition-colors shadow-[0_0_40px_rgba(129,140,248,0.45)]">
            Enter DQI <span className="inline-block transition-transform group-hover:translate-x-1">→</span>
          </button>
          <span className="text-xs text-slate-500">Press Enter to continue</span>
        </motion.div>
      </div>
    </div>
  )
}

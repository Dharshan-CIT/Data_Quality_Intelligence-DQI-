import { motion, useMotionValue, useSpring } from 'framer-motion'
import { useCountUp } from '../hooks/useCountUp'
import { click as playClick, confirm as playConfirm } from '../utils/sound'

const STATUS_COLORS = {
  good: 'var(--color-good)',
  warning: 'var(--color-warning)',
  serious: 'var(--color-serious)',
  critical: 'var(--color-critical)',
}
const BAND_TO_STATUS = {
  Excellent: 'good', Good: 'good', 'Needs Attention': 'warning', Poor: 'serious', Critical: 'critical',
}

export function statusColor(bandOrStatus) {
  const key = BAND_TO_STATUS[bandOrStatus] || bandOrStatus
  return STATUS_COLORS[key] || 'var(--color-muted)'
}

export function Card({ children, className = '', title }) {
  return (
    <div className={`bg-surface border border-border rounded-xl shadow-sm p-5 ${className}`}>
      {title && <div className="font-semibold mb-3 text-text">{title}</div>}
      {children}
    </div>
  )
}

export function Badge({ label, status }) {
  const color = statusColor(status)
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
      style={{ backgroundColor: `${color}1a`, color }}
    >
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  )
}

export function KpiCard({ label, value, sub, subStatus, decimals = 0, animate = true }) {
  const numeric = typeof value === 'number'
  const animated = useCountUp(numeric ? value : 0, 650, decimals)
  const display = numeric && animate ? animated : value
  return (
    <div className="flex-1 min-w-[150px] bg-surface border border-border rounded-xl shadow-sm px-4 py-3.5 dqi-fade-in">
      <div className="text-xs font-semibold uppercase tracking-wide text-text-secondary mb-1.5">{label}</div>
      <div className="text-2xl font-extrabold text-text leading-tight tabular-nums">{display}</div>
      {sub && (
        <div className="text-xs font-semibold mt-1" style={{ color: subStatus ? statusColor(subStatus) : 'var(--text-secondary)' }}>
          {sub}
        </div>
      )}
    </div>
  )
}

export function KpiRow({ children }) {
  return <div className="flex flex-wrap gap-3 mb-5">{children}</div>
}

export function Spinner({ size = 16 }) {
  return (
    <svg className="animate-spin" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function PageHeader({ icon, title, subtitle }) {
  return (
    <div className="flex items-start gap-3 mb-5">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
           style={{ background: 'linear-gradient(135deg, var(--color-series-1), var(--color-series-3))' }}>
        {icon}
      </div>
      <div>
        <h1 className="text-xl font-extrabold text-text leading-tight">{title}</h1>
        {subtitle && <p className="text-sm text-text-secondary mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}

export function Button({ children, onClick, variant = 'secondary', disabled, type = 'button', className = '' }) {
  const base = 'px-4 py-2 rounded-lg text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary: 'text-white hover:opacity-90',
    secondary: 'bg-surface border border-border text-text hover:bg-surface-raised',
    danger: 'bg-critical text-white hover:opacity-90',
  }
  const style = variant === 'primary' ? { backgroundColor: 'var(--color-series-1)' } : undefined
  const mx = useMotionValue(0)
  const my = useMotionValue(0)
  const x = useSpring(mx, { stiffness: 320, damping: 20 })
  const y = useSpring(my, { stiffness: 320, damping: 20 })
  const handleClick = (e) => {
    if (disabled) return
    ;(variant === 'primary' ? playConfirm : playClick)()
    onClick?.(e)
  }
  const onMove = (e) => {
    if (disabled) return
    const r = e.currentTarget.getBoundingClientRect()
    mx.set((e.clientX - r.left - r.width / 2) * 0.18)
    my.set((e.clientY - r.top - r.height / 2) * 0.25)
  }
  const reset = () => { mx.set(0); my.set(0) }
  return (
    <motion.button type={type} onClick={handleClick} disabled={disabled} style={{ ...style, x, y }}
            onMouseMove={onMove} onMouseLeave={reset}
            whileTap={disabled ? undefined : { scale: 0.93 }}
            className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </motion.button>
  )
}

/** A small toggle-able pill/circle button — severity filters, column chips, tabs. */
export function Chip({ children, active, onClick, className = '', title }) {
  return (
    <button
      type="button"
      title={title}
      onClick={() => { playClick(); onClick?.() }}
      className={`dqi-tappable text-xs font-semibold border transition-colors ${className}`}
      style={active
        ? { backgroundColor: 'var(--color-series-1)', color: 'white', borderColor: 'var(--color-series-1)' }
        : { borderColor: 'var(--border)' }}
    >
      {children}
    </button>
  )
}

export function Select({ value, onChange, options, placeholder }) {
  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text w-full"
    >
      {placeholder && <option value="" disabled>{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
      ))}
    </select>
  )
}

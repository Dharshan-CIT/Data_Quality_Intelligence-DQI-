import { motion } from 'framer-motion'
import { statusColor } from './ui'

function wavePath(width, amplitude, phase) {
  const points = []
  for (let x = 0; x <= width; x += 4) {
    points.push(`${x},${Math.sin((x / width) * Math.PI * 4 + phase) * amplitude}`)
  }
  return `M0,${amplitude} L${points.join(' L')} L${width},${amplitude * 4} L0,${amplitude * 4} Z`
}

export default function LiquidGauge({ value, band, size = 170, label = 'Health' }) {
  const color = statusColor(band)
  const fill = Math.max(0, Math.min(100, value))
  const level = size - (fill / 100) * size

  return (
    <div className="flex flex-col items-center">
      <div className="relative rounded-full overflow-hidden border-4 bg-surface"
           style={{ width: size, height: size, borderColor: color }}>
        <motion.div
          className="absolute left-0 right-0"
          initial={{ top: size }}
          animate={{ top: level }}
          transition={{ type: 'spring', stiffness: 60, damping: 14 }}
          style={{ height: size, background: `linear-gradient(${color}cc, ${color}66)` }}
        >
          {[0, 1].map((i) => (
            <motion.svg key={i} width={size * 2} height={size / 6} viewBox={`0 0 ${size * 2} ${size / 6}`}
                        className="absolute -top-3"
                        style={{ left: 0 }}
                        animate={{ x: [0, -size] }}
                        transition={{ repeat: Infinity, duration: 3.2 + i * 0.8, ease: 'linear' }}>
              <path d={wavePath(size * 2, 6 - i * 2, i * 1.5)} fill={color} opacity={i ? 0.45 : 0.85} />
            </motion.svg>
          ))}
        </motion.div>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div className="text-3xl font-extrabold text-text tabular-nums">{value?.toFixed ? value.toFixed(1) : value}</div>
          <div className="text-xs font-semibold" style={{ color }}>{band}</div>
        </div>
      </div>
      <div className="text-xs uppercase tracking-wide text-text-secondary mt-2">{label}</div>
    </div>
  )
}

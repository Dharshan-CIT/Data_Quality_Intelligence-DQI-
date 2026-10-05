import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

export default function CommandPalette({ open, onClose, commands }) {
  const [query, setQuery] = useState('')
  const [index, setIndex] = useState(0)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  const items = useMemo(() => {
    const q = query.trim().toLowerCase()
    return commands.filter((c) => !q || c.label.toLowerCase().includes(q) || (c.keywords || '').includes(q))
  }, [commands, query])

  useEffect(() => {
    if (open) { setQuery(''); setIndex(0); setTimeout(() => inputRef.current?.focus(), 30) }
  }, [open])

  useEffect(() => setIndex(0), [query])

  const run = (item) => {
    onClose()
    if (item.to) navigate(item.to)
    else item.action?.()
  }

  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setIndex((i) => Math.min(items.length - 1, i + 1)) }
    if (e.key === 'ArrowUp') { e.preventDefault(); setIndex((i) => Math.max(0, i - 1)) }
    if (e.key === 'Enter' && items[index]) run(items[index])
    if (e.key === 'Escape') onClose()
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="palette-backdrop"
          className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] bg-black/40 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onMouseDown={onClose}
        >
          <motion.div
            className="w-[min(560px,92vw)] bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden"
            initial={{ y: -14, scale: 0.97, opacity: 0 }} animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: -8, scale: 0.98, opacity: 0 }} transition={{ type: 'spring', stiffness: 380, damping: 30 }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKey}
              placeholder="Jump to a page or run an action…"
              className="w-full px-5 py-4 bg-transparent text-base outline-none border-b border-border text-text"
            />
            <div className="max-h-[360px] overflow-y-auto p-2">
              {items.length === 0 && <div className="px-4 py-6 text-sm text-text-secondary">No matches</div>}
              {items.map((item, i) => (
                <button
                  key={item.id}
                  onMouseEnter={() => setIndex(i)}
                  onClick={() => run(item)}
                  className={`w-full flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl text-left text-sm transition ${
                    i === index ? 'bg-series-1 text-white' : 'text-text'
                  }`}
                  style={i === index ? { backgroundColor: 'var(--color-series-1)' } : undefined}
                >
                  <span className="flex items-center gap-2.5"><span>{item.icon}</span>{item.label}</span>
                  <span className={`text-[11px] ${i === index ? 'text-white/80' : 'text-text-secondary'}`}>{item.hint}</span>
                </button>
              ))}
            </div>
            <div className="px-4 py-2 text-[11px] text-text-secondary border-t border-border flex gap-4">
              <span>↑↓ navigate</span><span>↵ run</span><span>esc close</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { click as playClick } from '../utils/sound'

const TAG_STYLE = {
  DETECTED: { color: 'var(--color-good)', label: 'DETECTED', hint: 'Computed directly from this dataset.' },
  INFERRED: { color: 'var(--color-warning)', label: 'INFERRED', hint: 'Rule-based explanation. Not verified from this dataset.' },
}

/**
 * Traces a bad column upstream: source → column → issue → propagation → downstream impact.
 * Every node is tagged DETECTED (measured in this dataset) or INFERRED (a likely explanation).
 */
export default function LineageGraph({ issue, rca, filename }) {
  const [open, setOpen] = useState(null)

  const column = issue.column || 'dataset-wide'
  // Each fact appears once. DETECTED nodes come from the measured issue; INFERRED nodes are explanations.
  const steps = [
    {
      id: 'source', tag: 'INFERRED', title: 'Likely upstream source',
      body: rca.probable_source,
      detail: rca.contributing_factors?.length ? rca.contributing_factors : null,
    },
    {
      id: 'column', tag: 'DETECTED', title: `Column · ${column}`,
      body: `Measured in ${filename}.`,
    },
    {
      id: 'issue', tag: 'DETECTED', title: issue.issue_type.replace(/_/g, ' '),
      body: `${issue.affected_records.toLocaleString()} records · ${issue.frequency_pct ?? 0}% of rows · severity ${issue.severity}/5.`,
      detail: [rca.detected_evidence],
    },
    {
      id: 'feature', tag: 'INFERRED', title: 'Affected feature',
      body: `'${column}' and anything joined or derived from it.`,
    },
    {
      id: 'impact', tag: 'INFERRED', title: 'Downstream impact',
      body: rca.downstream_consequence || issue.recommended_action,
    },
  ]

  return (
    <div>
      <div className="flex flex-wrap gap-2 text-[11px] text-text-secondary mb-3">
        {Object.entries(TAG_STYLE).map(([k, v]) => (
          <span key={k} className="inline-flex items-center gap-1.5" title={v.hint}>
            <span className="w-2 h-2 rounded-full" style={{ background: v.color }} /> {v.label}
          </span>
        ))}
      </div>

      <div className="flex flex-col gap-0">
        {steps.map((s, i) => {
          const tag = TAG_STYLE[s.tag]
          const isOpen = open === s.id
          return (
            <motion.div key={s.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.08, duration: 0.3 }} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className="w-3 h-3 rounded-full mt-1.5 ring-4 ring-surface" style={{ background: tag.color }} />
                {i < steps.length - 1 && (
                  <motion.div initial={{ scaleY: 0 }} animate={{ scaleY: 1 }}
                              transition={{ delay: i * 0.08 + 0.15, duration: 0.25 }}
                              className="w-px flex-1 origin-top my-0.5"
                              style={{ background: 'var(--border)', minHeight: 18 }} />
                )}
              </div>
              <button type="button" onClick={() => { playClick(); setOpen(isOpen ? null : s.id) }}
                      className="dqi-tappable flex-1 text-left rounded-lg border border-border bg-surface-raised px-3 py-2 mb-2 hover:border-[var(--color-series-1)] transition-colors">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold capitalize truncate">{s.title}</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                        style={{ background: `${tag.color}22`, color: tag.color }}>{tag.label}</span>
                </div>
                <div className="text-xs text-text-secondary mt-0.5 break-words">{s.body}</div>
                <AnimatePresence initial={false}>
                  {isOpen && s.detail && (
                    <motion.ul initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                               exit={{ height: 0, opacity: 0 }} className="overflow-hidden mt-2 list-disc list-inside text-xs text-text-secondary">
                      {s.detail.map((d, j) => <li key={j}>{d}</li>)}
                    </motion.ul>
                  )}
                </AnimatePresence>
              </button>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

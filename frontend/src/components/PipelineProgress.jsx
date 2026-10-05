import { Spinner } from './ui'

const STAGE_META = {
  ingestion: { label: 'Ingesting file', icon: '📥' },
  profiling: { label: 'Profiling dataset', icon: '🔍' },
  issue_detection: { label: 'Detecting quality issues', icon: '🧪' },
  quality_pillars: { label: 'Scoring 10 quality pillars', icon: '📐' },
  health_index: { label: 'Computing Dataset Health Index', icon: '❤️' },
  impact_scoring: { label: 'Scoring impact (severity × sensitivity × exposure)', icon: '🎯' },
  ranking_stats: { label: 'Comparing frequency vs. impact rankings', icon: '📊' },
}
const STAGE_ORDER = Object.keys(STAGE_META)

function detailLine(stage, detail) {
  if (!detail) return null
  switch (stage) {
    case 'ingestion': return `${detail.rows.toLocaleString()} rows × ${detail.columns} columns (${detail.memory_kb} KB)`
    case 'profiling': return `${detail.missing_pct}% missing · ${detail.duplicate_rows} duplicate rows`
    case 'issue_detection': return `${detail.issue_count} issue(s) found, ${detail.critical_count} critical`
    case 'quality_pillars': return `Weakest: ${detail.weakest.join(', ')}`
    case 'health_index': return `${detail.overall}/100 — ${detail.band}`
    case 'impact_scoring': return `Top impact score: ${detail.top_impact}`
    case 'ranking_stats': return `Spearman rs = ${detail.spearman_rs}, Kendall τ = ${detail.kendall_tau} (n=${detail.n_issues})`
    default: return null
  }
}

export default function PipelineProgress({ progress, pct }) {
  return (
    <div className="dqi-fade-in">
      <div className="w-full h-2 bg-gridline rounded-full overflow-hidden mb-5">
        <div
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{ width: `${pct}%`, backgroundColor: 'var(--color-series-1)' }}
        />
      </div>
      <div className="space-y-2">
        {STAGE_ORDER.map((stageId) => {
          const state = progress[stageId]
          const meta = STAGE_META[stageId]
          const status = state?.status || 'pending'
          return (
            <div
              key={stageId}
              className={`flex items-start gap-3 px-4 py-3 rounded-lg border transition-colors ${
                status === 'done' ? 'border-good/30 bg-good/5' :
                status === 'running' ? 'border-series-1/30 bg-surface-raised' :
                'border-border bg-surface opacity-50'
              }`}
            >
              <div className="w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5">
                {status === 'done' && <span className="text-good text-lg">✓</span>}
                {status === 'running' && <span className="text-series-1" style={{ color: 'var(--color-series-1)' }}><Spinner /></span>}
                {status === 'pending' && <span className="w-2 h-2 rounded-full bg-muted inline-block" />}
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold flex items-center gap-1.5">
                  <span>{meta.icon}</span> {meta.label}
                </div>
                {status === 'done' && state?.detail && (
                  <div className="text-xs text-text-secondary mt-0.5 dqi-fade-in">{detailLine(stageId, state.detail)}</div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { useData } from '../context/DataContext'
import { getIssues } from '../api/results'
import { api } from '../api/client'
import { Card, PageHeader, Badge, Chip } from '../components/ui'
import LineageGraph from '../components/LineageGraph'

const SEVERITY_LABEL = { 5: 'Critical', 4: 'Poor', 3: 'Needs Attention', 2: 'Good', 1: 'Excellent' }

export default function IssueExplorer() {
  const { active } = useData()
  const [issues, setIssues] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [rca, setRca] = useState(null)
  const [sortBy, setSortBy] = useState('impact_score')
  const [severityFilter, setSeverityFilter] = useState([1, 2, 3, 4, 5])

  useEffect(() => {
    if (!active) return
    getIssues(active).then(setIssues)
    setSelectedId(null); setRca(null)
  }, [active])

  const filtered = useMemo(() => {
    return [...issues]
      .filter((i) => severityFilter.includes(i.severity))
      .sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0))
  }, [issues, sortBy, severityFilter])

  useEffect(() => {
    if (!selectedId || !active) { setRca(null); return }
    api.get(`/impact/rca/${selectedId}`, { params: { filename: active } }).then((r) => setRca(r.data))
  }, [selectedId, active])

  if (!active) return <div className="text-text-secondary">Load a dataset on the Dashboard first.</div>
  if (issues.length === 0) return <div className="text-text-secondary">No issues loaded yet…</div>

  const selected = issues.find((i) => i.issue_id === selectedId)

  return (
    <div>
      <PageHeader icon="🗂️" title={`Issue Explorer — ${active}`} subtitle="Filter, sort, and drill into every detected issue." />

      <Card className="mb-5">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <div className="text-xs font-semibold text-text-secondary mb-1">Severity</div>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((s) => (
                <Chip key={s} active={severityFilter.includes(s)}
                      onClick={() => setSeverityFilter((f) => f.includes(s) ? f.filter((x) => x !== s) : [...f, s])}
                      className="w-7 h-7 rounded-full">
                  {s}
                </Chip>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold text-text-secondary mb-1">Sort by</div>
            <div className="flex gap-1">
              {[['impact_score', 'Impact'], ['affected_records', 'Frequency'], ['severity', 'Severity']].map(([k, l]) => (
                <Chip key={k} active={sortBy === k} onClick={() => setSortBy(k)} className="px-3 py-1.5 rounded-lg">
                  {l}
                </Chip>
              ))}
            </div>
          </div>
          <div className="text-xs text-text-secondary ml-auto">Showing {filtered.length} of {issues.length} issues</div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <Card className="lg:col-span-3 !p-0 overflow-hidden">
          <div className="overflow-y-auto max-h-[560px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface">
                <tr className="text-left text-text-secondary border-b border-border">
                  {['Type', 'Column', 'Affected', 'Sev', 'Impact', 'Δ Rank'].map((h) => (
                    <th key={h} className="py-2 px-3 font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((i) => (
                  <tr key={i.issue_id} onClick={() => setSelectedId(i.issue_id)}
                      className={`border-b border-border/60 cursor-pointer hover:bg-surface-raised ${selectedId === i.issue_id ? 'bg-surface-raised' : ''}`}>
                    <td className="py-2 px-3 font-medium">{i.issue_type}</td>
                    <td className="py-2 px-3 text-text-secondary">{i.column || '—'}</td>
                    <td className="py-2 px-3">{i.affected_records}</td>
                    <td className="py-2 px-3"><Badge label={i.severity} status={SEVERITY_LABEL[i.severity]} /></td>
                    <td className="py-2 px-3 font-semibold">{i.impact_score}</td>
                    <td className="py-2 px-3" style={{ color: i.rank_change > 0 ? 'var(--color-good)' : i.rank_change < 0 ? 'var(--color-critical)' : undefined }}>
                      {i.rank_change > 0 ? `+${i.rank_change}` : i.rank_change}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="lg:col-span-2 space-y-5">
          {selected ? (
            <>
              <Card title="Evidence">
                <Badge label={`Severity ${selected.severity}/5`} status={SEVERITY_LABEL[selected.severity]} />
                <p className="text-sm mt-3"><b>Explanation:</b> {selected.explanation}</p>
                <p className="text-sm mt-2"><b>Recommended action:</b> {selected.recommended_action}</p>
              </Card>
              {rca && (
                <Card title="Root-cause analysis">
                  <p className="text-sm">{rca.detected_evidence}</p>
                  <p className="text-sm mt-2 text-text-secondary">
                    <i>Probable source (inferred, not verified from this dataset):</i> {rca.probable_source}
                  </p>
                  {rca.contributing_factors?.length > 0 && (
                    <ul className="list-disc list-inside text-sm text-text-secondary mt-2">
                      {rca.contributing_factors.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  )}
                </Card>
              )}
              {rca && (
                <Card title="Data lineage — where this traces back to">
                  <LineageGraph issue={selected} rca={rca} filename={active} />
                </Card>
              )}
            </>
          ) : (
            <Card><p className="text-text-secondary text-sm">Select an issue from the table to see its full detail and root-cause analysis.</p></Card>
          )}
        </div>
      </div>
    </div>
  )
}

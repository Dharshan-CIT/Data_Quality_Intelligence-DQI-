import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { Card, KpiRow, KpiCard, Badge } from '../components/ui'

/** Public, read-only view of a frozen report snapshot. No session or dataset state is used. */
export default function SharedReport() {
  const { id } = useParams()
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get(`/reports/shared/${encodeURIComponent(id)}`)
      .then((r) => setReport(r.data))
      .catch(() => setError('This shared report does not exist or has been removed.'))
  }, [id])

  return (
    <div className="min-h-screen bg-page text-text">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="text-xs uppercase tracking-wide text-text-secondary">DQI · read-only snapshot</div>
            <h1 className="text-2xl font-extrabold">{report ? report.executive_summary.dataset : 'Shared report'}</h1>
            {report && <div className="text-xs text-text-secondary mt-1">Generated {new Date(report.generated_at).toLocaleString()}</div>}
          </div>
          <Link to="/" className="text-sm font-semibold text-series-1 hover:underline">Open DQI →</Link>
        </div>

        {error && <Card><p className="text-sm text-critical">{error}</p></Card>}
        {!report && !error && <p className="text-text-secondary">Loading snapshot…</p>}

        {report && (
          <div className="space-y-5 dqi-fade-in">
            <KpiRow>
              <KpiCard label="Health index" value={report.executive_summary.overall_health} decimals={2}
                       sub={report.executive_summary.health_band} subStatus={report.executive_summary.health_band} />
              <KpiCard label="Rows" value={report.executive_summary.rows} />
              <KpiCard label="Columns" value={report.executive_summary.columns} />
              <KpiCard label="Issues ranked" value={report.executive_summary.top_issue_count} />
            </KpiRow>

            <Card title="Weakest pillars">
              <div className="flex flex-wrap gap-2">
                {report.executive_summary.weakest_pillars.map((p) => (
                  <span key={p} className="px-3 py-1 rounded-full border border-border text-sm capitalize">{p}</span>
                ))}
              </div>
            </Card>

            <Card title="Top issues by impact" className="!p-0 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-secondary border-b border-border">
                    {['Issue', 'Column', 'Records', 'Impact'].map((h) => <th key={h} className="py-2 px-3 font-semibold">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {report.top_issues_by_impact.slice(0, 15).map((i, idx) => (
                    <tr key={idx} className="border-b border-border/60">
                      <td className="py-2 px-3 font-medium">{i.issue_type}</td>
                      <td className="py-2 px-3 text-text-secondary">{i.column || '—'}</td>
                      <td className="py-2 px-3">{i.affected_records}</td>
                      <td className="py-2 px-3"><Badge label={i.impact_score} status={i.severity >= 4 ? 'critical' : i.severity === 3 ? 'warning' : 'good'} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            {report.frequency_vs_impact && (
              <Card title="Frequency vs impact">
                <p className="text-sm">
                  Spearman rs = {report.frequency_vs_impact.spearman_rs}, Kendall τ = {report.frequency_vs_impact.kendall_tau} across {report.frequency_vs_impact.n_issues} issues.
                </p>
                <p className="text-xs text-text-secondary mt-1">{report.frequency_vs_impact.interpretation}</p>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

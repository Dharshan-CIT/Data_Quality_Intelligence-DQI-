import { useEffect, useState } from 'react'
import {
  Scatter, XAxis, YAxis, ZAxis, CartesianGrid, ResponsiveContainer, Tooltip, Cell, Line, ComposedChart,
} from 'recharts'
import { useData } from '../context/DataContext'
import { getRanking } from '../api/results'
import { api } from '../api/client'
import { Card, KpiRow, KpiCard, PageHeader, Button, Chip } from '../components/ui'

const SEQUENTIAL_BLUE = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#2a78d6', '#1c5cab', '#104281']

function impactColor(score, max) {
  const t = max > 0 ? Math.min(1, score / max) : 0
  const idx = Math.round(t * (SEQUENTIAL_BLUE.length - 1))
  return SEQUENTIAL_BLUE[idx]
}

export default function ImpactAnalysis() {
  const { active } = useData()
  const [ranking, setRanking] = useState([])
  const [corr, setCorr] = useState(null)
  const [columns, setColumns] = useState([])
  const [criticalCols, setCriticalCols] = useState([])
  const [revenue, setRevenue] = useState(0)
  const [opCost, setOpCost] = useState(0)
  const [exposure, setExposure] = useState(null)

  const load = () => {
    if (!active) return
    getRanking(active).then((d) => { setRanking(d.ranking); setCorr(d.correlation) })
    api.get('/results/profile', { params: { filename: active } }).then((r) =>
      setColumns(Object.keys(r.data.column_profiles)))
    api.get('/impact/exposure', { params: { filename: active } }).then((r) => setExposure(r.data))
  }

  useEffect(load, [active])

  const rescore = async () => {
    const { data } = await api.post('/impact/rescore', {
      critical_columns: criticalCols, revenue_per_record: revenue, operational_cost_per_record: opCost,
    }, { params: { filename: active } })
    setRanking(data.ranking); setCorr(data.correlation)
    api.get('/impact/exposure', { params: { filename: active } }).then((r) => setExposure(r.data))
  }

  if (!active) return <div className="text-text-secondary">Load a dataset on the Dashboard first.</div>
  if (!corr) return <div className="text-text-secondary">Loading…</div>

  const maxImpact = Math.max(1, ...ranking.map((r) => r.impact_score || 0))
  const maxRank = Math.max(1, ...ranking.map((r) => Math.max(r.frequency_rank, r.impact_rank)))
  const diagonal = [{ x: 1, y: 1 }, { x: maxRank, y: maxRank }]

  return (
    <div>
      <PageHeader icon="🎯" title={`Impact Analysis — ${active}`}
                  subtitle="The central DQI contribution: frequency-based vs. impact-aware prioritization." />

      <Card title="Scoring configuration" className="mb-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div>
            <div className="text-xs font-semibold text-text-secondary mb-1">Critical columns (sensitivity = 1.0)</div>
            <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
              {columns.map((c) => (
                <Chip key={c} active={criticalCols.includes(c)}
                      onClick={() => setCriticalCols((cc) => cc.includes(c) ? cc.filter((x) => x !== c) : [...cc, c])}
                      className="px-2.5 py-1 rounded-full">
                  {c}
                </Chip>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold text-text-secondary mb-1">Revenue / affected record ($)</div>
            <input type="number" min={0} value={revenue} onChange={(e) => setRevenue(Number(e.target.value))}
                   className="bg-surface border border-border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <div className="text-xs font-semibold text-text-secondary mb-1">Operational cost / record ($)</div>
            <input type="number" min={0} value={opCost} onChange={(e) => setOpCost(Number(e.target.value))}
                   className="bg-surface border border-border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
        </div>
        <Button variant="primary" className="mt-4" onClick={rescore}>Recompute impact scores</Button>
      </Card>

      <Card title="Frequency rank vs. impact-aware rank" className="mb-5">
        <ResponsiveContainer width="100%" height={420}>
          <ComposedChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
            <CartesianGrid stroke="var(--gridline)" />
            <XAxis type="number" dataKey="x" name="Frequency rank" domain={[0.5, maxRank + 0.5]}
                   tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                   label={{ value: 'Frequency rank (1 = most frequent)', position: 'insideBottom', offset: -5, fill: 'var(--text-secondary)', fontSize: 11 }} />
            <YAxis type="number" dataKey="y" name="Impact rank" domain={[0.5, maxRank + 0.5]}
                   tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                   label={{ value: 'Impact rank (1 = highest impact)', angle: -90, position: 'insideLeft', fill: 'var(--text-secondary)', fontSize: 11 }} />
            <ZAxis range={[120, 120]} />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
                     content={({ payload }) => {
                       if (!payload?.length) return null
                       const p = payload[0].payload
                       return (
                         <div className="bg-surface border border-border rounded-lg p-2 text-xs shadow">
                           <div className="font-semibold">{p.label}</div>
                           <div>Freq rank {p.x} · Impact rank {p.y} · score {p.impact_score}</div>
                         </div>
                       )
                     }} />
            <Line data={diagonal} dataKey="y" stroke="var(--baseline)" strokeDasharray="5 5" dot={false} legendType="none" isAnimationActive={false} />
            <Scatter name="Issues" data={ranking.map((r) => ({
              x: r.frequency_rank, y: r.impact_rank, impact_score: r.impact_score, label: `${r.issue_type} · ${r.column}`,
            }))} isAnimationActive animationDuration={700}>
              {ranking.map((r, i) => <Cell key={i} fill={impactColor(r.impact_score, maxImpact)} stroke="rgba(0,0,0,0.15)" />)}
            </Scatter>
          </ComposedChart>
        </ResponsiveContainer>
        <p className="text-xs text-text-secondary mt-2">
          Points on the dashed line: frequency and impact agree. Points far off it: exactly where frequency-based
          prioritization would have picked the wrong thing to fix first.
        </p>
      </Card>

      <KpiRow>
        <KpiCard label="Spearman's rs" value={corr.spearman_rs} decimals={4} sub={`p = ${corr.spearman_p}`} />
        <KpiCard label="Kendall's τ" value={corr.kendall_tau} decimals={4} sub={`p = ${corr.kendall_p}`} />
        <KpiCard label="Issues compared (n)" value={corr.n} />
      </KpiRow>
      <Card className="mb-5"><p className="text-sm">{corr.interpretation}</p></Card>

      <Card title="Full ranking comparison" className="mb-5 !p-0 overflow-hidden">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface">
              <tr className="text-left text-text-secondary border-b border-border">
                {['Type', 'Column', 'Affected', 'Sev', 'Sensitivity', 'Exposure', 'Impact', 'Freq Rank', 'Impact Rank', 'Δ'].map((h) => (
                  <th key={h} className="py-2 px-3 font-semibold whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...ranking].sort((a, b) => a.impact_rank - b.impact_rank).map((r) => (
                <tr key={r.issue_id} className="border-b border-border/60">
                  <td className="py-2 px-3">{r.issue_type}</td>
                  <td className="py-2 px-3 text-text-secondary">{r.column || '—'}</td>
                  <td className="py-2 px-3">{r.affected_records}</td>
                  <td className="py-2 px-3">{r.severity}</td>
                  <td className="py-2 px-3">{r.downstream_sensitivity}</td>
                  <td className="py-2 px-3">{r.business_exposure}</td>
                  <td className="py-2 px-3 font-semibold">{r.impact_score}</td>
                  <td className="py-2 px-3">{r.frequency_rank}</td>
                  <td className="py-2 px-3">{r.impact_rank}</td>
                  <td className="py-2 px-3">{r.rank_change > 0 ? `+${r.rank_change}` : r.rank_change}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {exposure && (
        <Card title="Business impact estimation">
          {revenue === 0 && opCost === 0 && (
            <p className="text-xs text-warning bg-warning/10 rounded-lg px-3 py-2 mb-3">
              UNCONFIGURED: set a revenue/operational-cost assumption above for a real $ estimate.
            </p>
          )}
          <KpiRow>
            <KpiCard label="Total estimated exposure" value={`$${exposure.summary.total_estimated_exposure.toLocaleString()}`} animate={false} />
          </KpiRow>
          <p className="text-xs text-text-secondary">{exposure.summary.label}</p>
        </Card>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell, LabelList } from 'recharts'
import { useData } from '../context/DataContext'
import { getHealth, getPillars } from '../api/results'
import { api } from '../api/client'
import { Card, KpiRow, KpiCard, PageHeader, Badge, Button, statusColor } from '../components/ui'

function WeightPanel({ active, health, onRecomputed }) {
  const current = health.weights_used || {}
  const defaults = health.default_weights || current
  const names = Object.keys(current)
  const [weights, setWeights] = useState(current)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  // Sliders follow the server's active weights whenever the dataset or the computed health changes.
  useEffect(() => { setWeights(health.weights_used || {}) }, [active, health])

  const total = names.reduce((s, n) => s + (Number(weights[n]) || 0), 0)
  const differs = (a, b) => names.some((n) => Math.abs((a[n] ?? 0) - (b[n] ?? 0)) > 1e-9)
  const changed = differs(weights, current)
  const atDefaults = !differs(current, defaults)

  const apply = async (payload) => {
    setBusy(true)
    setMsg(null)
    try {
      const { data } = await api.post('/results/health/weights', { weights: payload }, { params: { filename: active } })
      onRecomputed(data)
      setMsg(`Health index recomputed: ${data.overall} (${data.band}).`)
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Recompute failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title="Pillar weights — tune what matters to your business" className="mb-5">
      <p className="text-sm text-text-secondary mb-4">
        Weights are normalised by their sum, so only the ratios matter. The Health Index is the weighted average of the 10 pillar scores.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
        {names.map((n) => {
          const share = total > 0 ? Math.round(((Number(weights[n]) || 0) / total) * 1000) / 10 : 0
          return (
            <label key={n} className="block">
              <div className="flex justify-between text-sm mb-1">
                <span className="capitalize font-medium">{n}</span>
                <span className="text-text-secondary tabular-nums">{weights[n]?.toFixed(2)} · {share}%</span>
              </div>
              <input type="range" min="0" max="0.3" step="0.01" value={weights[n] ?? 0}
                     onChange={(e) => setWeights((w) => ({ ...w, [n]: parseFloat(e.target.value) }))}
                     className="w-full accent-[var(--color-series-1)]" />
            </label>
          )
        })}
      </div>
      <div className="flex items-center gap-3 mt-5">
        <Button variant="primary" className="whitespace-nowrap" disabled={busy || !changed || total <= 0}
                onClick={() => apply(weights)}>
          {busy ? 'Recomputing…' : 'Recompute health index'}
        </Button>
        <Button className="whitespace-nowrap" disabled={busy || atDefaults} onClick={() => apply(defaults)}>Restore config defaults</Button>
        <Button className="whitespace-nowrap" disabled={busy} onClick={() => apply(Object.fromEntries(names.map((n) => [n, 0.1])))}>Equal weights</Button>
        {msg && <span className="text-sm text-text-secondary">{msg}</span>}
      </div>
    </Card>
  )
}

export default function QualityPillars() {
  const { active } = useData()
  const [health, setHealth] = useState(null)
  const [pillars, setPillars] = useState(null)
  const [open, setOpen] = useState(null)

  useEffect(() => {
    if (!active) return
    Promise.all([getHealth(active), getPillars(active)]).then(([h, p]) => { setHealth(h); setPillars(p) })
  }, [active])

  if (!active) return <div className="text-text-secondary">Load a dataset on the Dashboard first.</div>
  if (!health || !pillars) return <div className="text-text-secondary">Loading…</div>

  const chartData = Object.entries(pillars).map(([name, p]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1), score: p.score, severity: p.severity,
  }))

  return (
    <div>
      <PageHeader icon="📐" title={`10-Pillar Quality Assessment — ${active}`} />
      <KpiRow>
        <KpiCard label="Dataset Health Index" value={health.overall} decimals={2} sub={health.band} subStatus={health.band} />
      </KpiRow>

      <WeightPanel active={active} health={health} onRecomputed={setHealth} />

      <Card title="Pillar scores" className="mb-5">
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={chartData} margin={{ top: 20, right: 10, left: 0, bottom: 40 }}>
            <CartesianGrid stroke="var(--gridline)" vertical={false} />
            <XAxis dataKey="name" angle={-25} textAnchor="end" interval={0} height={60}
                   tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
            <YAxis domain={[0, 105]} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
            <Bar dataKey="score" radius={[4, 4, 0, 0]} isAnimationActive animationDuration={700}>
              <LabelList dataKey="score" position="top" style={{ fill: 'var(--text)', fontSize: 11, fontWeight: 600 }} />
              {chartData.map((d, i) => <Cell key={i} fill={statusColor(d.severity)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Pillar detail">
        <div className="divide-y divide-border">
          {Object.entries(pillars).map(([name, p]) => (
            <div key={name} className="py-3">
              <button className="w-full flex items-center justify-between text-left"
                      onClick={() => setOpen(open === name ? null : name)}>
                <span className="font-semibold capitalize">{name} — {p.score}/100</span>
                <div className="flex items-center gap-3">
                  <Badge label={p.severity} status={p.severity} />
                  <span className="text-text-secondary">{open === name ? '▾' : '▸'}</span>
                </div>
              </button>
              {open === name && (
                <div className="mt-3 text-sm space-y-2 dqi-fade-in">
                  <p>{p.explanation}</p>
                  {p.limitation && (
                    <p className="text-warning bg-warning/10 rounded-lg px-3 py-2 text-xs">⚠ Limitation: {p.limitation}</p>
                  )}
                  <div className="flex gap-6 text-xs text-text-secondary">
                    <span>Affected records: <b className="text-text">{p.affected_records}</b></span>
                    <span>Affected columns: <b className="text-text">{p.affected_columns.length}</b></span>
                    <span>Linked issues: <b className="text-text">{p.detected_issues.length}</b></span>
                  </div>
                  {p.recommendations?.length > 0 && (
                    <ul className="list-disc list-inside text-text-secondary">
                      {p.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

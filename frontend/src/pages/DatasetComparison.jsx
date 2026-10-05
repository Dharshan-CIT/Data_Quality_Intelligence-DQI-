import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend } from 'recharts'
import { useData } from '../context/DataContext'
import { getHealth } from '../api/results'
import { Card, PageHeader, statusColor } from '../components/ui'

const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']

export default function DatasetComparison() {
  const { datasets } = useData()
  const [healthMap, setHealthMap] = useState({})

  useEffect(() => {
    datasets.forEach((d) => {
      if (!healthMap[d.filename]) {
        getHealth(d.filename).then((h) => setHealthMap((m) => ({ ...m, [d.filename]: h })))
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasets])

  if (datasets.length < 2) {
    return (
      <div>
        <PageHeader icon="📊" title="Dataset Comparison" />
        <Card><p className="text-text-secondary">Load at least two datasets on the Dashboard to compare them.</p></Card>
      </div>
    )
  }

  const ready = datasets.filter((d) => healthMap[d.filename])
  const pillarNames = ready.length ? Object.keys(healthMap[ready[0].filename].pillar_scores) : []
  const radarData = pillarNames.map((p) => {
    const row = { pillar: p.charAt(0).toUpperCase() + p.slice(1) }
    ready.forEach((d) => { row[d.filename] = healthMap[d.filename].pillar_scores[p] })
    return row
  })

  return (
    <div>
      <PageHeader icon="📊" title="Dataset Comparison" subtitle="Compare health, pillars, and impact across every loaded dataset." />

      <Card title="Summary" className="mb-5 !p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-secondary border-b border-border">
              {['Dataset', 'Health', 'Band', 'Rows', 'Issues', 'Critical', 'Top Impact'].map((h) => (
                <th key={h} className="py-2 px-3 font-semibold">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.filename} className="border-b border-border/60">
                <td className="py-2 px-3 font-medium">{d.filename}</td>
                <td className="py-2 px-3">{d.health}</td>
                <td className="py-2 px-3">{d.band}</td>
                <td className="py-2 px-3">{d.rows.toLocaleString()}</td>
                <td className="py-2 px-3">{d.issue_count}</td>
                <td className="py-2 px-3">{d.critical_count}</td>
                <td className="py-2 px-3">{d.top_impact_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Health comparison" className="mb-5">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={datasets}>
            <CartesianGrid stroke="var(--gridline)" vertical={false} />
            <XAxis dataKey="filename" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
            <YAxis domain={[0, 105]} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }} />
            <Bar dataKey="health" radius={[4, 4, 0, 0]} isAnimationActive animationDuration={600}>
              {datasets.map((d, i) => <Cell key={i} fill={statusColor(d.band)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {radarData.length > 0 && (
        <Card title="Pillar comparison">
          <ResponsiveContainer width="100%" height={420}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="var(--gridline)" />
              <PolarAngleAxis dataKey="pillar" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 10 }} />
              {ready.map((d, i) => (
                <Radar key={d.filename} name={d.filename} dataKey={d.filename}
                       stroke={SERIES[i % SERIES.length]} fill={SERIES[i % SERIES.length]} fillOpacity={0.15}
                       isAnimationActive animationDuration={700} />
              ))}
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  )
}

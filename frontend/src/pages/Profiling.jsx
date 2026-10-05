import { useEffect, useMemo, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts'
import { useData } from '../context/DataContext'
import { getProfile } from '../api/results'
import { api } from '../api/client'
import { Card, KpiCard, KpiRow, PageHeader, Select, Chip } from '../components/ui'
import MissingHeatmap from '../components/MissingHeatmap'

const ROW_LIMIT = 100

function ColumnInspector({ profile }) {
  const names = Object.keys(profile.column_profiles)
  const [name, setName] = useState(names[0])
  const col = profile.column_profiles[name]
  const top = useMemo(() => Object.entries(col?.top_values || {}), [col])
  const topMax = top.reduce((m, [, v]) => Math.max(m, v), 0)

  if (!col) return null
  const categorical = top.length > 0

  return (
    <Card title="Column inspector" className="mb-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="space-y-3">
          <Select value={name} onChange={setName} options={names} />
          <div className="text-sm space-y-1.5">
            <div><span className="text-text-secondary">Type:</span> <b>{col.inferred_type}</b> <span className="text-text-secondary">({col.dtype})</span></div>
            <div><span className="text-text-secondary">Nulls:</span> <b>{col.null_count}</b> ({col.null_pct}%)</div>
            <div><span className="text-text-secondary">Unique values:</span> <b>{col.unique_count}</b> · {col.cardinality}</div>
            {col.mean != null && <div><span className="text-text-secondary">Mean / median:</span> <b>{col.mean}</b> / {col.median}</div>}
            {col.min != null && <div><span className="text-text-secondary">Range:</span> <b>{col.min}</b> … <b>{col.max}</b></div>}
            {col.outlier_count != null && <div><span className="text-text-secondary">Outliers:</span> <b>{col.outlier_count}</b></div>}
          </div>
        </div>
        <div className="md:col-span-2">
          {categorical ? (
            <>
              <div className="text-xs font-semibold text-text-secondary mb-2">
                Top values {top.length < col.unique_count && `(${top.length} of ${col.unique_count} shown)`}
              </div>
              <div className="space-y-2">
                {top.map(([value, count]) => {
                  const pct = profile.rows ? ((count / profile.rows) * 100).toFixed(1) : '0'
                  return (
                    <div key={value} className="text-sm">
                      <div className="flex justify-between mb-0.5">
                        <span className="truncate pr-3">{value === '' ? <i className="text-text-secondary">(empty)</i> : value}</span>
                        <span className="tabular-nums text-text-secondary whitespace-nowrap">{count.toLocaleString()} · {pct}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-surface-raised overflow-hidden">
                        <div className="h-full rounded-full dqi-bar-grow"
                             style={{ width: `${(count / topMax) * 100}%`, background: 'var(--color-series-1)' }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          ) : (
            <p className="text-sm text-text-secondary">
              Top-value breakdown applies to categorical columns. This column is <b>{col.inferred_type}</b>
              {col.min != null ? ` (range ${col.min} to ${col.max})` : ''}.
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}

function RowInspector({ filename, selection, bins, onClose }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [onlyMissing, setOnlyMissing] = useState(true)

  useEffect(() => {
    setData(null); setError(null)
    api.get('/results/bin-rows', {
      params: { filename, column: selection.column, bin: selection.bin, bins, limit: ROW_LIMIT },
    }).then((r) => setData(r.data)).catch((e) => setError(e.response?.data?.detail || 'Could not load rows.'))
  }, [filename, selection, bins])

  if (error) return <Card className="mb-5"><p className="text-sm text-critical">{error}</p></Card>
  if (!data) return <Card className="mb-5"><p className="text-sm text-text-secondary">Loading rows…</p></Card>

  const columns = data.rows[0] ? Object.keys(data.rows[0].values) : []
  const rows = onlyMissing ? data.rows.filter((r) => r.null_columns.includes(selection.column)) : data.rows

  return (
    <Card className="mb-5 dqi-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <div className="font-semibold">
            Rows {data.row_range[0] + 1}–{data.row_range[1]} · column <span className="text-series-1">{selection.column}</span>
          </div>
          <div className="text-xs text-text-secondary">
            {data.null_in_column.toLocaleString()} of {data.rows_in_bin.toLocaleString()} rows in this block are missing “{selection.column}”.
            {onlyMissing
              ? `Listing those ${rows.length} rows.`
              : `Listing ${rows.length} rows (missing ones first, up to ${ROW_LIMIT}).`}
            NULL cells are highlighted.
          </div>
        </div>
        <div className="flex gap-2">
          <Chip active={onlyMissing} onClick={() => setOnlyMissing((v) => !v)} className="px-3 py-1.5 rounded-lg">
            {onlyMissing ? 'Showing missing only' : 'Showing all rows'}
          </Chip>
          <Chip onClick={onClose} className="px-3 py-1.5 rounded-lg">Close</Chip>
        </div>
      </div>
      <div className="overflow-auto max-h-[420px] border border-border rounded-lg">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-surface">
            <tr className="text-left text-text-secondary border-b border-border">
              <th className="py-2 px-2 font-semibold">Row</th>
              {columns.map((c) => (
                <th key={c} className={`py-2 px-2 font-semibold whitespace-nowrap ${c === selection.column ? 'text-text' : ''}`}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.row} className="border-b border-border/60">
                <td className="py-1.5 px-2 text-text-secondary tabular-nums">{r.row + 1}</td>
                {columns.map((c) => {
                  const isNull = r.null_columns.includes(c)
                  return (
                    <td key={c} className="py-1.5 px-2 whitespace-nowrap tabular-nums"
                        style={isNull ? { background: 'color-mix(in srgb, var(--color-critical) 22%, transparent)', color: 'var(--color-critical)', fontWeight: 600 } : undefined}>
                      {isNull ? 'NULL' : String(r.values[c])}
                    </td>
                  )
                })}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={columns.length + 1} className="py-4 px-2 text-center text-text-secondary">No missing values for this column in this block.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

export default function Profiling() {
  const { active } = useData()
  const [profile, setProfile] = useState(null)
  const [missing, setMissing] = useState(null)
  const [selection, setSelection] = useState(null)

  useEffect(() => {
    if (!active) return
    setSelection(null)
    getProfile(active).then(setProfile)
    api.get('/results/missing-matrix', { params: { filename: active } }).then((r) => setMissing(r.data))
  }, [active])

  const typeCounts = useMemo(() => profile && [
    { type: 'Numeric', count: profile.numeric_columns.length },
    { type: 'Categorical', count: profile.categorical_columns.length },
    { type: 'Datetime', count: profile.datetime_columns.length },
    { type: 'Boolean', count: profile.boolean_columns.length },
    { type: 'Identifier', count: profile.identifier_columns.length },
  ], [profile])

  if (!active) return <div className="text-text-secondary">Load a dataset on the Dashboard first.</div>
  if (!profile) return <div className="text-text-secondary">Loading profile…</div>

  const columns = Object.values(profile.column_profiles)
  const selectedWithRow = selection && missing
    ? { ...selection, row: missing.columns.indexOf(selection.column) }
    : null

  return (
    <div>
      <PageHeader icon="🔍" title={`Data Profiling — ${active}`} subtitle="Dataset- and column-level statistics." />

      <KpiRow>
        <KpiCard label="Rows" value={profile.rows} />
        <KpiCard label="Columns" value={profile.columns} />
        <KpiCard label="Memory" value={`${(profile.memory_bytes / 1024).toFixed(1)} KB`} animate={false} />
        <KpiCard label="Duplicate Rows" value={profile.duplicate_rows}
                 sub={profile.duplicate_rows ? 'flag' : 'none'} subStatus={profile.duplicate_rows ? 'warning' : 'good'} />
        <KpiCard label="Missing Cells" value={profile.missing_cells}
                 sub={`${profile.missing_pct}% of cells`} subStatus={profile.missing_pct > 5 ? 'warning' : 'good'} />
      </KpiRow>

      <ColumnInspector profile={profile} />

      <Card title="Missing-value map" className="mb-5">
        {missing ? (
          <MissingHeatmap data={missing} onCellClick={setSelection}
                          selected={selectedWithRow && selectedWithRow.row >= 0 ? selectedWithRow : null} />
        ) : <div className="text-sm text-text-secondary">Building map…</div>}
      </Card>

      {selection && missing && (
        <RowInspector filename={active} selection={selection} bins={missing.bins} onClose={() => setSelection(null)} />
      )}

      <Card title="Column type breakdown" className="mb-5">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={typeCounts}>
            <CartesianGrid stroke="var(--gridline)" vertical={false} />
            <XAxis dataKey="type" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
            <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} allowDecimals={false} />
            <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }} />
            <Bar dataKey="count" fill="var(--color-series-1)" radius={[4, 4, 0, 0]} isAnimationActive animationDuration={600} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Column-level profile">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-secondary border-b border-border">
                {['Column', 'Type', 'Nulls', 'Null %', 'Unique', 'Cardinality', 'Min', 'Max', 'Mean', 'Outliers'].map((h) => (
                  <th key={h} className="py-2 pr-4 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {columns.map((c) => (
                <tr key={c.name} className="border-b border-border/60 hover:bg-surface-raised">
                  <td className="py-2 pr-4 font-medium">{c.name}</td>
                  <td className="py-2 pr-4 text-text-secondary">{c.inferred_type}</td>
                  <td className="py-2 pr-4">{c.null_count}</td>
                  <td className="py-2 pr-4">{c.null_pct}%</td>
                  <td className="py-2 pr-4">{c.unique_count}</td>
                  <td className="py-2 pr-4 text-text-secondary">{c.cardinality}</td>
                  <td className="py-2 pr-4">{c.min ?? '—'}</td>
                  <td className="py-2 pr-4">{c.max ?? '—'}</td>
                  <td className="py-2 pr-4">{c.mean ?? '—'}</td>
                  <td className="py-2 pr-4">{c.outlier_count ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

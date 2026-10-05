import { useEffect, useState } from 'react'
import { useData } from '../context/DataContext'
import { getProfile } from '../api/results'
import { api } from '../api/client'
import { Card, KpiRow, KpiCard, PageHeader, Button, Select } from '../components/ui'

const OPS = [
  { value: 'duplicates', label: 'Remove exact duplicate rows' },
  { value: 'missing', label: 'Handle missing values' },
  { value: 'invalid_numeric', label: 'Handle invalid numeric values' },
  { value: 'format', label: 'Normalize text formatting' },
  { value: 'dates', label: 'Normalize dates' },
]

export default function Remediation() {
  const { active, activeSummary, refresh } = useData()
  const [profile, setProfile] = useState(null)
  const [remState, setRemState] = useState(null)
  const [op, setOp] = useState('duplicates')
  const [column, setColumn] = useState('')
  const [strategy, setStrategy] = useState('mean')
  const [constant, setConstant] = useState('')
  const [condition, setCondition] = useState('negative')
  const [replacement, setReplacement] = useState(0)
  const [msg, setMsg] = useState(null)
  const [validation, setValidation] = useState(null)

  const loadState = () => active && api.get('/remediation/state', { params: { filename: active } }).then((r) => setRemState(r.data))

  // Each operation has its own valid set of columns/strategies — if we don't
  // reset these when the operation changes, a value picked under the old
  // operation (e.g. a text column for "missing values") silently survives
  // in state even though the dropdown visually falls back to a different
  // displayed option, and the STALE value gets submitted on Apply.
  const changeOp = (nextOp) => {
    setOp(nextOp)
    setColumn('')
    setStrategy(nextOp === 'missing' ? 'mean' : 'replace')
    setCondition('negative')
    setConstant('')
    setReplacement(0)
    setMsg(null)
  }

  useEffect(() => {
    if (!active) return
    getProfile(active).then(setProfile)
    loadState()
    setValidation(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  const apply = async () => {
    setMsg(null)
    try {
      if (op === 'duplicates') {
        const { data } = await api.post('/remediation/remove-duplicates', null, { params: { filename: active } })
        setMsg(`Removed ${data.rows_affected} duplicate rows.`)
      } else if (op === 'missing') {
        const { data } = await api.post('/remediation/missing-values',
          { column, strategy, constant: strategy === 'constant' ? constant : null }, { params: { filename: active } })
        setMsg(`Applied '${strategy}' to ${data.rows_affected} missing values in '${column}'.`)
      } else if (op === 'invalid_numeric') {
        const { data } = await api.post('/remediation/invalid-numeric',
          { column, condition, strategy: strategy === 'constant' ? 'replace' : strategy, replacement },
          { params: { filename: active } })
        setMsg(`Applied repair to ${data.rows_affected} ${condition} values in '${column}'.`)
      } else if (op === 'format') {
        const { data } = await api.post('/remediation/normalize-formatting', { column }, { params: { filename: active } })
        setMsg(`Normalized formatting in '${column}' (${data.rows_affected} rows changed).`)
      } else if (op === 'dates') {
        const { data } = await api.post('/remediation/normalize-dates', { column }, { params: { filename: active } })
        setMsg(`Normalized dates in '${column}' (${data.rows_affected} rows changed).`)
      }
      loadState()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Failed to apply.')
    }
  }

  const commit = async () => {
    const { data } = await api.post('/remediation/commit', null, { params: { filename: active } })
    setValidation(data.validation)
    await refresh()
    loadState()
  }

  if (!active) return <div className="text-text-secondary">Load a dataset on the Dashboard first.</div>
  if (!profile || !remState) return <div className="text-text-secondary">Loading…</div>

  const columnOptions = Object.keys(profile.column_profiles)
  const numericCols = profile.numeric_columns
  const categoricalCols = profile.categorical_columns
  const dateCols = profile.datetime_columns

  return (
    <div>
      <PageHeader icon="🛠️" title={`Remediation — ${active}`}
                  subtitle="Before → Detected Issues → Selected Repairs → After. The original upload is never mutated." />

      <KpiRow>
        <KpiCard label="Rows" value={remState.rows} />
        <KpiCard label="Health (current)" value={activeSummary.health} decimals={2} sub={activeSummary.band} subStatus={activeSummary.band} />
        <KpiCard label="Open issues" value={activeSummary.issue_count} />
      </KpiRow>

      <Card title="Apply a repair" className="mb-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-xs font-semibold text-text-secondary mb-1">Operation</div>
            <Select value={op} onChange={changeOp} options={OPS} />
          </div>

          {op === 'missing' && (
            <>
              <div><div className="text-xs font-semibold text-text-secondary mb-1">Column</div>
                <Select value={column} onChange={setColumn} options={columnOptions} placeholder="Choose column" /></div>
              <div><div className="text-xs font-semibold text-text-secondary mb-1">Strategy</div>
                <Select value={strategy} onChange={setStrategy} options={['drop', 'mean', 'median', 'mode', 'constant', 'ffill']} /></div>
              {strategy === 'constant' && (
                <input value={constant} onChange={(e) => setConstant(e.target.value)} placeholder="Constant value"
                       className="bg-surface border border-border rounded-lg px-3 py-2 text-sm" />
              )}
            </>
          )}

          {op === 'invalid_numeric' && (
            <>
              <div><div className="text-xs font-semibold text-text-secondary mb-1">Column</div>
                <Select value={column} onChange={setColumn} options={numericCols} placeholder="Choose column" /></div>
              <div><div className="text-xs font-semibold text-text-secondary mb-1">Condition</div>
                <Select value={condition} onChange={setCondition} options={['negative', 'zero']} /></div>
              <div><div className="text-xs font-semibold text-text-secondary mb-1">Strategy</div>
                <Select value={strategy} onChange={setStrategy} options={['replace', 'remove', 'quarantine']} /></div>
              {strategy === 'replace' && (
                <input type="number" value={replacement} onChange={(e) => setReplacement(Number(e.target.value))}
                       className="bg-surface border border-border rounded-lg px-3 py-2 text-sm" placeholder="Replacement value" />
              )}
            </>
          )}

          {op === 'format' && (
            <div><div className="text-xs font-semibold text-text-secondary mb-1">Column</div>
              <Select value={column} onChange={setColumn} options={categoricalCols} placeholder="Choose column" /></div>
          )}

          {op === 'dates' && (
            <div><div className="text-xs font-semibold text-text-secondary mb-1">Column</div>
              <Select value={column} onChange={setColumn} options={dateCols} placeholder="Choose column" /></div>
          )}
        </div>
        <Button variant="primary" className="mt-4" onClick={apply} disabled={op !== 'duplicates' && !column}>
          Apply
        </Button>
        {op !== 'duplicates' && !column && (
          <p className="text-xs mt-2 text-text-secondary">Choose a column first.</p>
        )}
        {msg && <p className="text-sm mt-3 text-text-secondary">{msg}</p>}
      </Card>

      <Card title="Audit trail" className="mb-5">
        {remState.audit_trail.length === 0 ? (
          <p className="text-sm text-text-secondary">No remediation actions applied yet.</p>
        ) : (
          <div className="space-y-2 text-sm">
            {remState.audit_trail.map((a, i) => (
              <div key={i} className="border-b border-border pb-2">
                <b>{a.operation}</b> {a.column && `on '${a.column}'`} — {a.rows_affected} rows. {a.reason}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="mb-5">
        <p className="text-sm text-warning bg-warning/10 rounded-lg px-3 py-2 mb-3">
          Committing recomputes health/issues on the remediated data. This does not affect your original upload.
        </p>
        <Button variant="primary" onClick={commit}>Commit remediation and run validation</Button>
      </Card>

      {validation && (
        <Card title="Before / After validation">
          <KpiRow>
            <KpiCard label="Rows" value={validation.rows_after} sub={`${validation.rows_after - validation.rows_before >= 0 ? '+' : ''}${validation.rows_after - validation.rows_before}`} />
            <KpiCard label="Missing cells" value={validation.missing_cells_after} sub={`${validation.missing_cells_after - validation.missing_cells_before}`} />
            <KpiCard label="Health" value={validation.health_after} decimals={2} sub={`${(validation.health_after - validation.health_before).toFixed(2)}`} subStatus="good" />
            <KpiCard label="Issue count" value={validation.issue_count_after} sub={`${validation.issue_count_after - validation.issue_count_before}`} />
          </KpiRow>
          {validation.ks_results.length > 0 && (
            <div className="mt-3 text-sm space-y-2">
              <div className="font-semibold">Kolmogorov–Smirnov distribution shift check</div>
              {validation.ks_results.map((r, i) => (
                <div key={i} className="text-text-secondary">
                  <b className="text-text">{r.column}</b>: stat={r.statistic}, p={r.p_value} — {r.interpretation}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
